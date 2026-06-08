"""
Rebuild ChromaDB Index — Re-ingests ALL data files with new chunk settings.
Run this ONCE after changing CHUNK_SIZE / CHUNK_OVERLAP in config.py.
"""
import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from services.rag_service import add_documents, delete_collection, collection_count
from utils.text_chunker import chunk_text, chunk_pages
from utils.pdf_loader import extract_pdf


def rebuild():
    """Delete old collection and re-ingest all files."""
    # Step 1: Delete old collection
    print("Step 1: Deleting old ChromaDB collection...")
    delete_collection()

    total_chunks = 0

    # Step 2: Ingest base knowledge file
    data_file = os.path.join(os.path.dirname(__file__), "data", "aitd_kanpur_data.txt")
    if os.path.exists(data_file):
        print(f"Step 2: Ingesting base knowledge file: {data_file}")
        with open(data_file, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text, page_number=1, document_name="aitd_kanpur_data.txt",
                            source_type="knowledge_base")
        if chunks:
            texts = [c["text"] for c in chunks]
            metadatas = [{"document_name": c["document_name"],
                          "page_number": c["page_number"],
                          "source_type": c["source_type"]} for c in chunks]
            ids = [f"aitd_data_{i}" for i in range(len(chunks))]
            added = add_documents(texts, metadatas, ids)
            total_chunks += added
            print(f"  -> {added} chunks from aitd_kanpur_data.txt")
    else:
        print("Step 2: Base knowledge file not found, skipping.")

    # Step 3: Ingest all files from uploads/
    upload_dir = settings.UPLOAD_DIR
    print(f"Step 3: Ingesting files from {upload_dir}...")

    if os.path.isdir(upload_dir):
        for filename in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, filename)

            # Skip directories and non-text files
            if os.path.isdir(filepath):
                continue

            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in ("txt", "csv", "pdf"):
                continue

            print(f"  Processing: {filename} ({os.path.getsize(filepath)} bytes)")

            try:
                if ext == "pdf":
                    pages = extract_pdf(filepath)
                    chunks = chunk_pages(pages, document_name=filename, source_type="document")
                else:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    chunks = chunk_text(text, page_number=1, document_name=filename,
                                        source_type="document")

                if chunks:
                    texts = [c["text"] for c in chunks]
                    metadatas = [{"document_name": c["document_name"],
                                  "page_number": c["page_number"],
                                  "source_type": c["source_type"]} for c in chunks]
                    ids = [f"{filename}_{i}" for i in range(len(chunks))]
                    added = add_documents(texts, metadatas, ids)
                    total_chunks += added
                    print(f"  -> {added} chunks from {filename}")
                else:
                    print(f"  -> 0 chunks (empty or too short)")
            except Exception as e:
                print(f"  -> ERROR: {e}")

    # Step 4: Report
    final_count = collection_count()
    print(f"\nDONE! Total chunks in ChromaDB: {final_count}")
    print(f"Chunk settings: CHUNK_SIZE={settings.CHUNK_SIZE}, CHUNK_OVERLAP={settings.CHUNK_OVERLAP}")


if __name__ == "__main__":
    rebuild()
