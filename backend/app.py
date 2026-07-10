"""
AITD Kanpur AI Chatbot — FastAPI Main Application
Modular monolithic architecture with async PostgreSQL + ChromaDB.
"""
import os
import sys
import asyncio
import selectors
# Step 2: Rebuild the RAG search index
# After saving your changes, open a terminal in the backend/ directory and run the rebuild script:

# powershell
# python rebuild_index.py
# MUST be set before any async code runs — psycopg requires SelectorEventLoop on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database.db import init_db, get_conn, _conninfo, init_pool, close_pool
from utils.rate_limit import RateLimitMiddleware
from utils.logger import logger

from api.chat import router as chat_router
from api.upload import router as upload_router
from api.analytics import router as analytics_router
from api.health import router as health_router


async def _seed_faq():
    """Insert default FAQ rows if the table is empty."""
    import psycopg
    from services.normalize_service import normalize

    conn = await psycopg.AsyncConnection.connect(_conninfo)
    try:
        row = await conn.execute("SELECT COUNT(*) FROM faq")
        count = (await row.fetchone())[0]
        if count > 0:
            await conn.close()
            return

        faqs = [
            ("What are the admission dates?", "The application deadline for AITD Kanpur is 30th September every academic year. Apply online via www.aitd.ac.in/admissions. B.Tech admission is based on JEE (Main) and Diploma admission through state-level counselling for Divyang students.", "admission"),
            ("What is the hostel fee?", "The hostel fee at AITD Kanpur is approximately Rs. 20,000 to Rs. 25,000 per year. Separate hostels are available for boys and girls with barrier-free access.", "hostel"),
            ("What is the fee structure?", "B.Tech fee is approximately Rs. 65,000 to Rs. 76,000 per year. Diploma fee is Rs. 15,000 to Rs. 20,000 per year. Special concessions are available for Divyang students with reduced tuition of approximately Rs. 45,000.", "fees"),
            ("Who is the Director?", "The Director of AITD Kanpur is Dr. Rachna Asthana.", "administration"),
            ("What are the contact details?", "Phone: +91-0512-2583221. Email: info@aitd.ac.in or director@aitd.ac.in. Address: Awadhpuri, Opposite Rama Dental College, Kanpur - 208024, Uttar Pradesh. Office Hours: 9:00 AM to 5:00 PM, Monday to Friday.", "contact"),
            ("What courses are offered?", "AITD Kanpur offers B.Tech (4 years) in Computer Science & Engineering, Information Technology, Electronics Engineering, Biotechnology, and Chemical Engineering with ~300 total seats. Diploma (3 years) in CSE, Electronics, and Architecture Assistantship exclusively for Divyang students. M.Tech (2 years) in selected branches.", "course"),
            ("What are the placements like?", "AITD has a dedicated Training and Placement Department. Top recruiters include TCS, Wipro, Tech Mahindra, Infosys, and HCL. Average package is Rs. 3 to Rs. 5 LPA depending on branch and performance.", "placement"),
            ("Where is AITD located?", "AITD is located at Awadhpuri, Opposite Rama Dental College, Kanpur - 208024, Uttar Pradesh, India. The campus is spread over approximately 15 acres and is fully barrier-free and accessible for Divyang students.", "location"),
            ("What is AITD full form?", "AITD stands for Dr. Ambedkar Institute of Technology for Divyangjan. It was formerly known as AITH (Dr. Ambedkar Institute of Technology for Handicapped). Established in 1997 by the Government of Uttar Pradesh.", "general"),
            ("Who is the HOD of CSE?", "Prof. Shree Nath Dwivedi is the Head of Department (HOD) for both Computer Science & Engineering and Computer Science & Engineering (AI & ML) at AITD Kanpur. He is highly hardworking, a best faculty member, exceptionally supportive of students, and serves as the Project Head supervising innovative AI and computer science research at the institute.", "department"),
            ("Who is the HOD of IT?", "Dr. Abhishek Prabhakar is the Head of Department for Information Technology at AITD Kanpur.", "department"),
            ("Who is the HOD of Chemical Engineering?", "Dr. M. S. Tripathi is the Head of Department for Chemical Engineering at AITD Kanpur.", "department"),
            ("What are the library facilities?", "AITD library has over 17,800 books, 50+ journals, and a digital library with NPTEL access. The Computer Center has 200+ systems with 24x7 internet, LAN, and Wi-Fi connectivity.", "library"),
            ("What scholarships are available?", "AITD offers special concessions for Divyang students with reduced tuition. 60% seats are reserved for differently-abled candidates. Students may also avail government scholarships for SC/ST/OBC/Minority categories.", "scholarship"),
            ("What events are held at AITD?", "Major fests at AITD include Shankhnaad, Technozion, Freshers Party, Cultural Week, and Sports Fest. Student clubs include Cultural Cell, Literary Cell, Technical Society, NSS Unit, and Sports & Fitness Club.", "events"),
        ]

        for q, a, cat in faqs:
            await conn.execute(
                "INSERT INTO faq (question, normalized_key, answer, category, source) VALUES (%s, %s, %s, %s, 'seed') ON CONFLICT (normalized_key) DO NOTHING",
                (q, normalize(q), a, cat),
            )

        await conn.commit()
        logger.info(f"Seeded {len(faqs)} AITD FAQ entries.")
    finally:
        await conn.close()


