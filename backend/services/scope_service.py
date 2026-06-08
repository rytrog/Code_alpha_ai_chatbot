"""
Scope Checker — rejects non-university questions before any AI call.

Allowed topics:  admission, exam, hostel, faculty, department, course,
                 syllabus, fees, scholarship, library, registrar,
                 vice chancellor, academic calendar, circular, notice,
                 semester, campus, degree, graduation, tuition,
                 placement, research, convocation, result, timetable,
                 location, address, contact, phone, email, website

Blocked categories:  politics, religion, coding, entertainment,
                     personal advice, general knowledge
"""
import re
import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "university_keywords.json"

with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    _KEYWORDS: list[str] = [k.lower() for k in json.load(_f).get("keywords", [])]

# Explicit rejection phrases
_BLOCKED_PATTERNS: list[str] = [
    "capital of", "president of", "prime minister", "who won",
    "write code", "write python", "write java", "write program",
    "artificial intelligence definition", "machine learning definition",
    "recipe for", "movie", "song", "cricket", "football", "ipl",
    "messi", "ronaldo", "politics", "religion", "god",
    "boyfriend", "girlfriend", "dating", "love advice",
]

# Compile with word boundaries to avoid false positives (e.g. "ipl" in "diploma" or "god" in "pagoda")
_BLOCKED_REGEXES: list[re.Pattern] = [
    re.compile(r'\b' + re.escape(pattern) + r'\b', re.IGNORECASE)
    for pattern in _BLOCKED_PATTERNS
]

OUT_OF_SCOPE_REPLY = (
    "Sorry, I can only answer queries related to AITD, Kanpur. "
    "Please ask questions about admissions, fees, courses, placements, "
    "hostel, faculty, departments, or other AITD-related matters."
)


def is_in_scope(message: str) -> bool:
    """
    Return True if the message should be processed by the RAG pipeline.

    Strategy:
      1. Quick-reject queries that are OBVIOUSLY off-topic (blocked patterns).
      2. If any university keyword matches, definitely in scope.
      3. DEFAULT: allow through to RAG. If the data isn't there, the LLM
         will respond with "not available" — which is better UX than a
         hard scope rejection for borderline queries.
    """
    msg = message.lower()

    # Quick reject for obviously off-topic queries (using word boundaries)
    for rx in _BLOCKED_REGEXES:
        if rx.search(msg):
            return False

    # If any university keyword matches, definitely in scope
    for keyword in _KEYWORDS:
        if keyword in msg:
            return True

    # Default: ALLOW through to RAG (permissive approach)
    # The LLM prompt already instructs it to refuse non-AITD questions,
    # and cache_service won't cache negative answers.
    return True
