"""
Static Response Engine — handles metadata queries (Location, Contact, Developers, Identity).
Serves instant answers, bypassing FAQ, cache, and LLM stages.
"""
import json
import re
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "greetings.json"

with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    _GREETINGS_DATA = json.load(_f)

# Load queries and responses from greetings.json
_IDENTITY_QUERIES = [i.lower() for i in _GREETINGS_DATA.get("identity_queries", [])]
_IDENTITY_RESPONSE = _GREETINGS_DATA.get(
    "identity_response",
    "Hello! I am the official enquiry assistant for AITD Kanpur."
)

_DEV_QUERIES = [d.lower() for d in _GREETINGS_DATA.get("developer_queries", [])]
_DEV_RESPONSE = _GREETINGS_DATA.get(
    "developer_response",
    "I was designed and engineered by the AI Innovators team under the supervision of Prof. Sri Nath Dwivedi Sir."
)

# Separate Location queries into Address vs Routes/Map
# Separate Location keywords into Address vs Routes/Map
_ADDRESS_KEYWORDS = {"address", "location", "located", "where is", "situated", "pincode", "pin code"}
_ROUTE_KEYWORDS = {"reach", "route", "routes", "map", "directions", "way to", "how to go", "how to get"}

_ADDRESS_RESPONSE = (
    "### 📍 AITD Kanpur Address\n"
    "* **Institute Name**: Dr. Ambedkar Institute of Technology for Divyangjan (AITD), Kanpur\n"
    "* **Street Address**: Awadhpuri, Opposite Rama Dental College, Khyora\n"
    "* **City & State**: Kanpur, Uttar Pradesh\n"
    "* **PIN Code**: **208024**\n"
    "* **Key Landmarks**: Opposite Rama Dental College, Near Gurudev Chauraha"
)

_ROUTE_RESPONSE = (
    "### 🗺️ AITD Kanpur Route Guide\n"
    "* **Route A (from Kanpur Central Station)**: Kanpur Central → GT Road → Rawatpur Crossing → Awadhpuri → AITD (~11 km)\n"
    "* **Route B (from Rawatpur Station)**: Rawatpur Station → Kakadeo → Awadhpuri → AITD (~2.5 km)\n"
    "* **Route C (from Jhakarkati Bus Stand)**: Jhakarkati Bus Stand → GT Road → Rawatpur Crossing → Awadhpuri → AITD\n"
    "* **Visual Map**: Click the link below to view the interactive campus route:\n\n"
    "[MAP_ROUTE]"
)

# New static contact configuration
_CONTACT_QUERIES = [
    "contact details", "contact information", "phone number", "email address",
    "contact", "phone", "email", "how to contact", "office hours",
    "office timings", "timings", "timing", "contact number", "phone details"
]
_CONTACT_RESPONSE = (
    "📞 **AITD Kanpur Contact Details**\n\n"
    "* **Phone:** +91-0512-2583221\n"
    "* **Email:** info@aitd.ac.in or director@aitd.ac.in\n"
    "* **Address:** Awadhpuri, Opposite Rama Dental College, Kanpur - 208024, Uttar Pradesh\n"
    "* **Office Hours:** 9:00 AM to 5:00 PM, Monday to Friday"
)

# Developer verification names for substring matching
_DEVELOPER_NAMES = {
    "vishal kumar", "vishakhdutt", "awadhesh", "indrakesh",
    "sri nath dwivedi", "ai innovators"
}


def check_static(message: str) -> str | None:
    """
    Check if the user message matches any static response topic.
    Returns the static reply string if matched, otherwise None.
    """
    msg = message.lower().strip()
    clean_msg = msg.rstrip("?!.,;:")

    # 1. Check Developer / Team Members / Who Built Chatbot
    for query in _DEV_QUERIES:
        if clean_msg == query:
            return _DEV_RESPONSE
            
    # Substring check for developer names ONLY if query is asking about bot creation/development
    bot_build_keywords = {"you", "your", "chatbot", "bot", "app", "assistant", "this", "built", "created", "designed", "engineered", "made", "developer", "creator", "programmer"}
    msg_has_bot_context = any(k in clean_msg for k in bot_build_keywords)
    for name in _DEVELOPER_NAMES:
        if name in clean_msg and msg_has_bot_context:
            return _DEV_RESPONSE

    # Substring check for developer queries with bot keywords
    for query in _DEV_QUERIES:
        query_has_bot = any(k in query for k in bot_build_keywords)
        if query_has_bot or msg_has_bot_context:
            if clean_msg.startswith(query + " ") or clean_msg.endswith(" " + query) or f" {query} " in f" {clean_msg} ":
                return _DEV_RESPONSE

    # 2. Check Location & Route Map Queries
    # If the user is asking about specific routing/origins (like from Kanpur Central/Jhakarkati/Airport),
    # let the RAG system handle it using how_to_reach_AITD.txt which contains precise details.
    specific_routes = {"from", "central", "bus", "airport", "station", "railway"}
    has_specific_route = any(w in clean_msg for w in specific_routes)
    if not has_specific_route:
        # Check specific Route / Map keywords
        is_route_query = any(kw in clean_msg for kw in _ROUTE_KEYWORDS)
        if is_route_query:
            return _ROUTE_RESPONSE

        # Check Address / Location keywords
        is_address_query = any(kw in clean_msg for kw in _ADDRESS_KEYWORDS) or "where" in clean_msg
        if is_address_query:
            return _ADDRESS_RESPONSE

    # 3. Check Contact Information
    for query in _CONTACT_QUERIES:
        if clean_msg == query or query in clean_msg:
            return _CONTACT_RESPONSE

    # 4. Check College Information & Identity Details
    for query in _IDENTITY_QUERIES:
        if clean_msg == query or query in clean_msg:
            return _IDENTITY_RESPONSE

    return None
