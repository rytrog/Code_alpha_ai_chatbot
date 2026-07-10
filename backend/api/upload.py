"""
Upload API — POST /api/upload
"""
import os
import uuid
import asyncio
import csv
import io
from fastapi import APIRouter, UploadFile, File, Form, Depends

from config import settings
from database.db import get_conn
from services.rag_service import add_documents, delete_collection, collection_count, delete_document_chunks
from services.normalize_service import normalize
from utils.pdf_loader import extract_pdf
from utils.text_chunker import chunk_pages
from utils.validator import validate_file
from utils.logger import logger

router = APIRouter()


def parse_faq_csv(file_content: str) -> list[dict]:
    """Parse a CSV file containing Q&A pairs.
    Handles both header-based (matching 'question' and 'answer' or similar)
    and index-based (first column question, second column answer) schemas.
    """
    f = io.StringIO(file_content.strip())
    reader = csv.reader(f)
    try:
        rows = list(reader)
    except Exception as e:
        logger.error(f"Failed to parse CSV lines: {e}")
        return []

    if not rows:
        return []

    cleaned_rows = []
    for r in rows:
        if r:
            cleaned_rows.append([col.strip() for col in r])

    if not cleaned_rows:
        return []

    first_row = cleaned_rows[0]
    first_row_lower = [col.lower() for col in first_row]

    q_idx, a_idx = -1, -1
    for idx, col in enumerate(first_row_lower):
        if "question" in col or col == "q":
            q_idx = idx
        elif "answer" in col or col == "a":
            a_idx = idx

    has_headers = False
    if q_idx != -1 and a_idx != -1 and q_idx != a_idx:
        has_headers = True
    else:
        q_idx = 0
        a_idx = 1
        if len(first_row_lower) > 0 and (first_row_lower[0] in ("question", "q", "queries", "query", "questions")):
            has_headers = True
        elif len(first_row_lower) > 1 and (first_row_lower[1] in ("answer", "a", "response", "reply", "answers")):
            has_headers = True

    data_rows = cleaned_rows[1:] if has_headers else cleaned_rows

    faqs = []
    for r in data_rows:
        if not r or len(r) <= max(q_idx, a_idx):
            continue
        question = r[q_idx]
        answer = r[a_idx]
        if question and answer:
            faqs.append({"question": question, "answer": answer})
    return faqs


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    source_type: str = Form(default="document"),
    conn=Depends(get_conn),
):
    """Upload and ingest a document into the knowledge base."""
    file_bytes = await file.read()
    is_valid, err = validate_file(file.filename or "", len(file_bytes))
    if not is_valid:
        return {"error": err}

    filename = file.filename or "unnamed"
    ext = filename.rsplit(".", 1)[-1].lower()

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(settings.UPLOAD_DIR, filename)

    saved_filename = filename
    if os.path.exists(save_path):
        name, extension = os.path.splitext(filename)
        saved_filename = f"{name}_{uuid.uuid4().hex[:8]}{extension}"
        save_path = os.path.join(settings.UPLOAD_DIR, saved_filename)

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    logger.info(f"File saved: {save_path} ({len(file_bytes)} bytes)")

    if source_type == "faq":
        if ext != "csv":
            return {"error": "FAQ / Q&A Dataset must be a CSV file (.csv)"}
        
        text_content = file_bytes.decode("utf-8", errors="ignore")
        faq_list = parse_faq_csv(text_content)
        if not faq_list:
            return {"error": "No valid Q&A pairs found in CSV."}

        inserted_count = 0
        for pair in faq_list:
            q = pair["question"]
            a = pair["answer"]
            norm_key = normalize(q)
            await conn.execute(
                """
                INSERT INTO faq (question, normalized_key, answer, source)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (normalized_key)
                DO UPDATE SET answer = EXCLUDED.answer, source = EXCLUDED.source
                """,
                (q, norm_key, a, saved_filename),
            )
            inserted_count += 1

        # Record in PostgreSQL
        await conn.execute(
            "INSERT INTO documents (filename, source_type, chunk_count) VALUES (%s, %s, %s)",
            (saved_filename, source_type, inserted_count),
        )
        await conn.commit()

        logger.info(f"FAQ dataset ingested: {saved_filename} -> {inserted_count} QA pairs")

        return {
            "message": "FAQ document uploaded and ingested successfully.",
            "filename": saved_filename,
            "chunks": inserted_count,
            "source_type": source_type,
        }

    # Normal RAG flow
    if ext not in ("pdf", "txt", "csv"):
        return {"error": f"Unsupported file type: .{ext}"}

    try:
        # Perform text extraction
        if ext == "pdf":
            pages = await asyncio.to_thread(extract_pdf, save_path)
        else:
            text_content = file_bytes.decode("utf-8", errors="ignore")
            pages = [{"text": text_content, "page_number": 1}]

        # Chunk the pages (CPU-bound, run in thread pool)
        chunks = await asyncio.to_thread(chunk_pages, pages, saved_filename, source_type)
        total_chunks = 0
        if chunks:
            texts = [c["text"] for c in chunks]
            metadatas = [
                {
                    "document_name": c["document_name"],
                    "page_number": c["page_number"],
                    "source_type": c["source_type"]
                }
                for c in chunks
            ]
            ids = [f"{saved_filename}_{i}" for i in range(len(chunks))]

            # Ingest into ChromaDB (CPU-bound embedding computation, run in thread pool)
            added = await asyncio.to_thread(add_documents, texts, metadatas, ids)
            total_chunks = added

        # Record in PostgreSQL
        await conn.execute(
            "INSERT INTO documents (filename, source_type, chunk_count, status) VALUES (%s, %s, %s, %s)",
            (saved_filename, source_type, total_chunks, "completed"),
        )
        await conn.execute("DELETE FROM answer_cache")
        await conn.commit()

        logger.info(f"Document uploaded and ingested successfully: {saved_filename} -> {total_chunks} chunks")

        return {
            "message": "Document uploaded and ingested successfully.",
            "filename": saved_filename,
            "chunks": total_chunks,
            "source_type": source_type,
            "status": "completed",
        }
    except Exception as e:
        logger.error(f"Failed synchronous ingestion for {saved_filename}: {e}")
        # Insert as failed
        await conn.execute(
            "INSERT INTO documents (filename, source_type, chunk_count, status, error_message) VALUES (%s, %s, %s, %s, %s)",
            (saved_filename, source_type, 0, "failed", str(e)),
        )
        await conn.commit()
        return {"error": f"Ingestion failed: {str(e)}"}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, conn=Depends(get_conn)):
    """Delete a document record."""
    r = await conn.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
    doc = await r.fetchone()

    if not doc:
        return {"error": "Document not found."}

    file_path = os.path.join(settings.UPLOAD_DIR, doc["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"Deleted file: {file_path}")

    if doc["source_type"] == "faq":
        await conn.execute(
            "DELETE FROM faq WHERE source = %s", (doc["filename"],)
        )
    else:
        # Delete from ChromaDB
        await asyncio.to_thread(delete_document_chunks, doc["filename"])

        # Delete dependent cache entries from PostgreSQL
        await conn.execute(
            "DELETE FROM answer_cache WHERE source ILIKE %s",
            (f"%{doc['filename']}%",),
        )

    await conn.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
    await conn.commit()

    return {"message": f"Document '{doc['filename']}' deleted."}


@router.post("/rebuild-index")
async def rebuild_index(conn=Depends(get_conn)):
    """Rebuild the entire ChromaDB index from all documents in uploads/."""
    await asyncio.to_thread(delete_collection)

    r = await conn.execute("SELECT * FROM documents")
    documents = await r.fetchall()

    total_chunks = 0
    for doc in documents:
        if doc["source_type"] == "faq":
            continue
        file_path = os.path.join(settings.UPLOAD_DIR, doc["filename"])
        if not os.path.exists(file_path):
            continue

        ext = doc["filename"].rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            pages = extract_pdf(file_path)
        elif ext in ("txt", "csv"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                pages = [{"text": f.read(), "page_number": 1}]
        else:
            continue

        chunks = chunk_pages(pages, document_name=doc["filename"], source_type=doc["source_type"] or "document")
        if chunks:
            texts = [c["text"] for c in chunks]
            metadatas = [
                {"document_name": c["document_name"], "page_number": c["page_number"], "source_type": c["source_type"]}
                for c in chunks
            ]
            ids = [f"{doc['filename']}_{i}" for i in range(len(chunks))]
            added = await asyncio.to_thread(add_documents, texts, metadatas, ids)
            total_chunks += added
            await conn.execute(
                "UPDATE documents SET chunk_count = %s, status = 'completed', error_message = NULL WHERE id = %s",
                (added, doc["id"]),
            )
            await conn.commit()

    logger.info(f"Index rebuilt: {total_chunks} total chunks from {len(documents)} documents")
    return {
        "message": "Index rebuilt successfully.",
        "total_chunks": total_chunks,
        "documents_processed": len(documents),
    }
