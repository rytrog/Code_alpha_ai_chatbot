"""
Question Normalizer — produces a canonical cache key from any phrasing.

Multiple phrasings map to the same key:
  "What is the hostel fee?"   → "hostel fee"
  "Hostel charges"            → "hostel charges"   (different enough to keep)
  "Tell me about hostel fee"  → "hostel fee"
"""
import json
import re
from pathlib import Path

# ── Load stopwords once ──
_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "stopwords.json"

with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    _STOPWORDS: set[str] = set(json.load(_f).get("stopwords", []))


def normalize(text: str) -> str:
    """
    Normalise a user question into a canonical cache key.
    Steps:
      1. Lowercase
      2. Remove punctuation
      3. Remove stopwords
      4. Collapse whitespace & trim
    """
    # Lowercase
    text = text.lower()

    # Remove all non-alphanumeric characters (keep spaces)
    text = re.sub(r"[^a-z0-9\s]", "", text)

    # Remove stopwords
    words = text.split()
    words = [w for w in words if w not in _STOPWORDS]

    # Collapse whitespace
    return " ".join(words).strip()
