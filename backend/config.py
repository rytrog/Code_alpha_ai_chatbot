"""
University AI Chatbot — Application Configuration
Loads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

# ── Project root is one level above /backend ──
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    """Central configuration — reads from .env automatically."""

    # ── App ──
    APP_NAME: str = "University AI Chatbot"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── PostgreSQL ──
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/university_ai"

    # ── Gemini AI ──
    GEMINI_API_KEY: str = "SET_YOUR_GEMINI_API_KEY_HERE"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── ChromaDB ──
    CHROMA_PATH: str = str(PROJECT_DIR / "chroma" / "university_docs")

    # ── File uploads ──
    UPLOAD_DIR: str = str(PROJECT_DIR / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "csv", "txt"]

    # ── Rate limiting (per IP) ──
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 3600

    # ── Chat ──
    MAX_MESSAGE_LENGTH: int = 500
    MAX_ANSWER_WORDS: int = 200

    # ── Logging ──
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = str(PROJECT_DIR / "logs")

    # ── RAG ──
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    RAG_TOP_K: int = 3

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton instance used across the app
settings = Settings()
