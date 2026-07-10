"""
Ingestion Background Worker — Processes pending document ingestion tasks.
Utilizes PostgreSQL row locking (FOR UPDATE SKIP LOCKED) to run safely
across multiple concurrent Uvicorn worker processes.
"""
import os
import sys
import asyncio
import traceback
import psycopg
from psycopg.rows import dict_row

from config import settings
from database.db import db_pool, _conninfo
from utils.logger import logger
from services.rag_service import add_documents
from utils.pdf_loader import extract_pdf
from utils.text_chunker import chunk_pages

_worker_task = None
_should_run = False

async def ingestion_worker_loop():
    """Continuously poll the database for pending ingestion jobs."""
    global _should_run
    logger.info("Ingestion background worker loop started.")
    
    while _should_run:
        try:
            job = None
            
            # Acquire connection from the connection pool if available, else fallback
            if db_pool is not None:
                async with db_pool.connection() as conn:
                    conn.row_factory = dict_row
                    async with conn.transaction():
                        cur = await conn.execute(
                            """
                            SELECT id, filename, source_type 
                            FROM documents 
                            WHERE status = 'pending' 
                            ORDER BY id ASC 
                            LIMIT 1 
                            FOR UPDATE SKIP LOCKED
                            """
                        )
                        job = await cur.fetchone()
                        if job:
                            await conn.execute(
                                "UPDATE documents SET status = 'processing' WHERE id = %s",
                                (job["id"],)
                            )
            else:
                async with await psycopg.AsyncConnection.connect(_conninfo) as conn:
                    conn.row_factory = dict_row
                    async with conn.transaction():
                        cur = await conn.execute(
                            """
                            SELECT id, filename, source_type 
                            FROM documents 
                            WHERE status = 'pending' 
                            ORDER BY id ASC 
                            LIMIT 1 
                            FOR UPDATE SKIP LOCKED
                            """
                        )
                        job = await cur.fetchone()
                        if job:
                            await conn.execute(
                                "UPDATE documents SET status = 'processing' WHERE id = %s",
                                (job["id"],)
                            )

            if not job:
                # No jobs found, sleep briefly before checking again
                await asyncio.sleep(3)
                continue

            # Process the job
            doc_id = job["id"]
            filename = job["filename"]
            source_type = job["source_type"]
            logger.info(f"Background worker processing document: {filename} (ID: {doc_id})")

            try:
                file_path = os.path.join(settings.UPLOAD_DIR, filename)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Uploaded file not found on disk: {file_path}")

                ext = filename.rsplit(".", 1)[-1].lower()

                # Perform text extraction in a thread pool to avoid blocking the event loop
                if ext == "pdf":
                    pages = await asyncio.to_thread(extract_pdf, file_path)
                elif ext in ("txt", "csv"):
                    # Use utf-8 with fallback decoding
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text_content = f.read()
                    pages = [{"text": text_content, "page_number": 1}]
                else:
                    raise ValueError(f"Unsupported file extension: .{ext}")

                if not pages:
                    raise ValueError("No text content could be extracted from the file.")

                # Chunk the pages (CPU-bound, run in thread pool)
                chunks = await asyncio.to_thread(
                    chunk_pages, pages, filename, source_type
                )
                if not chunks:
                    raise ValueError("No chunks generated from the document.")

                texts = [c["text"] for c in chunks]
                metadatas = [
                    {
                        "document_name": c["document_name"],
                        "page_number": c["page_number"],
                        "source_type": c["source_type"]
                    }
                    for c in chunks
                ]
                ids = [f"{filename}_{i}" for i in range(len(chunks))]

                # Ingest into ChromaDB (CPU-bound embedding computation, run in thread pool)
                added = await asyncio.to_thread(add_documents, texts, metadatas, ids)

                # Complete: Update database and clean cache
                if db_pool is not None:
                    async with db_pool.connection() as conn:
                        async with conn.transaction():
                            await conn.execute(
                                """
                                UPDATE documents 
                                SET status = 'completed', chunk_count = %s, error_message = NULL 
                                WHERE id = %s
                                """,
                                (added, doc_id)
                            )
                            await conn.execute("DELETE FROM answer_cache")
                else:
                    async with await psycopg.AsyncConnection.connect(_conninfo) as conn:
                        async with conn.transaction():
                            await conn.execute(
                                """
                                UPDATE documents 
                                SET status = 'completed', chunk_count = %s, error_message = NULL 
                                WHERE id = %s
                                """,
                                (added, doc_id)
                            )
                            await conn.execute("DELETE FROM answer_cache")

                logger.info(f"Successfully finished background ingestion for {filename} (Added {added} chunks).")

            except Exception as doc_err:
                logger.error(f"Failed background ingestion for {filename}: {doc_err}")
                tb_msg = traceback.format_exc()
                
                # Mark job as failed in the database
                if db_pool is not None:
                    async with db_pool.connection() as conn:
                        async with conn.transaction():
                            await conn.execute(
                                """
                                UPDATE documents 
                                SET status = 'failed', error_message = %s 
                                WHERE id = %s
                                """,
                                (str(doc_err), doc_id)
                            )
                else:
                    async with await psycopg.AsyncConnection.connect(_conninfo) as conn:
                        async with conn.transaction():
                            await conn.execute(
                                """
                                UPDATE documents 
                                SET status = 'failed', error_message = %s 
                                WHERE id = %s
                                """,
                                (str(doc_err), doc_id)
                            )

        except Exception as loop_err:
            logger.error(f"Error in background ingestion loop: {loop_err}")
            await asyncio.sleep(5)


async def start_ingestion_worker():
    """Start the background ingestion loop task."""
    global _worker_task, _should_run
    if _worker_task is not None:
        return
    _should_run = True
    _worker_task = asyncio.create_task(ingestion_worker_loop())
    logger.info("Ingestion worker task successfully spawned.")


async def stop_ingestion_worker():
    """Gracefully cancel and stop the background ingestion task."""
    global _worker_task, _should_run
    if _worker_task is None:
        return
    _should_run = False
    logger.info("Stopping background ingestion worker...")
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    _worker_task = None
    logger.info("Background ingestion worker stopped.")
