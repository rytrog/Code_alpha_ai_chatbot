"""
Chat API — POST /api/chat
9-stage pipeline using psycopg directly.
"""
import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from psycopg import AsyncConnection

from database.db import get_conn
from services.greeting_service import check_greeting
from services.faq_service import check_faq
from services.normalize_service import normalize
from services.cache_service import get_cached, save_cache
from services.scope_service import is_in_scope, OUT_OF_SCOPE_REPLY
from services.rag_service import retrieve
from services.gemini_service import generate_answer
from services.source_service import format_sources
from utils.validator import validate_message
from utils.logger import logger

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="User question")


class ChatResponse(BaseModel):
    answer: str
    source: str = ""
    response_type: str = "rag"


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, conn=Depends(get_conn)):
    """Process a user question through the 9-stage pipeline."""
    start = time.time()
    message = body.message.strip()

    is_valid, err = validate_message(message)
    if not is_valid:
        return ChatResponse(answer=err, source="", response_type="error")

    # Stage 1: Greeting
    greeting = check_greeting(message)
    if greeting:
        elapsed = (time.time() - start) * 1000
        await _log(conn, message, greeting, "", "greeting", elapsed)
        return ChatResponse(answer=greeting, source="", response_type="greeting")

    # Stage 2+3: Normalize + FAQ
    norm_key = normalize(message)
    faq_result = await check_faq(norm_key, conn)
    if faq_result:
        elapsed = (time.time() - start) * 1000
        await _log(conn, message, faq_result["answer"], faq_result["source"], "faq", elapsed)
        return ChatResponse(answer=faq_result["answer"], source=faq_result["source"], response_type="faq")

    # Stage 4: Cache
    cached = await get_cached(norm_key, conn)
    if cached:
        elapsed = (time.time() - start) * 1000
        await _log(conn, message, cached["answer"], cached["source"], "cached", elapsed)
        return ChatResponse(answer=cached["answer"], source=cached["source"], response_type="cached")

    # Stage 5: Scope
    if not is_in_scope(message):
        elapsed = (time.time() - start) * 1000
        await _log(conn, message, OUT_OF_SCOPE_REPLY, "", "out_of_scope", elapsed)
        return ChatResponse(answer=OUT_OF_SCOPE_REPLY, source="", response_type="out_of_scope")

    # Stage 6: RAG
    import asyncio
    chunks = await asyncio.to_thread(retrieve, norm_key)

    # Stage 7: Gemini
    result = await generate_answer(message, chunks)

    # Stage 8: Cache save
    source_str = result.get("source", "") or format_sources(chunks)
    answer_text = result.get("answer", "")
    await save_cache(norm_key, answer_text, source_str, conn)

    # Stage 9: Return
    elapsed = (time.time() - start) * 1000
    await _log(conn, message, answer_text, source_str, "rag", elapsed)
    logger.info(f"Chat processed in {elapsed:.0f}ms | type=rag | key='{norm_key}'")

    return ChatResponse(answer=answer_text, source=source_str, response_type="rag")


async def _log(conn, question, answer, source, response_type, elapsed_ms):
    """Persist a chat interaction to the chat_logs table."""
    try:
        await conn.execute(
            "INSERT INTO chat_logs (question, answer, source, response_type, response_time_ms) VALUES (%s, %s, %s, %s, %s)",
            (question, answer, source, response_type, round(elapsed_ms, 2)),
        )
        await conn.commit()
    except Exception as e:
        await conn.rollback()
        logger.error(f"Failed to log chat: {e}")
