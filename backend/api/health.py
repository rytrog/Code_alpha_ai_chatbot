"""
Health Check API — GET /api/health
"""
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from database.db import get_conn
from services.rag_service import collection_count
from utils.logger import logger

router = APIRouter()


@router.get("/health")
async def health_check(conn=Depends(get_conn)):
    """System health check."""
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {},
    }

    try:
        await conn.execute("SELECT 1")
        health["services"]["postgresql"] = "connected"
    except Exception as e:
        health["services"]["postgresql"] = f"error: {e}"
        health["status"] = "degraded"
        logger.error(f"Health - PostgreSQL: {e}")

    try:
        count = await asyncio.to_thread(collection_count)
        health["services"]["chromadb"] = f"connected ({count} chunks)"
    except Exception as e:
        health["services"]["chromadb"] = f"error: {e}"
        health["status"] = "degraded"

    return health

