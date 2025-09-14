import os
import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Configuration:
    output_dir: str = os.environ.get("OUTPUT_DIR", "./outputs")
    max_concurrent_agents: int = int(os.environ.get("MAX_AGENTS", "2"))
    embedding_model: str = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    memory_db_path: str = os.environ.get("MEMORY_DB_PATH", "./memory_db")
    chunk_size: int = int(os.environ.get("CHUNK_SIZE", "2000"))
    chunk_overlap: int = int(os.environ.get("CHUNK_OVERLAP", "200"))
    httrack_docker_image: str = os.environ.get("HTTRACK_IMAGE", "ralfbs/httrack:latest")
    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
    mongo_uri: str = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")

    # Quality thresholds
    min_quality_score: float = float(os.environ.get("MIN_QUALITY_SCORE", "75.0"))
    max_generation_iterations: int = int(os.environ.get("MAX_ITERATIONS", "3"))

    # Content processing
    min_content_length: int = int(os.environ.get("MIN_CONTENT_LENGTH", "500"))
    max_context_tokens: int = int(os.environ.get("MAX_CONTEXT_TOKENS", "8000"))

    def validate(self) -> bool:
        """Validate configuration settings"""
        if not self.gemini_api_key:
            logger.error("❌ GEMINI_API_KEY is required")
            return False
        if not self.mongo_uri:
            logger.error("❌ MONGO_URI is required")
            return False
        return True


# --- Logging setup ---
logger = logging.getLogger("agentic")
logger.setLevel(logging.INFO)

# Avoid adding multiple handlers if this file gets imported more than once
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
