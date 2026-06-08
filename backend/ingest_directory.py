"""
Bulk Ingestion Script — Ingests all text documents from Ai_chatbot_data/
into ChromaDB and registers them in the PostgreSQL documents table.
"""
import os
import sys
import shutil
import asyncio

# psycopg requires SelectorEventLoop on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from database.db import _conninfo
from services.rag_service import add_documents
from utils.text_chunker import chunk_text
from utils.logger import logger
import psycopg

DATA_DIR = Path(__file__).resolve().parent.parent / "Ai_chatbot_data"
UPLOAD_DIR = Path(settings.UPLOAD_DIR)


async def ingest_file(filename: str, conn):
    file_path = DATA_DIR / filename
    if not file_path.exists():
        logger.error(f"File {filename} does not exist.")
        return

    # Read content
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text_content = f.read()

    # Destination in upload folder
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest_path = UPLOAD_DIR / filename
    shutil.copy2(file_path, dest_path)
    logger.info(f"Copied {filename} to {dest_path}")

    # Chunk text
    chunks = chunk_text(
        text=text_content,
        page_number=1,
        document_name=filename,
        source_type="document"
    )
    if not chunks:
        logger.warning(f"No chunks generated for {filename}")
        return

    texts = [c["text"] for c in chunks]
    metadatas = [
        {"document_name": c["document_name"], "page_number": c["page_number"], "source_type": c["source_type"]}
        for c in chunks
    ]
    ids = [f"{filename}_{i}" for i in range(len(chunks))]

    # Ingest into ChromaDB
    added = await asyncio.to_thread(add_documents, texts, metadatas, ids)
    logger.info(f"Ingested {added} chunks from {filename} into ChromaDB.")

    # Record in PostgreSQL (update if already exists to prevent duplicates)
    await conn.execute(
        """
        INSERT INTO documents (filename, source_type, chunk_count)
        VALUES (%s, 'document', %s)
        ON CONFLICT DO NOTHING
        """,
        (filename, added)
    )
    await conn.commit()
    logger.info(f"Registered {filename} in PostgreSQL documents registry.")


async def main():
    if not DATA_DIR.exists():
        print(f"Data directory {DATA_DIR} not found.")
        return

    conn = await psycopg.AsyncConnection.connect(_conninfo)
    try:
        files = [f for f in os.listdir(DATA_DIR) if f.endswith(".txt")]
        print(f"Found {len(files)} text files in {DATA_DIR}. Starting ingestion...")
        for filename in files:
            await ingest_file(filename, conn)
        print("Bulk ingestion completed successfully!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
