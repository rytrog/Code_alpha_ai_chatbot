# Architecture Scalability & Concurrency Report
**Project:** University AI Chatbot (FastAPI + psycopg3 + ChromaDB + Gemini 2.5 Flash)

---

## 1. Executive Summary
This report analyzes the concurrency limits, architectural bottlenecks, and scaling roadmap for the **University AI Chatbot**. 

The current design utilizes a **9-stage pipeline** designed to shield the application from calling the LLM (Large Language Model) on every interaction. While this hybrid pipeline significantly improves efficiency, the current backend implementation has structural bottlenecks—most notably, the absence of database connection pooling and local CPU-bound embedding generation—which limits the default deployment to a few concurrent users for full AI responses.

By implementing the production scaling recommendations detailed in this report, the architecture can scale to support **thousands of concurrent students** during peak hours (e.g., during admissions or exam results releases).

---

## 2. Request Processing & Concurrency Matrix
Because requests are processed sequentially through the 9-stage pipeline, the response time—and therefore the concurrent capacity—varies dramatically based on the *type* of question a student asks.

### Pipeline Stage Breakdown
```
[User Message] ──> (Stage 1: Greeting) ─────────────────────────> [Fast Reply (1ms)]
                    └──> (Stage 2 & 3: Normalization & FAQ) ────> [DB Read (15ms)]
                          └──> (Stage 4: Cache Lookup) ──────────> [DB Read (15ms)]
                                └──> (Stage 5: Scope Validation) ──> [Reject (2ms)]
                                      └──> (Stage 6, 7 & 8: ChromaDB + Gemini + Cache Write) ──> [AI Reply (1-3s)]
```

### Estimated Concurrency Performance (Single Instance, 2-4 Cores, CPU-only)

| Request Type | Active Stages | Average Response Time | Estimated Max Concurrency (Req/Sec) | Performance Bottleneck |
| :--- | :--- | :--- | :--- | :--- |
| **Greetings / Off-topic** | Stage 1, 5 | ~1 – 2 ms | **1,500+** | Python event loop overhead |
| **FAQ Hits** | Stage 2, 3 | ~10 – 30 ms | **50 – 150** | PostgreSQL connection handshake latency |
| **Cached Answers** | Stage 4 | ~10 – 30 ms | **50 – 150** | PostgreSQL connection handshake latency |
| **Full RAG / Gemini LLM** | Stage 6, 7, 8, 9 | ~1,000 – 3,000 ms | **5 – 15** | CPU-bound embedding generation & LLM network latency |

---

## 3. Structural Bottlenecks in the Current Codebase

### 🛑 1. Database Connection Overhead (Critical)
In `backend/database/db.py` (lines 78-85), the FastAPI connection dependency opens and closes a new PostgreSQL connection for **every single request**:
```python
async def get_conn():
    conn = await psycopg.AsyncConnection.connect(_conninfo)
    try:
        yield conn
    finally:
        await conn.close()
```
* **Impact:** For every request, the backend performs a full TCP/IP handshake and SSL negotiation, and PostgreSQL forks a new backend worker process. If 100 students click "Send" at the same time, the system will run out of database connections or experience severe latency.

### 🛑 2. CPU-Bound Local Embeddings (High Impact)
In `backend/services/rag_service.py`, ChromaDB is initialized locally:
```python
_chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
```
* **Impact:** Before looking up text in ChromaDB, the system must translate the student's question into a mathematical vector (embedding) using its default local Transformer model. Running this model on a standard server CPU blocks thread pools and spikes CPU utilization to 100% under modest loads.

### 🛑 3. Single-Worker ASGI Server
The backend is set up to run via Uvicorn with `workers=1` and `reload=False`.
* **Impact:** Even though FastAPI uses asynchronous I/O, Python executes in a single process. Any CPU-bound task (such as text normalizations, regex checks, and embedding calculation) blocks the entire event loop, causing other requests to wait.

### 🛑 4. External LLM Rate Limits
The Gemini 2.5 Flash model is called synchronously inside a thread pool (`asyncio.to_thread`) via the Google GenAI SDK.
* **Impact:** If many students generate RAG requests simultaneously, the system will hit the Gemini API rate limits (e.g., Free Tier is restricted to 15 RPM). Without a queue or retry mechanism, students will receive an generic fallback error message.

---

## 4. Roadmap to Production-Grade Scalability

To transition the University AI Chatbot from a development prototype to a production system supporting thousands of students, implement the following architectural upgrades:

### Phase 1: Quick Wins (Upgrading the Current Code)
1. **Enable Connection Pooling:**
   Modify `db.py` to use `psycopg_pool.AsyncConnectionPool` instead of direct connections. This maintains a persistent, reusable pool of database connections (e.g., 20 connections shared across the application).
2. **Increase Web Server Workers:**
   Deploy using Gunicorn as the process manager:
   ```bash
   gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```
   *(Formula for workers: `2 * Number of CPU Cores + 1`)*

### Phase 2: Cache & Embedding Scaling
3. **Introduce Redis for Cache and FAQs:**
   Move the FAQ lookup and Gemini Cache out of PostgreSQL and into **Redis**. Redis serves cache keys in under **1 millisecond** and can handle up to **100,000+ operations/sec**, shielding PostgreSQL from high read traffic.
4. **Offload Embedding Generation:**
   Instead of running the embedding model locally on the CPU, configure ChromaDB to use Google's `text-embedding-004` API endpoint, or migrate to a dedicated, GPU-accelerated embedding server.

### Phase 3: Infrastructure Scaling
5. **Decouple Vector Search:**
   Run ChromaDB as a separate containerized service (or migrate to PgVector inside PostgreSQL, or use Qdrant/Pinecone). This isolates heavy vector math calculations from the main API server.
6. **Horizontal Load Balancing:**
   Deploy multiple instances of the FastAPI container behind the existing **Nginx** reverse proxy. Nginx can distribute the incoming student traffic across these instances using a round-robin algorithm:
   ```nginx
   upstream fastapi_backend {
       server backend-node-1:8000;
       server backend-node-2:8000;
       server backend-node-3:8000;
       keepalive 32;
   }
   ```
7. **Gemini API Optimization:**
   * Upgrade your Google AI Studio API key to a **Pay-as-you-go** account to lift the 15 RPM restriction.
   * Implement **Exponential Backoff and Retries** in the Gemini service to handle rate limits gracefully when traffic spikes.
