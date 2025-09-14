from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from controllers.content_generator_controller import content_bp
from mongoengine import connect
from configuration.configuration import Configuration, logger

app = Flask(__name__)

# MongoDB configuration
app.config['MONGODB_SETTINGS'] = {
    'db': 'content_gen',
    'host': Configuration.mongo_uri
}

try:
    connect(**app.config['MONGODB_SETTINGS'])
    logger.info("✅ MongoDB connected successfully")
except Exception as e:
    logger.error(f"❌ MongoDB connection failed: {e}")
    raise

# Register blueprints
app.register_blueprint(content_bp)


# Add CORS headers for development
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@app.route('/')
def index():
    """Root endpoint with system information"""
    return {
        "service": "Agentic Content Generation System",
        "version": "1.0.0",
        "description": "Backend-first AI system for transforming knowledge sources into educational content",
        "endpoints": {
            "health": "/health",
            "config": "/config",
            "stats": "/stats",
            "generate_website": "/generate/website",
            "generate_github": "/generate/github",
            "generate_text": "/generate/text",
            "generate_multiple": "/generate/multiple",
            "demo": "/demo"
        },
        "workflow": [
            "Knowledge Ingestion",
            "Memory Processing",
            "Content Planning",
            "AI Generation",
            "Quality Assessment"
        ]
    }


if __name__ == "__main__":
    logger.info("🚀 Starting Agentic Content Generation System")
    logger.info("📋 Available endpoints:")
    logger.info("   GET  /         - System information")
    logger.info("   GET  /health   - Health check")
    logger.info("   GET  /config   - System configuration")
    logger.info("   GET  /stats    - System statistics")
    logger.info("   POST /generate/website - Generate from website")
    logger.info("   POST /generate/github  - Generate from GitHub")
    logger.info("   POST /generate/text    - Generate from text")
    logger.info("   POST /generate/multiple - Generate from multiple sources")
    logger.info("   POST /demo     - Demo generation")

    app.run(debug=True, host='0.0.0.0', port=5000)