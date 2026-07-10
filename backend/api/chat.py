"""
Chat API — POST /api/chat
Multi-stage pipeline using psycopg pool.

PIPELINE STAGES:
  0. Input Validation
  1. Greeting Engine
  2. Static Response Engine
  3. Normalization
  4. FAQ Engine (PostgreSQL)
  5. Cache Engine (positive-only)
  6. Scope Checker (permissive)
  7. RAG Retrieval (ChromaDB) — dual query strategy
  8. LLM Generation
  9. Website Fallback (aitd.ac.in) — if LLM returned negative answer
  10. Cache (positive only) + Logging
  11. Return Response

KEY RULES:
  - Negative answers are NEVER cached.
  - If RAG fails, website fallback is tried before giving up.
  - Original message is used for embedding search (not normalized key).
"""
import time
import asyncio
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from config import settings
from database.db import get_conn
from services.greeting_service import check_greeting
from services.static_service import check_static
from services.faq_service import check_faq
from services.normalize_service import normalize, normalize_query
from services.cache_service import get_cached, save_cache, _is_negative_answer
from services.scope_service import is_in_scope, OUT_OF_SCOPE_REPLY
from services.rag_service import retrieve
from services.llm_service import generate_answer
from services.web_search_service import search_and_ingest
from services.source_service import format_sources
from services.history_service import save_message, get_history, condense_query
from utils.validator import validate_message
from utils.logger import logger

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="User question")
    session_id: str | None = Field(None, description="Unique session ID for the user")


