import asyncio
from flask import Blueprint, request, jsonify
from services.content_generator import ContentGeneratorService
from configuration.configuration import logger

content_bp = Blueprint("content", __name__)
service = ContentGeneratorService()


@content_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        stats = service.get_system_stats()
        return jsonify({
            "status": "healthy",
            "service": "Agentic Content Generation System",
            "version": "1.0.0",
            "agents_active": len([agent for agent, status in stats["agent_status"].items() if status != "error"]),
            "memory_stats": stats["memory_stats"],
            "supported_content_types": service.get_supported_content_types(),
            "supported_source_types": service.get_supported_source_types()
        })
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@content_bp.route("/config", methods=["GET"])
def get_configuration():
    """Get system configuration"""
    try:
        config = service.get_configuration()
        return jsonify({
            "status": "success",
            "configuration": config
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@content_bp.route("/stats", methods=["GET"])
def get_system_stats():
    """Get comprehensive system statistics"""
    try:
        stats = service.get_system_stats()
        return jsonify({
            "status": "success",
            "statistics": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@content_bp.route("/generate/website", methods=["POST"])
def generate_from_website():
    """Generate content from website source"""
    data = request.json or {}
    url = data.get("url")
    topic = data.get("topic")
    content_type = data.get("content_type", "tutorial")
    audience_level = data.get("audience_level", "intermediate")
    tone = data.get("tone", "conversational")
    depth = data.get("depth", 2)
    constraints = data.get("constraints", {})

    logger.info(f"🌐 Website generation request: {url} -> {content_type}")

    try:
        result = asyncio.run(service.generate_from_website(
            url=url,
            topic=topic,
            content_type=content_type,
            audience_level=audience_level,
            tone=tone,
            depth=depth,
            constraints=constraints
        ))
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Website generation failed: {e}")
        return jsonify({"error": str(e)}), 500


@content_bp.route("/generate/github", methods=["POST"])
def generate_from_github():
    """Generate content from GitHub repository"""
    data = request.json or {}
    repo_url = data.get("repo_url")
    topic = data.get("topic")
    content_type = data.get("content_type", "tutorial")
    audience_level = data.get("audience_level", "intermediate")
    tone = data.get("tone", "conversational")
    constraints = data.get("constraints", {})

    logger.info(f"📁 GitHub generation request: {repo_url} -> {content_type}")

    try:
        result = asyncio.run(service.generate_from_github(
            repo_url=repo_url,
            topic=topic,
            content_type=content_type,
            audience_level=audience_level,
            tone=tone,
            constraints=constraints
        ))
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ GitHub generation failed: {e}")
        return jsonify({"error": str(e)}), 500


@content_bp.route("/generate/text", methods=["POST"])
def generate_from_text():
    """Generate content from text input"""
    data = request.json or {}
    content = data.get("content")
    topic = data.get("topic")
    content_type = data.get("content_type", "tutorial")
    audience_level = data.get("audience_level", "intermediate")
    tone = data.get("tone", "conversational")
    constraints = data.get("constraints", {})

    logger.info(f"📝 Text generation request: {len(content or '')} chars -> {content_type}")

    try:
        result = asyncio.run(service.generate_from_text(
            content=content,
            topic=topic,
            content_type=content_type,
            audience_level=audience_level,
            tone=tone,
            constraints=constraints
        ))
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Text generation failed: {e}")
        return jsonify({"error": str(e)}), 500


@content_bp.route("/generate/multiple", methods=["POST"])
def generate_from_multiple_sources():
    """Generate content from multiple sources"""
    data = request.json or {}
    sources = data.get("sources", [])
    topic = data.get("topic")
    content_type = data.get("content_type", "tutorial")
    audience_level = data.get("audience_level", "intermediate")
    tone = data.get("tone", "conversational")
    constraints = data.get("constraints", {})

    logger.info(f"🔗 Multi-source generation request: {len(sources)} sources -> {content_type}")

    try:
        result = asyncio.run(service.generate_from_multiple_sources(
            sources=sources,
            topic=topic,
            content_type=content_type,
            audience_level=audience_level,
            tone=tone,
            constraints=constraints
        ))
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Multi-source generation failed: {e}")
        return jsonify({"error": str(e)}), 500


@content_bp.route("/task/<task_id>/status", methods=["GET"])
def get_task_status(task_id: str):
    """Get status of a specific generation task"""
    try:
        result = asyncio.run(service.get_task_status(task_id))
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Task status check failed: {e}")
        return jsonify({"error": str(e)}), 500


@content_bp.route("/demo", methods=["POST"])
def demo_generation():
    """Demo endpoint for testing the complete pipeline"""
    data = request.json or {}

    # Demo configuration
    demo_config = {
        "topic": data.get("topic", "Machine Learning Basics"),
        "content_type": data.get("content_type", "tutorial"),
        "audience_level": data.get("audience_level", "beginner"),
        "tone": data.get("tone", "conversational"),
        "sources": data.get("sources", [{
            "type": "text",
            "source": """
            Machine Learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed. 

            Key concepts include:
            - Supervised Learning: Learning from labeled examples
            - Unsupervised Learning: Finding patterns in unlabeled data  
            - Neural Networks: Computing systems inspired by biological neural networks
            - Deep Learning: Neural networks with multiple layers
            - Training Data: The dataset used to teach the algorithm
            - Model: The mathematical representation learned from data

            Common applications include image recognition, natural language processing, recommendation systems, and predictive analytics.
            """,
            "metadata": {"title": "ML Basics Overview"}
        }]),
        "constraints": data.get("constraints", {"length": "medium", "complexity": "low"})
    }

    logger.info(f"🎯 Demo generation: {demo_config['topic']} -> {demo_config['content_type']}")

    try:
        result = asyncio.run(service.generate_from_multiple_sources(**demo_config))
        return jsonify({
            "status": "success",
            "demo_config": demo_config,
            "result": result,
            "message": "Demo generation completed successfully"
        })
    except Exception as e:
        logger.error(f"❌ Demo generation failed: {e}")
        return jsonify({"error": str(e), "demo_config": demo_config}), 500


@content_bp.record_once
def setup(state):
    """Setup teardown handler"""
    app = state.app

    @app.teardown_appcontext
    def shutdown(exception=None):
        try:
            asyncio.run(service.shutdown())
            logger.info("✅ Service shutdown complete")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")