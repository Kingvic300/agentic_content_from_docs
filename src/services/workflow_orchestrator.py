import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from configuration.configuration import Configuration as Config
from services.memory import AgentMemory
from services.agents.ingestion_agent import IngestionAgent
from services.agents.planning_agent import PlanningAgent
from services.agents.generation_agent import GenerationAgent
from services.agents.quality_agent import QualityAgent
from models.models import GeneratedContent


logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.memory = AgentMemory(self.config)
        self.ingestion_agent = IngestionAgent(self.config, self.memory)
        self.planning_agent = PlanningAgent(self.config, self.memory)
        self.generation_agent = GenerationAgent(self.config, self.memory)
        self.quality_agent = QualityAgent(self.config, self.memory)

        self.workers = []
        logger.info("WorkflowOrchestrator initialized")

    async def add_task(self, task: Dict[str, Any]):
        await self.task_queue.put(task)
        logger.info(f"Task added to queue: {task.get('id', 'unknown')}")

    async def worker(self, worker_id: int):
        logger.info(f"Worker-{worker_id} started")

        while True:
            task = await self.task_queue.get()
            if task is None:
                logger.info(f"Worker-{worker_id} shutting down")
                break

            try:
                logger.info(f"Worker-{worker_id} processing task {task.get('id', 'unknown')}")
                result = await self.process_task(task)
                await self.save_content(result["content"], result["quality_result"])
            except Exception as e:
                logger.exception(f"Worker-{worker_id} error processing task {task.get('id')}: {e}")
            finally:
                self.task_queue.task_done()

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Processing task {task.get('id')}")

        ingestion_results = []
        for src in task.get("sources", []):
            ing_task = {
                "type": src.get("type"),
                "source": src.get("source"),
                "metadata": src.get("metadata", {}),
                "depth": src.get("depth", 2)
            }
            ing_res = await self.ingestion_agent.process(ing_task)
            if ing_res.get("status") == "success":
                ingestion_results.append(ing_res)
            else:
                logger.warning(f"Ingestion failed for source {src.get('source')}: {ing_res.get('message')}")

        plan_task = {"topic": task.get("topic")}
        plan_res = await self.planning_agent.process(plan_task)

        max_iterations = 3
        iteration = 0
        quality_res = {"quality_metrics": {"overall_score": 0.0}}
        content_obj = None
        while iteration < max_iterations and quality_res["quality_metrics"]["overall_score"] < 75.0:
            generation_task = {
                "topic": task.get("topic"),
                "content_type": task.get("content_type"),
                "plan": plan_res,
                "sources": ingestion_results,
                "recommendations": quality_res.get("recommendations", []) if iteration > 0 else []
            }
            content_obj = await self.generation_agent.process(generation_task)

            if not isinstance(content_obj, GeneratedContent):
                raise ValueError("Invalid content object from generation agent")

            quality_task = {"content": content_obj.content}
            quality_res = await self.quality_agent.process(quality_task)
            logger.info(f"Iteration {iteration + 1}: Quality score = {quality_res['quality_metrics']['overall_score']}")

            iteration += 1

        return {"content": content_obj, "quality_result": quality_res}

    async def save_content(self, content: GeneratedContent, quality_result: Dict[str, Any]) -> str:
        output_path = self.output_dir / f"{content.id}.md"
        try:
            full_content = f"""# {content.title}

**Generated:** {content.created_at.strftime('%Y-%m-%d %H:%M:%S')}
**Content Type:** {content.content_type}
**Quality Score:** {quality_result['quality_metrics']['overall_score']:.1f}/100

## Metadata
- Source Documents: {len(content.source_documents)}
- Content ID: {content.id}

---

{content.content}

---

## Quality Metrics
- Overall Score: {quality_result['quality_metrics']['overall_score']:.1f}/100
- Technical Accuracy: {quality_result['quality_metrics']['technical_accuracy']:.1f}/100
- Readability: {quality_result['quality_metrics']['readability_score']:.1f}/100
- Completeness: {quality_result['quality_metrics']['completeness_score']:.1f}/100

## Recommendations
{chr(10).join(f"- {rec}" for rec in quality_result.get('recommendations', []))}
"""
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_content)
            logger.info(f"Content saved to: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to save content: {e}")
            raise

    async def start(self):
        logger.info("Starting WorkflowOrchestrator")
        self.workers = [
            asyncio.create_task(self.worker(i))
            for i in range(self.config.max_concurrent_agents)
        ]
        return self.workers

    async def generate_content_pipeline(
        self,
        topic: str,
        content_type: str,
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not topic or not content_type:
            return {"error": "Topic and content_type are required"}
        content_id = f"{topic.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}"
        task = {
            "id": content_id,
            "topic": topic,
            "content_type": content_type,
            "sources": sources
        }
        await self.add_task(task)

        fake_content = GeneratedContent(
            id=content_id,
            title=f"{topic} {content_type.capitalize()}",
            content_type=content_type,
            content=f"Generating {content_type} content about {topic}...",
            source_documents=[s.get("document_id") for s in sources],
            metadata={},
        )
        fake_quality = {
            "quality_metrics": {"overall_score": 0.0, "technical_accuracy": 0.0, "readability_score": 0.0, "completeness_score": 0.0},
            "recommendations": [],
        }
        return {"id": content_id, "content": fake_content.to_dict(), "quality_result": fake_quality}

    async def shutdown(self):
        logger.info("Shutting down orchestrator")
        for _ in range(self.config.max_concurrent_agents):
            await self.task_queue.put(None)
        await asyncio.gather(*self.workers, return_exceptions=True)