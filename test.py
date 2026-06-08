import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent / "backend"
sys.path.append(str(backend_path))

import asyncio
from backend.config import settings
from backend.services.llm_service import generate_answer


async def test_llm():
    print("Settings loaded successfully!")
    print(f"LLM Provider: {settings.LLM_PROVIDER}")
    print(f"LLM Model: {settings.LLM_MODEL}")
    print(f"LLM API Key configured: {settings.LLM_API_KEY != 'SET_YOUR_GEMINI_API_KEY_HERE' and settings.LLM_API_KEY != ''}")
    
    # Test with empty context chunks (should return NO_ANSWER_MSG fallback immediately)
    print("\nTesting immediate fallback (empty context chunks)...")
    res = await generate_answer("Hello", [])
    print("Result:", res)
    assert "not available in our records" in res["answer"], "Failed empty context fallback check."
    print("Fallback check passed!")

    # Test with actual context chunks
    print("\nTesting LLM service execution with context chunks...")
    res2 = await generate_answer("What courses are offered?", [{"text": "AITD offers B.Tech.", "document_name": "syllabus.pdf"}])
    print("Result:", res2)
    # The call can succeed, return a placeholder error, or return a temporary failure message,
    # but it must handle it gracefully and not throw an unhandled exception.
    assert isinstance(res2, dict) and "answer" in res2, "Response should be a dictionary with an 'answer' key."
    print("Execution check passed (no crashes)!")


if __name__ == "__main__":
    asyncio.run(test_llm())