"""
Gemini Service — generates answers using Gemini 2.5 Flash.
Strict rules: answer ONLY from provided context, max 200 words,
never hallucinate.
"""
import asyncio
from pathlib import Path
from google import genai
from config import settings
from utils.logger import logger

# ── Load the prompt template once ──
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "university_prompt.txt"
with open(_PROMPT_PATH, "r", encoding="utf-8") as _f:
    _SYSTEM_PROMPT = _f.read().strip()

# Fallback when context has no answer
NO_ANSWER_MSG = "The requested information is not available in our records. Please contact AITD administration at info@aitd.ac.in or call +91-0512-2583221 for further assistance."


async def generate_answer(question: str, context_chunks: list[dict]) -> dict:
    """
    Call Gemini 2.5 Flash with retrieved context.

    Returns {"answer": str, "source": str}.
    If API key is not set or context is empty, returns a fallback message.
    """
    # Guard: no context available
    if not context_chunks:
        return {"answer": NO_ANSWER_MSG, "source": ""}

    # Guard: API key not configured
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "SET_YOUR_GEMINI_API_KEY_HERE":
        logger.error("GEMINI_API_KEY is not configured.")
        return {
            "answer": "AI service is not configured. Please contact the administrator.",
            "source": "",
        }

    # Build context string from chunks
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        source_label = chunk.get("document_name", "Unknown")
        page = chunk.get("page_number", "")
        page_str = f" (Page {page})" if page else ""
        context_parts.append(f"[Source {i}: {source_label}{page_str}]\n{chunk['text']}")

    context_text = "\n\n".join(context_parts)

    # Build the full prompt
    user_prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"--- CONTEXT START ---\n{context_text}\n--- CONTEXT END ---\n\n"
        f"Question: {question}\n\n"
        f"Answer (max {settings.MAX_ANSWER_WORDS} words):"
    )

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Run the sync Gemini SDK call in a thread to avoid blocking
        # the async event loop (the SDK's generate_content is synchronous)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=user_prompt,
        )
        answer_text = response.text.strip() if response.text else NO_ANSWER_MSG

        # Build source string from chunks used
        sources = []
        for chunk in context_chunks:
            src = chunk.get("document_name", "")
            page = chunk.get("page_number", "")
            label = f"{src} (Page {page})" if page else src
            if label and label not in sources:
                sources.append(label)

        source_str = ", ".join(sources) if sources else ""

        return {"answer": answer_text, "source": source_str}

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {
            "answer": "I apologize, but I could not generate a response at this moment. Please try again later.",
            "source": "",
        }
