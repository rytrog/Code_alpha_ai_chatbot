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


# ── Typo Correction & Fuzzy Matching Constants ──
TYPO_DICT = {
    "helo": "hello",
    "heyl": "hey",
    "thenks": "thanks",
    "thanku": "thank you",
    "gud": "good",
    "morningg": "morning",
    "admision": "admission",
    "hostal": "hostel",
    "scholership": "scholarship",
    "deprtment": "department",
    "fe": "fee",
    "tranning": "training",
    "cours": "course",
    "cources": "courses",
    "activitys": "activities",
    "faciltiy": "facility",
    "facilties": "facilities",
    "ragin": "ragging",
    "antiragin": "antiragging",
    "collge": "college",
    "colg": "college",
    "univ": "university",
}

MULTI_WORD_TYPOS = {
    "gud morning": "good morning",
    "gud afternoon": "good afternoon",
    "gud evening": "good evening",
    "gud night": "good night",
    "gudnoon": "good noon",
    "goodnoon": "good noon",
}

VOCABULARY = [
    # Greetings & basic polite words
    "hello", "hey", "hi", "thanks", "thank", "good", "morning", "afternoon", "evening", "night", "noon", "welcome", "bye", "goodbye",
    # College domains
    "hostel", "admission", "scholarship", "department", "placement", "training", "fee", "fees", "structure", "campus",
    "location", "facility", "facilities", "student", "activity", "activities", "course", "courses", "degree", "diploma",
    "ragging", "antiragging", "information", "institute", "purpose", "chatbot", "reach", "library", "canteen", "labs",
    "placementdetails", "studentactivity", "feestructure", "college", "kanpur", "university", "syllabus", "academics"
]


def normalize_query(user_message: str) -> str:
    """
    Expose a single function to normalize user queries before any downstream processing.
    Steps:
      1. Convert text to lowercase.
      2. Remove unwanted punctuation (replace non-alphanumeric/non-space with space).
      3. Remove extra spaces (split & clean).
      4. Correct common known typos using predefined TYPO_DICT/MULTI_WORD_TYPOS.
      5. Apply fuzzy matching using RapidFuzz.
    """
    if not user_message:
        return ""

    # 1. Lowercase text
    text = user_message.lower()

    # 2. Normalize punctuation (replace with space to prevent words joining)
    text = re.sub(r"[^\w\s]", " ", text)

    # 3. Collapse extra spaces
    words = text.split()
    if not words:
        return ""

    clean_phrase = " ".join(words)

    # 4. Correct multi-word known typos first
    if clean_phrase in MULTI_WORD_TYPOS:
        return MULTI_WORD_TYPOS[clean_phrase]

    # Process word-by-word
    corrected_words = []
    
    # Import rapidfuzz inline to prevent import errors if packages are setting up
    try:
        from rapidfuzz import process, fuzz
        has_rapidfuzz = True
    except ImportError:
        has_rapidfuzz = False

    for word in words:
        # Step 4: Correct known single-word typos
        if word in TYPO_DICT:
            corrected_words.append(TYPO_DICT[word])
        # Step 5: Apply fuzzy matching using RapidFuzz
        elif has_rapidfuzz and len(word) > 3 and word not in VOCABULARY:
            # Extract the closest match from the domain vocabulary using fuzz.ratio
            match = process.extractOne(word, VOCABULARY, scorer=fuzz.ratio)
            if match and match[1] >= 80.0:
                corrected_words.append(match[0])
            else:
                corrected_words.append(word)
        else:
            corrected_words.append(word)

    return " ".join(corrected_words).strip()

