"""
Answer Cache Service — avoids repeated AI calls via PostgreSQL.

CRITICAL RULES:
  1. NEVER cache negative/failure answers. If the LLM could not answer
     a question, we do NOT store that response.
  2. No duplicate entries — uses ON CONFLICT to prevent duplicates.
  3. On retrieval, double-checks for stale negatives and purges them.

This ensures every future attempt gets a fresh RAG + LLM pass when
the answer wasn't found previously.
"""
from utils.logger import logger

# ── Phrases that indicate a failed / no-answer response ──
# These patterns MUST be comprehensive — any failure response that gets
# cached will poison future queries for the same normalized key.
_NEGATIVE_PATTERNS = [
    # Exact fallback messages from llm_service.py
    "the requested information is not available in our records",
    "could not generate a response at this moment",
    "please try again later",
    "ai service is not configured",
    # Scope rejection message from scope_service.py
    "sorry, i can only answer queries related to aitd",
    "sorry, i can only answer",
    # System error patterns
    "system error",
    "llm provider",
    "is not supported",
    "please contact aitd administration",
    # Common LLM refusal phrasings
    "i don't have information",
    "i do not have information",
    "i don't have enough information",
    "not mentioned in the context",
    "not found in the context",
    "not found in the provided",
    "not available in the context",
    "not available in our records",
    "no information available",
    "no relevant information",
    "cannot find",
    "unable to find",
    "i cannot answer",
    "i'm unable to answer",
    "does not contain information",
    "does not contain relevant",
    "not present in",
    "the context does not",
    "the provided context does not",
    "beyond the scope",
    "outside my scope",
    "i apologize, but i could not",
    "i apologize, but i don't",
    "i'm sorry, but the",
    "i am sorry, but the",
    "unfortunately, the provided context",
    "unfortunately, i cannot",
    "unfortunately, i could not",
    "information is not available",
    "data is not available",
    "not mentioned in any",
    "no data available",
    "no answer found",
    "couldn't find",
    "could not find",
]


def _is_negative_answer(answer: str) -> bool:
    """Return True if the answer is a failure / fallback message."""
    if not answer or not answer.strip():
        return True
    # Very short answers (< 15 chars) are likely errors
    if len(answer.strip()) < 15:
        return True
    answer_lower = answer.lower()
    return any(pat in answer_lower for pat in _NEGATIVE_PATTERNS)


async def get_cached(normalized_key: str, conn) -> dict | None:
    """Retrieve a cached answer by normalised key (only positive answers)."""
    try:
        r = await conn.execute(
            "SELECT answer, source FROM answer_cache WHERE normalized_key = %s",
            (normalized_key,),
        )
        row = await r.fetchone()
    except Exception as e:
        logger.error(f"Cache read error for key '{normalized_key}': {e}")
        return None

    if row:
        # Double-check: if an old negative answer is stuck in the cache, purge it
        if _is_negative_answer(row["answer"]):
            logger.info(f"Purging cached NEGATIVE answer for key '{normalized_key}'")
            try:
                await conn.execute(
                    "DELETE FROM answer_cache WHERE normalized_key = %s",
                    (normalized_key,),
                )
                await conn.commit()
            except Exception:
                await conn.rollback()
            return None
        return {"answer": row["answer"], "source": row["source"] or ""}
    return None


async def save_cache(normalized_key: str, answer: str, source: str, conn) -> None:
    """Persist a new answer in the cache — ONLY if it is a positive answer."""
    # ── NEVER cache failure / fallback responses ──
    if _is_negative_answer(answer):
        logger.info(f"BLOCKED cache save for NEGATIVE answer (key='{normalized_key}').")
        return

    try:
        # Use ON CONFLICT DO UPDATE to handle duplicates cleanly
        # If a positive answer already exists, update it only if the new answer
        # is longer (more complete) — prevents overwriting good answers with worse ones
        await conn.execute(
            """INSERT INTO answer_cache (normalized_key, answer, source)
               VALUES (%s, %s, %s)
               ON CONFLICT (normalized_key)
               DO UPDATE SET answer = CASE
                   WHEN LENGTH(EXCLUDED.answer) > LENGTH(answer_cache.answer)
                   THEN EXCLUDED.answer
                   ELSE answer_cache.answer
               END,
               source = CASE
                   WHEN LENGTH(EXCLUDED.answer) > LENGTH(answer_cache.answer)
                   THEN EXCLUDED.source
                   ELSE answer_cache.source
               END""",
            (normalized_key, answer, source),
        )
        await conn.commit()
        logger.info(f"Cached positive answer for key '{normalized_key}'.")
    except Exception as e:
        await conn.rollback()
        logger.error(f"Cache save error for key '{normalized_key}': {e}")


async def purge_negative_cache(conn) -> int:
    """
    Remove ALL negative/failure answers from the answer_cache table.
    Called on startup to clean stale entries from before fixes were applied.
    Returns count of entries purged.
    """
    try:
        # Build a big OR condition for all patterns
        conditions = []
        params = []
        for pat in _NEGATIVE_PATTERNS:
            conditions.append("answer ILIKE %s")
            params.append(f"%{pat}%")

        if not conditions:
            return 0

        where_clause = " OR ".join(conditions)
        query = f"DELETE FROM answer_cache WHERE {where_clause}"

        r = await conn.execute(query, params)
        count = r.rowcount
        await conn.commit()

        if count > 0:
            logger.info(f"Purged {count} stale negative cache entries on startup.")
        return count
    except Exception as e:
        await conn.rollback()
        logger.error(f"Failed to purge negative cache: {e}")
        return 0
