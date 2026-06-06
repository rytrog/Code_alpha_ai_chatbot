"""
FAQ Service — answers pre-configured university questions from PostgreSQL.
"""


import difflib


async def check_faq(normalized_key: str, conn) -> dict | None:
    """Look up a normalised question key in the FAQ table, falling back to fuzzy matching."""
    # 1. Fast exact SQL match to avoid scanning all keys in database
    r = await conn.execute(
        "SELECT answer, source FROM faq WHERE normalized_key = %s", (normalized_key,)
    )
    row = await r.fetchone()
    if row:
        return {"answer": row["answer"], "source": row["source"] or "FAQ Database"}

    # 2. Fuzzy match fallback
    r = await conn.execute("SELECT normalized_key, answer, source FROM faq")
    rows = await r.fetchall()
    if not rows:
        return None

    faq_map = {row["normalized_key"]: row for row in rows if row["normalized_key"]}
    matches = difflib.get_close_matches(normalized_key, list(faq_map.keys()), n=1, cutoff=0.85)
    if matches:
        matched_key = matches[0]
        matched_row = faq_map[matched_key]
        return {
            "answer": matched_row["answer"],
            "source": matched_row["source"] or "FAQ Database",
        }

    return None
