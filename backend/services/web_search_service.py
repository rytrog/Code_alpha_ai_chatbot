"""
Web Search Service — fallback to aitd.ac.in when RAG has no answer.

When the RAG pipeline + LLM cannot answer from uploaded documents,
this service scrapes relevant pages from the AITD website and
provides the content as context for a fresh LLM attempt.

The scraped content is also auto-ingested into ChromaDB so future
queries don't need to re-scrape.
"""
import re
import asyncio
import httpx
from utils.logger import logger

# ── Known AITD website pages mapped by topic ──
# These are the most useful pages to scrape for different query topics.
AITD_PAGES = {
    "general": [
        "https://aitd.ac.in/history_and_motivation.aspx",
        "https://aitd.ac.in/vision_mission.aspx",
        "https://aitd.ac.in/future_goals.aspx",
    ],
    "department": [
        "https://aitd.ac.in/department_computer_science.aspx",
        "https://aitd.ac.in/department_IT.aspx",
        "https://aitd.ac.in/department_electrronic_engg.aspx",
        "https://aitd.ac.in/department_bio_technology.aspx",
        "https://aitd.ac.in/department_chem_engineering.aspx",
        "https://aitd.ac.in/department_applied_science.aspx",
        "https://aitd.ac.in/department_architectural_assistantship.aspx",
        "https://aitd.ac.in/department_modern_office.aspx",
    ],
    "governance": [
        "https://aitd.ac.in/director.aspx",
        "https://aitd.ac.in/dean_committee.aspx",
        "https://aitd.ac.in/board_of_governors.aspx",
    ],
    "admission": [
        "https://aitd.ac.in/academic_pro_degree.aspx",
        "https://aitd.ac.in/academic_pro_diploma.aspx",
    ],
    "faculty": [
        "https://aitd.ac.in/faculty_degree_wing.aspx",
        "https://aitd.ac.in/faculty_diploma_wing.aspx",
    ],
    "infrastructure": [
        "https://aitd.ac.in/academic_infrastructure.aspx",
        "https://aitd.ac.in/student_hostel.aspx",
        "https://aitd.ac.in/aboutlibrary.aspx",
    ],
    "placement": [
        "https://aitd.ac.in/training_placement.aspx",
    ],
    "contact": [
        "https://aitd.ac.in/contact_us.aspx",
    ],
    "anti_ragging": [
        "https://aitd.ac.in/anti_ragging.aspx",
    ],
}

# Keywords that map to topic categories
_TOPIC_KEYWORDS = {
    "department": ["department", "hod", "head of", "cse", "it ", "electronics",
                    "biotechnology", "chemical", "aiml", "ai&ml", "ai & ml",
                    "computer science", "information technology", "applied science",
                    "architecture"],
    "governance": ["director", "dean", "governor", "principal", "committee"],
    "admission": ["admission", "eligibility", "apply", "application", "jee",
                   "counselling", "cuet", "entrance", "degree", "diploma",
                   "b.tech", "btech", "m.tech", "mtech"],
    "faculty": ["faculty", "professor", "teacher", "lecturer", "staff"],
    "infrastructure": ["hostel", "library", "lab", "workshop", "infrastructure",
                        "campus", "building", "facility"],
    "placement": ["placement", "package", "salary", "recruiter", "company",
                   "training", "internship", "t&p", "tcs", "wipro", "infosys"],
    "contact": ["contact", "phone", "email", "address", "office hours"],
    "anti_ragging": ["ragging", "anti-ragging", "helpline", "grievance"],
    "general": ["history", "vision", "mission", "about", "established",
                 "aitd", "aith", "ambedkar", "divyangjan"],
}


def _detect_topics(query: str) -> list[str]:
    """Detect which topic categories are relevant to the user's query."""
    query_lower = query.lower()
    matched_topics = []

    for topic, keywords in _TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                if topic not in matched_topics:
                    matched_topics.append(topic)
                break

    # Default to general + department if nothing matched
    if not matched_topics:
        matched_topics = ["general", "department"]

    return matched_topics