class ChatResponse(BaseModel):
    answer: str
    source: str = ""
    response_type: str = "rag"


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, conn=Depends(get_conn)):
    """Process a user question through the multi-stage pipeline."""
    start = time.time()
    message = body.message.strip()

    # Stage 0: Input Validation
    is_valid, err = validate_message(message)
    if not is_valid:
        return ChatResponse(answer=err, source="", response_type="error")

    # Stage 0.5: Query Normalization Layer
    message = normalize_query(message)

    # Extract or fallback session_id
    session_id = body.session_id
    if not session_id:
        session_id = request.client.host if request.client else "unknown"

    # Pre-fetch history early to determine if this is a follow-up query
    history = []
    if settings.ENABLE_CONVERSATIONAL_MEMORY:
        try:
            history = await get_history(session_id, conn)
        except Exception as e:
            logger.error(f"Memory failsafe: fell back to single-turn due to error: {e}")

    # Stage 0.6: Scope Checker (runs early for first turns to reject off-topic questions)
    if not history:
        if not is_in_scope(message):
            elapsed = (time.time() - start) * 1000
            await _log(conn, message, OUT_OF_SCOPE_REPLY, "", "out_of_scope", elapsed)
            return ChatResponse(answer=OUT_OF_SCOPE_REPLY, source="", response_type="out_of_scope")

    # Stage 1: Greeting Engine
    greeting = check_greeting(message, session_id)
    if greeting:
        elapsed = (time.time() - start) * 1000
        await _log(conn, message, greeting, "", "greeting", elapsed)
        return ChatResponse(answer=greeting, source="", response_type="greeting")

    # Stage 2: Static Response Engine
    static_reply = check_static(message)
    if static_reply:
        elapsed = (time.time() - start) * 1000
        await _log(conn, message, static_reply, "", "static", elapsed)
        if settings.ENABLE_CONVERSATIONAL_MEMORY:
            try:
                await save_message(session_id, "user", message, conn)
                await save_message(session_id, "assistant", static_reply, conn)
            except Exception as e:
                logger.error(f"Memory | Failed to save static turns: {e}")
        return ChatResponse(answer=static_reply, source="", response_type="static")

    # Stage 2.5: Fast-Path Cache & FAQ Engine (Original Query Direct Lookup)
    orig_norm_key = normalize(message)
    logger.info(f"Pipeline | Fast-path lookup for original query key: '{orig_norm_key}'")

    # Check FAQ for original query
    faq_result = await check_faq(orig_norm_key, conn)
    if faq_result:
        elapsed = (time.time() - start) * 1000
        logger.info(f"Pipeline | Fast-path FAQ HIT for '{orig_norm_key}'")
        await _log(conn, message, faq_result["answer"], faq_result["source"], "faq", elapsed)
        if settings.ENABLE_CONVERSATIONAL_MEMORY:
            try:
                await save_message(session_id, "user", message, conn)
                await save_message(session_id, "assistant", faq_result["answer"], conn)
            except Exception as e:
                logger.error(f"Memory | Failed to save FAQ turns: {e}")
        return ChatResponse(answer=faq_result["answer"], source=faq_result["source"], response_type="faq")

    # Check Cache for original query
    cached = await get_cached(orig_norm_key, conn)
    if cached:
        elapsed = (time.time() - start) * 1000
        logger.info(f"Pipeline | Fast-path Cache HIT for '{orig_norm_key}'")
        await _log(conn, message, cached["answer"], cached["source"], "cached", elapsed)
        if settings.ENABLE_CONVERSATIONAL_MEMORY:
            try:
                await save_message(session_id, "user", message, conn)
                await save_message(session_id, "assistant", cached["answer"], conn)
            except Exception as e:
                logger.error(f"Memory | Failed to save cached turns: {e}")
        return ChatResponse(answer=cached["answer"], source=cached["source"], response_type="cached")

    # Stage 3: Conversational History Condensation (only on fast-path miss)
    search_query = message
    if history:
        try:
            search_query = await condense_query(message, history)
            search_query = normalize_query(search_query)
        except Exception as e:
            logger.error(f"Memory failsafe: fell back to single-turn due to error: {e}")

    # Stage 4: Normalization Engine (for rephrased query)
    norm_key = normalize(search_query)
    logger.info(f"Pipeline | norm_key='{norm_key}' | search_query='{search_query}' | original='{message}'")

    # Stage 5: Rephrased Cache & FAQ Engine (only if key differs from original query)
    if norm_key != orig_norm_key:
        # Check FAQ for rephrased query
        faq_result = await check_faq(norm_key, conn)
        if faq_result:
            elapsed = (time.time() - start) * 1000
            logger.info(f"Pipeline | Rephrased FAQ HIT for '{norm_key}'")
            await _log(conn, message, faq_result["answer"], faq_result["source"], "faq", elapsed)
            if settings.ENABLE_CONVERSATIONAL_MEMORY:
                try:
                    await save_message(session_id, "user", message, conn)
                    await save_message(session_id, "assistant", faq_result["answer"], conn)
                except Exception as e:
                    logger.error(f"Memory | Failed to save FAQ turns: {e}")
            return ChatResponse(answer=faq_result["answer"], source=faq_result["source"], response_type="faq")

        # Check Cache for rephrased query
        cached = await get_cached(norm_key, conn)
        if cached:
            elapsed = (time.time() - start) * 1000
            logger.info(f"Pipeline | Rephrased Cache HIT for '{norm_key}'")
            await _log(conn, message, cached["answer"], cached["source"], "cached", elapsed)
            if settings.ENABLE_CONVERSATIONAL_MEMORY:
                try:
                    await save_message(session_id, "user", message, conn)
                    await save_message(session_id, "assistant", cached["answer"], conn)
                except Exception as e:
                    logger.error(f"Memory | Failed to save cached turns: {e}")
            return ChatResponse(answer=cached["answer"], source=cached["source"], response_type="cached")


    # Stage 6: Scope Checker for rephrased queries (only if check wasn't run early)
    if history:
        if not is_in_scope(search_query):
            elapsed = (time.time() - start) * 1000
            await _log(conn, message, OUT_OF_SCOPE_REPLY, "", "out_of_scope", elapsed)
            return ChatResponse(answer=OUT_OF_SCOPE_REPLY, source="", response_type="out_of_scope")

    # Stage 7: Retrieval (ChromaDB) — DUAL QUERY STRATEGY
    # Primary: use the search_query for embedding search (better semantics)
    chunks = await asyncio.to_thread(retrieve, search_query)

    # Fallback: if search_query got 0 chunks, try normalized key
    if not chunks and norm_key != search_query.lower():
        logger.info(f"Pipeline | Primary RAG returned 0 chunks, trying norm_key: '{norm_key}'")
        chunks = await asyncio.to_thread(retrieve, norm_key)

    # Stage 8: LLM Generation
    # generate_answer handles empty chunks (returns NO_ANSWER_MSG)
    result = await generate_answer(message, chunks, history)
    answer_text = result.get("answer", "")
    source_str = result.get("source", "") or format_sources(chunks)

    # Stage 9: Website Fallback
    # If the LLM returned a negative answer, try scraping aitd.ac.in
    if _is_negative_answer(answer_text):
        logger.info(f"Pipeline | LLM returned negative answer, trying website fallback...")
        try:
            web_chunks = await search_and_ingest(search_query)
            if web_chunks:
                # Combine with top 2 RAG chunks to stay within token limits
                all_chunks = chunks[:2] + web_chunks
                # Re-run LLM with the combined context
                web_result = await generate_answer(message, all_chunks, history)
                web_answer = web_result.get("answer", "")
                web_source = web_result.get("source", "") or format_sources(web_chunks)

                # Only use website answer if it's positive (actually found something)
                if not _is_negative_answer(web_answer):
                    logger.info(f"Pipeline | Website fallback SUCCESS")
                    answer_text = web_answer
                    source_str = web_source
                else:
                    logger.info(f"Pipeline | Website fallback also returned negative")
            else:
                logger.info(f"Pipeline | Website fallback returned 0 chunks")
        except Exception as e:
            logger.error(f"Pipeline | Website fallback error: {e}")

    # Stage 10: Cache + Logging
    # save_cache internally checks for negative answers and WON'T cache them
    await save_cache(norm_key, answer_text, source_str, conn)

    # Stage 11: Return Response
    elapsed = (time.time() - start) * 1000
    await _log(conn, message, answer_text, source_str, "rag", elapsed)
    logger.info(f"Pipeline | DONE in {elapsed:.0f}ms | chunks={len(chunks)} | key='{norm_key}'")

    if settings.ENABLE_CONVERSATIONAL_MEMORY:
        try:
            await save_message(session_id, "user", message, conn)
            await save_message(session_id, "assistant", answer_text, conn)
        except Exception as e:
            logger.error(f"Memory | Failed to save RAG turns: {e}")

    return ChatResponse(answer=answer_text, source=source_str, response_type="rag")


async def _log(conn, question, answer, source, response_type, elapsed_ms):
    """Persist a chat interaction to the chat_logs table."""
    # Do not log negative/failure/out-of-scope responses to the database
    if _is_negative_answer(answer):
        logger.info(f"Skipped database logging for negative/fallback response to query: '{question}'")
        return

    try:
        await conn.execute(
            "INSERT INTO chat_logs (question, answer, source, response_type, response_time_ms) VALUES (%s, %s, %s, %s, %s)",
            (question, answer, source, response_type, round(elapsed_ms, 2)),
        )
        await conn.commit()
    except Exception as e:
        await conn.rollback()
        logger.error(f"Failed to log chat: {e}")
