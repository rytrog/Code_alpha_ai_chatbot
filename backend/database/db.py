"""
University AI Chatbot — Async Database Layer (psycopg3)
Uses psycopg3 async connections directly (no pool, no SQLAlchemy).
"""
import psycopg
from psycopg.rows import dict_row
from config import settings
from utils.logger import logger

# ── Parse DATABASE_URL into psycopg conninfo ──
def _parse_db_url(url: str) -> str:
    """Convert SQLAlchemy-style URL to psycopg conninfo string."""
    from urllib.parse import unquote, urlparse
    clean_url = url.replace("+psycopg", "").replace("+asyncpg", "")
    parsed = urlparse(clean_url)
    password = unquote(parsed.password) if parsed.password else ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    dbname = parsed.path.lstrip("/") if parsed.path else ""
    user = parsed.username or "postgres"
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"

_conninfo = _parse_db_url(settings.DATABASE_URL)


async def init_db():
    """Create tables on startup."""
    conn = await psycopg.AsyncConnection.connect(_conninfo)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS faq (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                normalized_key VARCHAR(512) NOT NULL UNIQUE,
                answer TEXT NOT NULL,
                category VARCHAR(255),
                source VARCHAR(512)
            )
        """)
        await conn.execute("ALTER TABLE faq ADD COLUMN IF NOT EXISTS source VARCHAR(512)")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS answer_cache (
                id SERIAL PRIMARY KEY,
                normalized_key VARCHAR(512) NOT NULL UNIQUE,
                answer TEXT NOT NULL,
                source TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(512) NOT NULL,
                source_type VARCHAR(100),
                chunk_count INTEGER DEFAULT 0,
                uploaded_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_logs (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT,
                response_type VARCHAR(50) NOT NULL,
                response_time_ms FLOAT DEFAULT 0.0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_chatlog_created ON chat_logs (created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_chatlog_type ON chat_logs (response_type)")
        await conn.commit()
        logger.info("Database tables initialized.")
    finally:
        await conn.close()


async def get_conn():
    """FastAPI dependency — yields an async DB connection with dict rows."""
    conn = await psycopg.AsyncConnection.connect(_conninfo)
    conn.row_factory = dict_row
    try:
        yield conn
    finally:
        await conn.close()
