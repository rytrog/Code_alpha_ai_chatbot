"""
Answer Cache Service — avoids repeated AI calls via PostgreSQL.
"""
from utils.logger import logger


async def get_cached(normalized_key: str, conn) -> dict | None:
    """Retrieve a cached answer by normalised key."""
    r = await conn.execute(
        "SELECT answer, source FROM answer_cache WHERE normalized_key = %s",
        (normalized_key,),
    )
    row = await r.fetchone()
    if row:
        return {"answer": row["answer"], "source": row["source"] or ""}
    return None


async def save_cache(normalized_key: str, answer: str, source: str, conn) -> None:
    """Persist a new answer in the cache."""
    try:
        existing = await get_cached(normalized_key, conn)
        if existing:
            return

        await conn.execute(
            "INSERT INTO answer_cache (normalized_key, answer, source) VALUES (%s, %s, %s) ON CONFLICT (normalized_key) DO NOTHING",
            (normalized_key, answer, source),
        )
        await conn.commit()
    except Exception as e:
        await conn.rollback()
        logger.error(f"Cache save error for key '{normalized_key}': {e}")
