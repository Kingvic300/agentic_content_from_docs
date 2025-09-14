from typing import Dict, Any, List
from configuration.configuration import Configuration as Config, logger
from services.workflow_orchestrator import WorkflowOrchestrator


class ContentGeneratorService:
    """
    Main service interface for the Agentic Content Generation System.
    Provides high-level API for content generation from various sources.
    """

    def __init__(self):
        self.config = Config()

        # Validate configuration
        if not self.config.validate():
            raise ValueError("Invalid configuration. Please check your environment variables.")

        self.orchestrator = WorkflowOrchestrator(self.config)
        logger.info("✅ ContentGeneratorService initialized")

    async def shutdown(self):
        """Shutdown the service and all components"""
        await self.orchestrator.shutdown()
        logger.info("✅ ContentGeneratorService shutdown complete")

    async def generate_from_website(
            self,
            url: str,
            topic: str,
            content_type: str,
            audience_level: str = "intermediate",
            tone: str = "conversational",
            depth: int = 2,
            constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate content from a website source"""
        if not url or not topic:
            return {"error": "URL and topic are required"}

        logger.info(f"🌐 Generating {content_type} from website: {url}")

        sources = [{
            "type": "website",
            "source": url,
            "depth": depth,
            "metadata": {"url": url, "scraping_depth": depth}
        }]

        return await self.orchestrator.generate_content_pipeline(
            topic=topic,
            content_type=content_type,
            sources=sources,
            audience_level=audience_level,
            tone=tone,
            constraints=constraints
        )

    async def generate_from_github(
            self,
            repo_url: str,
            topic: str,
            content_type: str,
            audience_level: str = "intermediate",
            tone: str = "conversational",
            constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate content from a GitHub repository"""
        if not repo_url or not topic:
            return {"error": "Repo URL and topic are required"}

        logger.info(f"📁 Generating {content_type} from GitHub: {repo_url}")

        sources = [{
            "type": "github",
            "source": repo_url,
            "metadata": {"repository_url": repo_url}
        }]

        return await self.orchestrator.generate_content_pipeline(
            topic=topic,
            content_type=content_type,
            sources=sources,
            audience_level=audience_level,
            tone=tone,
            constraints=constraints
        )

    async def generate_from_text(
            self,
            content: str,
            topic: str,
            content_type: str,
            audience_level: str = "intermediate",
            tone: str = "conversational",
            constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate content from raw text input"""
        if not content or not topic:
            return {"error": "Content and topic are required"}

        logger.info(f"📝 Generating {content_type} from text content ({len(content)} chars)")

        sources = [{
            "type": "text",
            "source": content,
            "metadata": {
                "title": topic,
                "content_length": len(content),
                "word_count": len(content.split())
            }
        }]

        return await self.orchestrator.generate_content_pipeline(
            topic=topic,
            content_type=content_type,
            sources=sources,
            audience_level=audience_level,
            tone=tone,
            constraints=constraints
        )

    async def generate_from_multiple_sources(
            self,
            sources: List[Dict[str, Any]],
            topic: str,
            content_type: str,
            audience_level: str = "intermediate",
            tone: str = "conversational",
            constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate content from multiple knowledge sources"""
        if not sources or not topic:
            return {"error": "Sources and topic are required"}

        logger.info(f"🔗 Generating {content_type} from {len(sources)} sources")

        return await self.orchestrator.generate_content_pipeline(
            topic=topic,
            content_type=content_type,
            sources=sources,
            audience_level=audience_level,
            tone=tone,
            constraints=constraints
        )

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a content generation task"""
        return await self.orchestrator.get_task_status(task_id)

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return self.orchestrator.get_system_stats()

    def get_supported_content_types(self) -> List[str]:
        """Get list of supported content types"""
        return ["youtube", "tutorial", "book", "interactive"]

    def get_supported_source_types(self) -> List[str]:
        """Get list of supported knowledge source types"""
        return ["website", "github", "text", "document"]

    def get_configuration(self) -> Dict[str, Any]:
        """Get current system configuration (sanitized)"""
        return {
            "max_concurrent_agents": self.config.max_concurrent_agents,
            "min_quality_score": self.config.min_quality_score,
            "max_generation_iterations": self.config.max_generation_iterations,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "min_content_length": self.config.min_content_length,
            "max_context_tokens": self.config.max_context_tokens,
            "embedding_model": self.config.embedding_model
        }