async def _auto_ingest_data():
    """Auto-ingest the AITD data file into ChromaDB if collection is empty."""
    from services.rag_service import collection_count, add_documents
    from utils.text_chunker import chunk_text

    count = await asyncio.to_thread(collection_count)
    if count > 0:
        return

    data_file = os.path.join(os.path.dirname(__file__), "data", "aitd_kanpur_data.txt")
    if not os.path.exists(data_file):
        logger.warning("AITD data file not found, skipping auto-ingest.")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text, page_number=1, document_name="aitd_kanpur_data.txt", source_type="knowledge_base")
    if not chunks:
        return

    texts = [c["text"] for c in chunks]
    metadatas = [
        {"document_name": c["document_name"], "page_number": c["page_number"], "source_type": c["source_type"]}
        for c in chunks
    ]
    ids = [f"aitd_data_{i}" for i in range(len(chunks))]

    added = await asyncio.to_thread(add_documents, texts, metadatas, ids)
    logger.info(f"Auto-ingested AITD data: {added} chunks into ChromaDB.")


async def _background_ingest():
    """Wrapper to run auto-ingest in background without blocking startup."""
    try:
        await _auto_ingest_data()
    except Exception as e:
        logger.error(f"Background auto-ingest error: {e}")


async def _purge_negative_cache():
    """Purge all stale negative/failure answers from the answer_cache on startup."""
    import psycopg
    from psycopg.rows import dict_row
    from services.cache_service import purge_negative_cache

    conn = await psycopg.AsyncConnection.connect(_conninfo)
    conn.row_factory = dict_row
    try:
        purged = await purge_negative_cache(conn)
        if purged > 0:
            logger.info(f"Startup: purged {purged} stale negative cache entries.")
    except Exception as e:
        logger.warning(f"Startup: failed to purge negative cache: {e}")
    finally:
        await conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info(f"Starting {settings.APP_NAME}...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    try:
        await init_pool()
        await init_db()
        await _seed_faq()
        # Purge any stale negative answers from previous runs
        await _purge_negative_cache()
        logger.info("Database initialised. FAQ seeded. Negative cache purged.")
        
        # Pre-initialize ChromaDB client and collection to avoid multithreading race conditions
        from services.rag_service import init_chroma
        await asyncio.to_thread(init_chroma)
        logger.info("ChromaDB initialized thread-safely.")

        # Start the background ingestion worker
        from services.ingestion_worker import start_ingestion_worker
        await start_ingestion_worker()
    except Exception as e:
        logger.error(f"Database/ChromaDB startup error: {e}")
        logger.warning("App running with degraded services. Chat/RAG may fail.")

    # Auto-ingest AITD knowledge base in background
    ingest_task = asyncio.create_task(_background_ingest())

    yield

    if not ingest_task.done():
        ingest_task.cancel()
    
    # Stop the background ingestion worker
    try:
        from services.ingestion_worker import stop_ingestion_worker
        await stop_ingestion_worker()
    except Exception as e:
        logger.error(f"Error stopping background ingestion worker: {e}")

    await close_pool()
    logger.info("Shutting down.")


# ── FastAPI app ──
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

# ── API routes ──
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
app.include_router(health_router, prefix="/api", tags=["Health"])

# ── Static files (widget + admin panel) ──
_backend_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_backend_dir)

widget_dir = os.path.join(_project_root, "widget")
admin_dir = os.path.join(_project_root, "admin-panel")

if os.path.isdir(widget_dir):
    app.mount("/widget", StaticFiles(directory=widget_dir), name="widget")
if os.path.isdir(admin_dir):
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


def _is_windows():
    return sys.platform == "win32"


if __name__ == "__main__":
    import uvicorn

    try:
        if _is_windows():
            # Force SelectorEventLoop to avoid psycopg3 'ProactorEventLoop' compatibility issues
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            config = uvicorn.Config(
                app="app:app",
                host=settings.HOST,
                port=settings.PORT,
                reload=False,
                workers=2,
                loop="asyncio",
            )
            server = uvicorn.Server(config)
            loop.run_until_complete(server.serve())
        else:
            uvicorn.run(
                "app:app",
                host=settings.HOST,
                port=settings.PORT,
                reload=False,
                workers=2,
            )
    except KeyboardInterrupt:
        logger.info("Server stopped manually via KeyboardInterrupt.")


