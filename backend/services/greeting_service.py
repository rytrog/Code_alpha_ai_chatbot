"""
Greeting Service — instant responses for greetings (no AI call).
Loaded once at module level for <50 ms response time.
"""
import json
import random
from pathlib import Path

# ── Load greetings data once ──
_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "greetings.json"

with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    _GREETINGS_DATA = json.load(_f)

_GREETING_WORDS = [g.lower() for g in _GREETINGS_DATA.get("greetings", [])]
_RESPONSES = _GREETINGS_DATA.get("responses", [
    "Hello! Welcome to the University Assistant. How can I help you today?"
])
_IDENTITY_QUERIES = [i.lower() for i in _GREETINGS_DATA.get("identity_queries", [])]
_IDENTITY_RESPONSE = _GREETINGS_DATA.get(
    "identity_response",
    "Hello! I am the official enquiry assistant for AITD Kanpur."
)


def check_greeting(message: str) -> str | None:
    """
    Return a random greeting response if *message* is a greeting,
    otherwise return None.  No AI call is made.
    """
    msg = message.lower().strip()
    
    # Strip basic trailing punctuation for exact comparison
    clean_msg = msg.rstrip("?!.,;:")

    # Check identity queries first
    for query in _IDENTITY_QUERIES:
        if clean_msg == query:
            return _IDENTITY_RESPONSE

    # Check if the entire message is a greeting or starts with one
    for word in _GREETING_WORDS:
        if clean_msg == word or clean_msg.startswith(word + " ") or clean_msg.startswith(word + "!") or clean_msg.startswith(word + ","):
            return random.choice(_RESPONSES)

    return None


