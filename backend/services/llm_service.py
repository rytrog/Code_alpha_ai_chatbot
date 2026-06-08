"""
LLM Service — generates answers using a generalized LLM provider interface.
Supports Gemini, OpenAI, Anthropic, and OpenAI-compatible providers.
Strict rules: answer ONLY from provided context, max 200 words,
never hallucinate.
"""
import asyncio
from pathlib import Path
from google import genai
from openai import AsyncOpenAI
import httpx
from config import settings
from utils.logger import logger

# ── Load the prompt template once ──
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "university_prompt.txt"
with open(_PROMPT_PATH, "r", encoding="utf-8") as _f:
    _SYSTEM_PROMPT = _f.read().strip()

# Fallback when context has no answer
NO_ANSWER_MSG = "The requested information is not available in our records. Please contact AITD administration at info@aitd.ac.in or call +91-0512-2583221 for further assistance."

# ── Global Cached Clients for Connection Pooling ──
_GEMINI_CLIENT = None
_OPENAI_CLIENT = None
_OPENAI_CLIENT_KEY = None  # To track if API key or base URL changed
_OPENAI_CLIENT_BASE = None
_HTTPX_CLIENT = None


def _get_gemini_client(api_key: str) -> genai.Client:
    """Gets or initializes the cached Gemini client."""
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        logger.info("Initializing new connection-pooled Gemini client.")
        _GEMINI_CLIENT = genai.Client(api_key=api_key)
    return _GEMINI_CLIENT


def _get_openai_client(api_key: str, base_url: str = None) -> AsyncOpenAI:
    """Gets or initializes the cached OpenAI client, re-initializing if config changes."""
    global _OPENAI_CLIENT, _OPENAI_CLIENT_KEY, _OPENAI_CLIENT_BASE
    
    # Re-initialize client if key or base URL changed (e.g. settings modified at runtime)
    if (_OPENAI_CLIENT is None or 
            _OPENAI_CLIENT_KEY != api_key or 
            _OPENAI_CLIENT_BASE != base_url):
        logger.info(f"Initializing new connection-pooled OpenAI client. Base URL: {base_url}")
        _OPENAI_CLIENT = AsyncOpenAI(api_key=api_key, base_url=base_url or None)
        _OPENAI_CLIENT_KEY = api_key
        _OPENAI_CLIENT_BASE = base_url
        
    return _OPENAI_CLIENT


def _get_httpx_client() -> httpx.AsyncClient:
    """Gets or initializes the cached HTTPX client for generic calls (like Anthropic)."""
    global _HTTPX_CLIENT
    if _HTTPX_CLIENT is None:
        logger.info("Initializing new connection-pooled HTTPX client.")
        _HTTPX_CLIENT = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=20)
        )
    return _HTTPX_CLIENT


async def generate_answer(question: str, context_chunks: list[dict]) -> dict:
    """
    Call the configured LLM API (Gemini, OpenAI, Anthropic, or OpenAI-compatible)
    with retrieved context.

    Returns {"answer": str, "source": str}.
    """
    # Guard: no context available
    if not context_chunks:
        return {"answer": NO_ANSWER_MSG, "source": ""}

    provider = settings.LLM_PROVIDER.lower().strip()
    model_name = settings.LLM_MODEL
    api_key = settings.LLM_API_KEY
    base_url = settings.LLM_BASE_URL

    # Legacy configuration fallback logic for out-of-the-box compatibility
    if not api_key or api_key == "SET_YOUR_GEMINI_API_KEY_HERE":
        if provider == "gemini":
            api_key = settings.GEMINI_API_KEY
            model_name = settings.GEMINI_MODEL

    # Guard: API key not configured
    if not api_key or api_key in ("SET_YOUR_GEMINI_API_KEY_HERE", ""):
        logger.error(f"API key is not configured for provider '{provider}'.")
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
        if provider == "gemini":
            client = _get_gemini_client(api_key)
            # Run the sync Gemini SDK call in a thread to avoid blocking the event loop
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=user_prompt,
            )
            answer_text = response.text.strip() if response.text else NO_ANSWER_MSG

        elif provider in ("openai", "openai_compatible", "groq"):
            client_base_url = base_url
            if provider == "groq" and not client_base_url:
                client_base_url = "https://api.groq.com/openai/v1"

            client = _get_openai_client(api_key, client_base_url)

            # Auto-correct common spelling typo: 'Ilama' -> 'llama'
            actual_model = model_name
            if "Ilama" in actual_model:
                actual_model = actual_model.replace("Ilama", "llama")

            try:
                response = await client.chat.completions.create(
                    model=actual_model,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=settings.MAX_ANSWER_WORDS * 2,
                    temperature=0.0,
                )
                answer_text = response.choices[0].message.content.strip() if response.choices else NO_ANSWER_MSG
            except Exception as e:
                import openai
                is_rate_limit = isinstance(e, openai.RateLimitError) or "rate limit" in str(e).lower() or "429" in str(e)
                if is_rate_limit and provider == "groq":
                    fallbacks = ["llama-3.1-8b-instant", "qwen/qwen3-32b", "openai/gpt-oss-20b", "groq/compound-mini"]
                    fallbacks = [m for m in fallbacks if m != actual_model]
                    logger.warning(f"Groq primary model '{actual_model}' rate-limited. Trying fallbacks: {fallbacks}")
                    success = False
                    for fallback_model in fallbacks:
                        try:
                            logger.info(f"Trying Groq fallback model '{fallback_model}'...")
                            response = await client.chat.completions.create(
                                model=fallback_model,
                                messages=[
                                    {"role": "user", "content": user_prompt}
                                ],
                                max_tokens=settings.MAX_ANSWER_WORDS * 2,
                                temperature=0.0,
                            )
                            answer_text = response.choices[0].message.content.strip() if response.choices else NO_ANSWER_MSG
                            logger.info(f"Groq fallback model '{fallback_model}' succeeded!")
                            success = True
                            break
                        except Exception as fe:
                            logger.warning(f"Groq fallback model '{fallback_model}' failed: {fe}")
                    if not success:
                        raise e
                else:
                    raise e

        elif provider == "anthropic":
            client = _get_httpx_client()
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model_name,
                "max_tokens": settings.MAX_ANSWER_WORDS * 2,
                "messages": [
                    {"role": "user", "content": user_prompt}
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
            answer_text = data["content"][0]["text"].strip() if data.get("content") else NO_ANSWER_MSG

        else:
            logger.error(f"Unsupported LLM provider configured: {provider}")
            return {
                "answer": f"System error: LLM provider '{provider}' is not supported.",
                "source": "",
            }

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
        logger.error(f"LLM API error ({provider}): {e}")
        return {
            "answer": "I apologize, but I could not generate a response at this moment. Please try again later.",
            "source": "",
        }