def _extract_text_from_html(html: str) -> str:
    """
    Extract readable text from HTML, removing scripts, styles, and tags.
    Simple regex-based extraction (no BeautifulSoup dependency required).
    """
    # Remove script and style blocks
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # Remove all hidden inputs (ASP.NET viewstate etc.)
    html = re.sub(r'<input[^>]*type="hidden"[^>]*/?\s*>', '', html, flags=re.IGNORECASE)

    # Replace common block elements with newlines
    html = re.sub(r'<(?:br|p|div|tr|li|h[1-6])[^>]*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</(?:p|div|tr|li|h[1-6]|td|th)>', '\n', html, flags=re.IGNORECASE)

    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)

    # Decode common HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")

    # Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = text.strip()

    # Remove lines that are just whitespace or single characters
    lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 2]
    return '\n'.join(lines)


async def search_website(query: str) -> list[dict]:
    """
    Scrape relevant pages from aitd.ac.in based on the query topic.

    Returns list of context chunks:
      [{"text": ..., "document_name": "aitd.ac.in/...", "page_number": 0,
        "source_type": "website", "relevance_score": 0.5}, ...]
    """
    topics = _detect_topics(query)
    urls_to_scrape = []
    for topic in topics:
        urls_to_scrape.extend(AITD_PAGES.get(topic, []))

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in urls_to_scrape:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    # Cap at 5 pages to avoid slow responses
    unique_urls = unique_urls[:5]

    if not unique_urls:
        logger.info("Web search: no relevant AITD pages found for query topics.")
        return []

    logger.info(f"Web search: scraping {len(unique_urls)} pages for topics {topics}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://aitd.ac.in/",
    }

    chunks = []
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
        for url in unique_urls:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.warning(f"Web search: {url} returned status {response.status_code}")
                    continue

                text = _extract_text_from_html(response.text)

                # Skip if extracted text is too short to be useful
                if len(text) < 50:
                    logger.warning(f"Web search: {url} extracted text too short ({len(text)} chars)")
                    continue

                # Trim to reasonable size (first 3000 chars of useful content)
                if len(text) > 3000:
                    text = text[:3000]

                page_name = url.split('/')[-1].replace('.aspx', '').replace('.html', '')
                chunks.append({
                    "text": text,
                    "document_name": f"aitd.ac.in/{page_name}",
                    "page_number": 0,
                    "source_type": "website",
                    "relevance_score": 0.5,
                })
                logger.info(f"Web search: scraped {url} -> {len(text)} chars")

            except httpx.TimeoutException:
                logger.warning(f"Web search: timeout scraping {url}")
            except Exception as e:
                logger.warning(f"Web search: error scraping {url}: {e}")

    logger.info(f"Web search: returned {len(chunks)} chunks from website")
    return chunks


async def search_and_ingest(query: str) -> list[dict]:
    """
    Search the website AND auto-ingest scraped content into ChromaDB
    for future queries. Returns the chunks for immediate LLM use.
    """
    chunks = await search_website(query)

    if not chunks:
        return []

    # Auto-ingest into ChromaDB in background (don't block the response)
    try:
        from services.rag_service import add_documents

        texts = [c["text"] for c in chunks]
        metadatas = [
            {"document_name": c["document_name"], "page_number": 0, "source_type": "website"}
            for c in chunks
        ]
        ids = [f"web_{c['document_name'].replace('/', '_')}_{i}" for i, c in enumerate(chunks)]

        added = await asyncio.to_thread(add_documents, texts, metadatas, ids)
        logger.info(f"Web search: auto-ingested {added} website chunks into ChromaDB")
    except Exception as e:
        logger.warning(f"Web search: failed to auto-ingest website content: {e}")

    return chunks
