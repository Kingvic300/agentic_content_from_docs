import asyncio
from flask import Blueprint, request, jsonify, current_app
from services.content_generator import ContentGeneratorService

content_bp = Blueprint("content", __name__)
service = ContentGeneratorService()


@content_bp.route("/generate/website", methods=["POST"])
def generate_from_website():
    data = request.json or {}
    url = data.get("url")
    topic = data.get("topic")
    content_type = data.get("content_type", "tutorial")
    depth = data.get("depth", 2)

    try:
        result = asyncio.run(service.generate_from_website(url, topic, content_type, depth))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@content_bp.route("/generate/github", methods=["POST"])
def generate_from_github():
    data = request.json or {}
    repo_url = data.get("repo_url")
    topic = data.get("topic")
    content_type = data.get("content_type", "tutorial")

    try:
        result = asyncio.run(service.generate_from_github(repo_url, topic, content_type))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@content_bp.route("/generate/text", methods=["POST"])
def generate_from_text():
    data = request.json or {}
    content = data.get("content")
    topic = data.get("topic")
    content_type = data.get("content_type", "tutorial")

    try:
        result = asyncio.run(service.generate_from_text(content, topic, content_type))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.record_once
def setup(state):
    app = state.app

    @app.teardown_appcontext
    def shutdown(exception=None):
        try:
            asyncio.run(service.shutdown())
        except Exception as e:
            print(f"Error during shutdown: {e}")
