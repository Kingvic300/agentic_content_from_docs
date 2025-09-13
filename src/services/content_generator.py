from typing import Dict, Any, List
from configuration.configuration import Configuration as Config
from services.workflow_orchestrator import WorkflowOrchestrator


class ContentGeneratorService:
    def __init__(self):
        self.config = Config()
        self.orchestrator = WorkflowOrchestrator(self.config)

    async def shutdown(self):
        await self.orchestrator.shutdown()

    async def generate_from_website(self, url: str, topic: str, content_type: str, depth: int = 2) -> Dict[str, Any]:
        if not url or not topic:
            return {"error": "URL and topic are required"}
        sources = [{"type": "website", "source": url, "depth": depth}]
        return await self.orchestrator.generate_content_pipeline(topic, content_type, sources)

    async def generate_from_github(self, repo_url: str, topic: str, content_type: str) -> Dict[str, Any]:
        if not repo_url or not topic:
            return {"error": "Repo URL and topic are required"}
        sources = [{"type": "github", "source": repo_url}]
        return await self.orchestrator.generate_content_pipeline(topic, content_type, sources)

    async def generate_from_text(self, content: str, topic: str, content_type: str) -> Dict[str, Any]:
        if not content or not topic:
            return {"error": "Content and topic are required"}
        sources = [{"type": "text", "source": content, "metadata": {"title": topic}}]
        return await self.orchestrator.generate_content_pipeline(topic, content_type, sources)