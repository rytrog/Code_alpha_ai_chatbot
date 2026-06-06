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

OUT_OF_SCOPE_REPLY = (
    "Sorry, I can only answer queries related to AITD, Kanpur. "
    "Please ask questions about admissions, fees, courses, placements, "
    "hostel, faculty, departments, or other AITD-related matters."
)


def is_in_scope(message: str) -> bool:
    """
    Return True if the message relates to a university topic.
    Check blocked patterns first (quick reject), then allowed keywords.
    """
    msg = message.lower()

    # Quick reject for obviously off-topic queries
    for pattern in _BLOCKED_PATTERNS:
        if pattern in msg:
            return False

    # Check for at least one university keyword
    for keyword in _KEYWORDS:
        if keyword in msg:
            return True

    # Default: reject (strict scope)
    return False
