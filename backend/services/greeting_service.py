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

_GREETING_WORDS: list[str] = [g.lower() for g in _GREETINGS_DATA.get("greetings", [])]
_RESPONSES: list[str] = _GREETINGS_DATA.get("responses", [
    "Hello! Welcome to the University Assistant. How can I help you today?"
])


def check_greeting(message: str) -> str | None:
    """
    Return a random greeting response if *message* is a greeting,
    otherwise return None.  No AI call is made.
    """
    msg = message.lower().strip()

    # Check if the entire message is a greeting or starts with one
    for word in _GREETING_WORDS:
        if msg == word or msg.startswith(word + " ") or msg.startswith(word + "!") or msg.startswith(word + ","):
            return random.choice(_RESPONSES)

    return None
