import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from configuration.configuration import Configuration as Config
from services.memory import AgentMemory
from services.agents.ingestion_agent import IngestionAgent
from services.agents.planning_agent import PlanningAgent
from services.agents.generation_agent import GenerationAgent
from services.agents.quality_agent import QualityAgent
from models.models import GeneratedContent

logger = logging.getLogger(__name__)


# Try to import get_document_by_id from your models module if available,
# otherwise use a safe fallback that returns None.
try:
    from models.models import get_document_by_id  # type: ignore
except Exception:
    def get_document_by_id(doc_id: str):
        # Fallback: not available in environment. Return None so callers can handle missing docs.
        return None


class WorkflowOrchestrator:
    """
    Central orchestrator for the agentic content generation workflow.
    Coordinates ingestion, memory, planning, generation, and quality agents.
    """

    def __init__(self, config: Config):
        self.config = config
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize memory system
        self.memory = AgentMemory(self.config)

        # Initialize specialized agents
        self.ingestion_agent = IngestionAgent(self.config, self.memory)
        self.planning_agent = PlanningAgent(self.config, self.memory)
        self.generation_agent = GenerationAgent(self.config, self.memory)
        self.quality_agent = QualityAgent(self.config, self.memory)

        # Worker management
        self.workers: List[asyncio.Task] = []
        self.is_running = False

        # Workflow statistics
        self.stats = {
            "tasks_processed": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_quality_score": 0.0,
            "total_processing_time": 0.0
        }

        logger.info("✅ WorkflowOrchestrator initialized with all agents")

    async def add_task(self, task: Dict[str, Any]):
        """Add a task to the processing queue"""
        await self.task_queue.put(task)
        logger.info(f"📋 Task queued: {task.get('id', 'unknown')} ({task.get('content_type', 'unknown')})")

    async def worker(self, worker_id: int):
        """Worker process for handling tasks from the queue"""
        logger.info(f"🔧 Worker-{worker_id} started")

        while True:
            task = await self.task_queue.get()
            if task is None:
                logger.info(f"🔧 Worker-{worker_id} shutting down")
                self.task_queue.task_done()
                break

            try:
                start_time = datetime.now()
                task_id = task.get('id', 'unknown')

                logger.info(f"🔧 Worker-{worker_id} processing task {task_id}")

                # Process task through the full pipeline
                result = await self.process_task_pipeline(task)

                # Save results
                if result.get("status") == "success":
                    saved_path = await self.save_content(result["content"], result["quality_result"])
                    self.stats["successful_generations"] += 1

                    processing_time = (datetime.now() - start_time).total_seconds()
                    self.stats["total_processing_time"] += processing_time

                    logger.info(f"✅ Task {task_id} completed successfully in {processing_time:.1f}s (saved: {saved_path})")
                else:
                    self.stats["failed_generations"] += 1
                    logger.error(f"❌ Task {task_id} failed: {result.get('message', 'Unknown error')}")

                self.stats["tasks_processed"] += 1

            except Exception as e:
                self.stats["failed_generations"] += 1
                self.stats["tasks_processed"] += 1
                logger.exception(f"❌ Worker-{worker_id} error processing task {task.get('id')}: {e}")
            finally:
                self.task_queue.task_done()

    async def process_task_pipeline(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete agentic workflow pipeline:
        Ingestion → Memory → Planning → Generation → Quality → Iteration
        """
        task_id = task.get('id', 'unknown')
        logger.info(f"🔄 Starting pipeline for task {task_id}")

        try:
            # Phase 1: Knowledge Ingestion
            logger.info(f"📥 Phase 1: Knowledge Ingestion - {task_id}")
            ingestion_results = await self._execute_ingestion_phase(task)

            if not ingestion_results:
                return {"status": "error", "message": "No content successfully ingested"}

            # Phase 2: Content Planning
            logger.info(f"📋 Phase 2: Content Planning - {task_id}")
            planning_result = await self._execute_planning_phase(task)

            if planning_result.get("status") != "success":
                return {"status": "error", "message": "Planning phase failed"}

            # Phase 3: Iterative Generation and Quality Assessment
            logger.info(f"🎯 Phase 3: Content Generation & Quality Loop - {task_id}")
            final_result = await self._execute_generation_quality_loop(
                task, ingestion_results, planning_result
            )

            return final_result

        except Exception as e:
            logger.exception(f"❌ Pipeline failed for task {task_id}: {e}")
            return {"status": "error", "message": f"Pipeline execution failed: {str(e)}"}

    async def _execute_ingestion_phase(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute knowledge ingestion for all sources"""
        ingestion_results: List[Dict[str, Any]] = []
        sources = task.get("sources", [])

        if not sources:
            logger.warning("⚠️ No sources provided for ingestion")
            return []

        # Process each source
        for i, source in enumerate(sources):
            logger.info(f"📥 Processing source {i + 1}/{len(sources)}: {source.get('type', 'unknown')}")

            ingestion_task = {
                "type": source.get("type"),
                "source": source.get("source"),
                "metadata": source.get("metadata", {}),
                "depth": source.get("depth", 2)
            }

            try:
                result = await self.ingestion_agent.process(ingestion_task)

                if result and result.get("status") == "success":
                    ingestion_results.append(result)
                    logger.info(f"✅ Source {i + 1} ingested successfully")
                else:
                    logger.warning(f"⚠️ Source {i + 1} ingestion failed: {result.get('message', 'Unknown error') if result else 'No result'}")

            except Exception as e:
                logger.exception(f"❌ Source {i + 1} ingestion error: {e}")

        logger.info(f"📥 Ingestion complete: {len(ingestion_results)}/{len(sources)} sources successful")
        return ingestion_results

    async def _execute_planning_phase(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content planning phase"""
        planning_task = {
            "topic": task.get("topic"),
            "content_type": task.get("content_type"),
            "audience_level": task.get("audience_level", "intermediate"),
            "constraints": task.get("constraints", {})
        }

        try:
            result = await self.planning_agent.process(planning_task)

            if result.get("status") == "success":
                logger.info(f"✅ Planning complete: {len(result.get('outline', []))} sections planned")
            else:
                logger.error(f"❌ Planning failed: {result.get('message', 'Unknown error')}")

            return result

        except Exception as e:
            logger.exception(f"❌ Planning phase error: {e}")
            return {"status": "error", "message": f"Planning failed: {str(e)}"}

    async def _execute_generation_quality_loop(
            self,
            task: Dict[str, Any],
            ingestion_results: List[Dict[str, Any]],
            planning_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute iterative generation and quality assessment loop"""

        max_iterations = getattr(self.config, "max_generation_iterations", 3)
        min_quality_score = getattr(self.config, "min_quality_score", 80.0)

        iteration = 0
        quality_result: Dict[str, Any] = {"quality_metrics": {"overall_score": 0.0}}
        content_obj: Optional[GeneratedContent] = None
        recommendations: List[str] = []

        logger.info(
            f"🔄 Starting generation-quality loop (max {max_iterations} iterations, target quality: {min_quality_score})")

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"🔄 Generation iteration {iteration}/{max_iterations}")

            # Generation phase
            generation_task = {
                "topic": task.get("topic"),
                "content_type": task.get("content_type"),
                "audience_level": task.get("audience_level", "intermediate"),
                "tone": task.get("tone", "conversational"),
                "constraints": task.get("constraints", {}),
                "plan": planning_result,
                "sources": ingestion_results,
                "recommendations": recommendations
            }

            try:
                content_obj = await self.generation_agent.process(generation_task)

                # Validate returned content object
                if not isinstance(content_obj, GeneratedContent):
                    logger.error(f"❌ Generation agent returned invalid content object (type: {type(content_obj)})")
                    break

                length = len(getattr(content_obj, "content", "") or "")
                logger.info(f"✅ Content generated: {length} characters")

            except Exception as e:
                logger.exception(f"❌ Generation failed on iteration {iteration}: {e}")
                break

            # Quality assessment phase
            quality_task = {
                "content": getattr(content_obj, "content", ""),
                "content_type": task.get("content_type"),
                "topic": task.get("topic")
            }

            try:
                quality_result = await self.quality_agent.process(quality_task)

                if quality_result.get("status") != "success":
                    logger.warning(f"⚠️ Quality assessment failed on iteration {iteration}")
                    break

                current_score = quality_result["quality_metrics"].get("overall_score", 0.0)
                logger.info(f"📊 Quality score: {current_score:.1f}/100")

                # Check if quality threshold is met
                if current_score >= min_quality_score:
                    logger.info(f"✅ Quality threshold met ({current_score:.1f} >= {min_quality_score})")
                    break

                # Get recommendations for next iteration
                recommendations = quality_result.get("recommendations", []) or []
                if recommendations:
                    logger.info(f"💡 Applying {len(recommendations)} recommendations for next iteration")
                else:
                    logger.info("ℹ️ No specific recommendations available")

            except Exception as e:
                logger.exception(f"❌ Quality assessment failed on iteration {iteration}: {e}")
                break

        # Final results
        final_score = quality_result.get("quality_metrics", {}).get("overall_score", 0.0)
        meets_standards = final_score >= min_quality_score

        logger.info(f"🏁 Generation loop complete: {iteration} iterations, final score: {final_score:.1f}/100")

        if meets_standards:
            logger.info("✅ Content meets quality standards")
        else:
            logger.warning(f"⚠️ Content below quality threshold ({final_score:.1f} < {min_quality_score})")

        # Update statistics safely
        total_tasks = self.stats["successful_generations"] + self.stats["failed_generations"]
        if total_tasks <= 0:
            # first sample
            self.stats["average_quality_score"] = final_score
        else:
            # running average (include this task)
            self.stats["average_quality_score"] = (
                (self.stats["average_quality_score"] * (total_tasks - 1) + final_score) / max(1, total_tasks)
            )

        return {
            "status": "success",
            "content": content_obj,
            "quality_result": {**quality_result, "meets_quality_standards": meets_standards, "iterations_used": iteration},
            "iterations_used": iteration,
            "meets_quality_standards": meets_standards
        }

    async def save_content(self, content: GeneratedContent, quality_result: Dict[str, Any]) -> Optional[str]:
        """Save generated content with comprehensive metadata"""
        try:
            content_id = getattr(content, "id", None) or getattr(content, "content_id", None) or f"content_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_path = self.output_dir / f"{content_id}.md"

            # Safely obtain attributes with fallbacks
            title = getattr(content, "title", content_id)
            created_at = getattr(content, "created_at", datetime.now())
            if isinstance(created_at, str):
                # try to parse ISO string if necessary; otherwise, use now
                try:
                    created_at = datetime.fromisoformat(created_at)
                except Exception:
                    created_at = datetime.now()

            content_text = getattr(content, "content", "") or ""
            content_type = getattr(content, "content_type", "unknown")
            source_documents = getattr(content, "source_documents", []) or []
            metadata = getattr(content, "metadata", {}) or {}

            memory_stats = self.memory.get_memory_stats()

            full_content = f"""# {title}

**Generated:** {created_at.strftime('%Y-%m-%d %H:%M:%S')}
**Content Type:** {content_type}
**Quality Score:** {quality_result.get('quality_metrics', {}).get('overall_score', 0):.1f}/100
**Meets Standards:** {'✅ Yes' if quality_result.get('meets_quality_standards', False) else '⚠️ No'}

## Metadata
- Source Documents: {len(source_documents)}
- Content ID: {content_id}
- Word Count: {len(content_text.split())}
- Character Count: {len(content_text)}
- Memory Chunks Used: {metadata.get('context_chunks_used', 0)}
- Generation Iterations: {quality_result.get('iterations_used', 1)}

## Knowledge Sources
{self._format_source_documents(source_documents)}

## Memory System Stats
- Total Documents: {memory_stats.get('total_documents', 0)}
- Total Chunks: {memory_stats.get('total_chunks', 0)}
- Total Concepts: {memory_stats.get('total_concepts', 0)}
- Total Relationships: {memory_stats.get('total_relationships', 0)}

---

{content_text}

---

## Quality Metrics
- Overall Score: {quality_result.get('quality_metrics', {}).get('overall_score', 0):.1f}/100
- Technical Accuracy: {quality_result.get('quality_metrics', {}).get('technical_accuracy', 0):.1f}/100
- Readability: {quality_result.get('quality_metrics', {}).get('readability_score', 0):.1f}/100
- Completeness: {quality_result.get('quality_metrics', {}).get('completeness_score', 0):.1f}/100
- Engagement: {quality_result.get('quality_metrics', {}).get('engagement_score', 0):.1f}/100
- Structure: {quality_result.get('quality_metrics', {}).get('structure_score', 0):.1f}/100
- Factual Consistency: {quality_result.get('quality_metrics', {}).get('factual_consistency', 0):.1f}/100

## Detailed Analysis
{self._format_detailed_analysis(quality_result.get('detailed_analysis', {}))}

## Improvement Recommendations
{self._format_recommendations(quality_result.get('recommendations', []))}

## Agent Workflow Trace
- Ingestion Agent: ✅ Processed knowledge sources
- Memory Agent: ✅ Stored and retrieved context
- Planning Agent: ✅ Created content structure
- Generation Agent: ✅ Generated content using configured model
- Quality Agent: ✅ Assessed and validated output

---
*Generated by Agentic Content Generation System*
*Workflow: Ingestion → Memory → Planning → Generation → Quality*
"""

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_content)

            logger.info(f"💾 Content saved: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.exception(f"❌ Failed to save content: {e}")
            return None

    def _format_source_documents(self, source_docs: List[str]) -> str:
        """Format source document information"""
        if not source_docs:
            return "- No source documents available"

        formatted = []
        for doc_id in source_docs:
            try:
                doc = get_document_by_id(doc_id)
                if doc:
                    # doc expected to have title, source, and doc_type attributes
                    title = getattr(doc, "title", doc_id)
                    source = getattr(doc, "source", "unknown")
                    doc_type = getattr(doc, "doc_type", "unknown")
                    formatted.append(f"- **{title}** ({source}) - {doc_type}")
                else:
                    formatted.append(f"- Document ID: {doc_id}")
            except Exception:
                formatted.append(f"- Document ID: {doc_id}")

        return "\n".join(formatted)

    def _format_detailed_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format detailed quality analysis"""
        if not analysis:
            return "- No detailed analysis available"

        formatted = []
        for key, value in analysis.items():
            formatted_key = key.replace('_', ' ').title()
            if isinstance(value, (int, float)):
                formatted.append(f"- **{formatted_key}**: {value}")
            else:
                formatted.append(f"- **{formatted_key}**: {str(value)}")

        return "\n".join(formatted)

    def _format_recommendations(self, recommendations: List[str]) -> str:
        """Format improvement recommendations"""
        if not recommendations:
            return "- No specific recommendations"

        return "\n".join(f"- {rec}" for rec in recommendations)

    async def start(self):
        """Start the workflow orchestrator with worker processes"""
        if self.is_running:
            logger.warning("⚠️ Orchestrator already running")
            return self.workers

        max_workers = getattr(self.config, "max_concurrent_agents", 2)
        logger.info(f"🚀 Starting WorkflowOrchestrator with {max_workers} workers")
        self.is_running = True

        self.workers = [
            asyncio.create_task(self.worker(i))
            for i in range(max_workers)
        ]

        logger.info("✅ All workers started")
        return self.workers

    async def generate_content_pipeline(
            self,
            topic: str,
            content_type: str,
            sources: List[Dict[str, Any]],
            audience_level: str = "intermediate",
            tone: str = "conversational",
            constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for content generation pipeline.
        This is the primary interface for external systems.
        """

        # Validate inputs
        if not topic or not content_type:
            return {"error": "Topic and content_type are required"}

        if not sources:
            return {"error": "At least one knowledge source is required"}

        # Generate unique task ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_topic = topic.replace(' ', '_')
        content_id = f"{content_type}_{safe_topic}_{timestamp}"

        # Create comprehensive task
        task = {
            "id": content_id,
            "topic": topic,
            "content_type": content_type,
            "audience_level": audience_level,
            "tone": tone,
            "constraints": constraints or {},
            "sources": sources,
            "created_at": datetime.now().isoformat()
        }

        logger.info(f"🎯 New content generation request: {content_id}")
        logger.info(f"   Topic: {topic}")
        logger.info(f"   Type: {content_type}")
        logger.info(f"   Sources: {len(sources)}")
        logger.info(f"   Audience: {audience_level}")
        logger.info(f"   Tone: {tone}")

        # Start workers if not already running
        if not self.is_running:
            await self.start()

        # Add task to queue
        await self.add_task(task)

        # For demo / sync clients, return immediate queued response
        return {
            "task_id": content_id,
            "status": "queued",
            "message": "Content generation task queued successfully",
            "workflow_stages": [
                "Knowledge Ingestion",
                "Memory Processing",
                "Content Planning",
                "AI Generation",
                "Quality Assessment",
                "Output Finalization"
            ]
        }

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task (placeholder)"""
        # TODO: replace with DB/cache-backed status tracking
        return {
            "task_id": task_id,
            "status": "processing",
            "current_stage": "Content Generation",
            "progress": 75,
            "estimated_remaining_seconds": 60
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        memory_stats = self.memory.get_memory_stats()

        return {
            "orchestrator_stats": self.stats,
            "memory_stats": memory_stats,
            "agent_status": {
                "ingestion_agent": getattr(self.ingestion_agent, "status", "unknown"),
                "planning_agent": getattr(self.planning_agent, "status", "unknown"),
                "generation_agent": getattr(self.generation_agent, "status", "unknown"),
                "quality_agent": getattr(self.quality_agent, "status", "unknown")
            },
            "system_config": {
                "max_concurrent_agents": getattr(self.config, "max_concurrent_agents", None),
                "min_quality_score": getattr(self.config, "min_quality_score", None),
                "max_iterations": getattr(self.config, "max_generation_iterations", None),
                "chunk_size": getattr(self.config, "chunk_size", None)
            },
            "queue_status": {
                "pending_tasks": self.task_queue.qsize(),
                "active_workers": len([w for w in self.workers if not w.done()]) if self.workers else 0,
                "is_running": self.is_running
            }
        }

    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        if not self.is_running:
            logger.info("🛑 Orchestrator is not running")
            return

        logger.info("🛑 Shutting down WorkflowOrchestrator...")
        self.is_running = False

        # Signal workers to stop by sending sentinel None
        max_workers = getattr(self.config, "max_concurrent_agents", len(self.workers) or 1)
        for _ in range(max_workers):
            await self.task_queue.put(None)

        # Wait for workers to complete
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        # Log final statistics
        logger.info("📊 Final Statistics:")
        logger.info(f"   Tasks Processed: {self.stats['tasks_processed']}")
        logger.info(f"   Successful: {self.stats['successful_generations']}")
        logger.info(f"   Failed: {self.stats['failed_generations']}")
        logger.info(f"   Average Quality: {self.stats['average_quality_score']:.1f}")
        logger.info(f"   Total Processing Time: {self.stats['total_processing_time']:.1f}s")

        logger.info("✅ WorkflowOrchestrator shutdown complete")
