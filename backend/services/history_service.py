"""
History Service — manages session chat history and query condensation.
"""
import asyncio
import time
from config import settings
from utils.logger import logger
from services.llm_service import _get_gemini_client, _get_openai_client, _get_httpx_client


async def save_message(session_id: str, role: str, content: str, conn) -> None:
    """Save a chat message and enforce the sliding memory turns limit."""
    if not session_id or not content:
        return

    try:
        # Save user/assistant turn
        await conn.execute(
            "INSERT INTO chat_history (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content)
        )
        await conn.commit()

        # Enforce memory turn window (MAX_MEMORY_TURNS * 2 messages total)
        limit = settings.MAX_MEMORY_TURNS * 2
        await conn.execute(
            """DELETE FROM chat_history 
               WHERE session_id = %s 
               AND id NOT IN (
                   SELECT id FROM chat_history 
                   WHERE session_id = %s 
                   ORDER BY created_at DESC, id DESC
                   LIMIT %s
               )""",
            (session_id, session_id, limit)
        )
        await conn.commit()

        # Auto-purge any stale chat history older than 1 hour globally (inactivity cleanup)
        await conn.execute(
            "DELETE FROM chat_history WHERE created_at < NOW() - INTERVAL '1 hour'"
        )
        await conn.commit()
    except Exception as e:
        await conn.rollback()
        logger.error(f"Memory | Failed to save message for session '{session_id}': {e}")


async def get_history(session_id: str, conn) -> list[dict]:
    """Retrieve recent turns for the session in chronological order (oldest first)."""
    if not session_id:
        return []

    try:
        limit = settings.MAX_MEMORY_TURNS * 2
        cursor = await conn.execute(
            """SELECT role, content FROM (
                   SELECT id, role, content, created_at FROM chat_history
                   WHERE session_id = %s
                   ORDER BY created_at DESC, id DESC
                   LIMIT %s
               ) sub
               ORDER BY created_at ASC, id ASC""",
            (session_id, limit)
        )
        rows = await cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]
    except Exception as e:
        logger.error(f"Memory | Failed to retrieve history for session '{session_id}': {e}")
        return []


async def condense_query(question: str, history: list[dict]) -> str:
    """
    Rephrase a follow-up query to be standalone based on the chat history.
    If the question is standalone, it is returned as-is.
    """
    if not history:
        return question

    provider = settings.LLM_PROVIDER.lower().strip()
    model_name = settings.LLM_MODEL
    api_key = settings.LLM_API_KEY
    base_url = settings.LLM_BASE_URL

    # Legacy configuration fallback logic
    if not api_key or api_key == "SET_YOUR_GEMINI_API_KEY_HERE":
        if provider == "gemini":
            api_key = settings.GEMINI_API_KEY
            model_name = settings.GEMINI_MODEL

    if not api_key or api_key in ("SET_YOUR_GEMINI_API_KEY_HERE", ""):
        logger.warning("Memory | API key not configured for condensation; using original query.")
        return question

    # Format chat history for prompt
    history_lines = []
    for turn in history:
        role = "User" if turn["role"] == "user" else "Assistant"
        history_lines.append(f"{role}: {turn['content']}")
    history_str = "\n".join(history_lines)

    system_prompt = (
        "You are a query contextualizer for a university RAG system.\n"
        "Given the conversation history and a follow-up question, rephrase the follow-up question into a standalone, search-friendly query.\n"
        "CRITICAL: If the follow-up question is already a complete, standalone question that does not refer to previous turns (e.g. contains specific nouns like AITD, library, B.Tech fees, HOD, and no vague pronouns), you MUST return the follow-up question EXACTLY as-is, word-for-word, without any changes.\n"
        "Do NOT answer the question. Do NOT add any pleasantries, intro, or explanation. Output ONLY the rephrased question (or the original if already standalone)."
    )

    user_content = (
        f"Conversation History:\n{history_str}\n\n"
        f"Follow-up Question: {question}\n\n"
        "Standalone Rephrased Question:"
    )

    try:
        if provider == "gemini":
            client = _get_gemini_client(api_key)
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=f"{system_prompt}\n\n{user_content}",
            )
            text = response.text.strip() if response.text else question
            logger.info(f"Memory | Rephrased query: '{question}' -> '{text}'")
            return text

        elif provider in ("openai", "openai_compatible", "groq"):
            client_base_url = base_url
            if provider == "groq" and not client_base_url:
                client_base_url = "https://api.groq.com/openai/v1"

            client = _get_openai_client(api_key, client_base_url)

            # Auto-correct spelling typo
            actual_model = model_name
            if "Ilama" in actual_model:
                actual_model = actual_model.replace("Ilama", "llama")

            response = await client.chat.completions.create(
                model=actual_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=100,
                temperature=0.0,
            )
            text = response.choices[0].message.content.strip() if response.choices else question
            logger.info(f"Memory | Rephrased query: '{question}' -> '{text}'")
            return text

        elif provider == "anthropic":
            client = _get_httpx_client()
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model_name,
                "max_tokens": 100,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.0
            }
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            text = data["content"][0]["text"].strip() if data.get("content") else question
            logger.info(f"Memory | Rephrased query: '{question}' -> '{text}'")
            return text

        else:
            return question

    except Exception as e:
        logger.error(f"Memory | Failed to rephrase query: {e}")
        return question
