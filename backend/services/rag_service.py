"""
RAG Service — retrieves relevant document chunks from ChromaDB.
Returns top-K chunks with source metadata.

GENERALIZED SEARCH: retrieves a large pool of candidates from ALL files
in the database, then re-ranks by relevance score to give the best context.

All tuning parameters are read from config.py (configurable via .env):
  - RAG_CANDIDATE_POOL  → how many candidates to fetch from ChromaDB
  - RAG_TOP_K           → how many to pass to the LLM after re-ranking
  - RAG_RELEVANCE_THRESHOLD → minimum cosine similarity to keep a chunk
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
from utils.logger import logger

# ── Lazy ChromaDB client (initialised on first access) ──
_chroma_client = None

COLLECTION_NAME = "university_docs"


def _get_client():
    """Get or create the ChromaDB client (lazy singleton)."""
    global _chroma_client
    if _chroma_client is None:
        logger.info("Initializing ChromaDB client (first access, may download embedding model)...")
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("ChromaDB client initialized.")
    return _chroma_client


def _get_collection():
    """Get or create the university docs collection."""
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve(query: str, n_results: int | None = None) -> list[dict]:
    """
    GENERALIZED SEARCH across ALL documents in ChromaDB.

    Strategy:
      1. Fetch a LARGE pool of candidates (RAG_CANDIDATE_POOL from config)
         from the entire database — this ensures chunks from every uploaded
         file are considered.
      2. Filter by RAG_RELEVANCE_THRESHOLD (permissive, from config).
      3. Sort by relevance and return top RAG_TOP_K chunks (from config).

    Returns list of dicts:
      [{"text": ..., "document_name": ..., "page_number": ...,
        "source_type": ..., "relevance_score": ...}, ...]
    """
    pool_size = settings.RAG_CANDIDATE_POOL
    final_size = n_results or settings.RAG_TOP_K
    threshold = settings.RAG_RELEVANCE_THRESHOLD

    collection = _get_collection()

    total_docs = collection.count()
    if total_docs == 0:
        logger.warning("ChromaDB collection is empty — no documents ingested yet.")
        return []

    # Fetch a large candidate pool (capped at total doc count)
    fetch_count = min(pool_size, total_docs)

    logger.info(
        f"RAG search: query='{query[:100]}' | pool={fetch_count}/{total_docs} "
        f"| threshold={threshold} | final_size={final_size}"
    )

    try:
        results = collection.query(
            query_texts=[query],
            n_results=fetch_count,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        return []

    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score: 1 - distance
            score = round(1 - dist, 4)

            doc_name = meta.get("document_name", "Unknown")
            logger.debug(
                f"  Chunk from '{doc_name}' | score={score:.4f} | "
                f"text='{doc[:60]}...'"
            )

            if score >= threshold:
                chunks.append({
                    "text": doc,
                    "document_name": doc_name,
                    "page_number": meta.get("page_number", 0),
                    "source_type": meta.get("source_type", "document"),
                    "relevance_score": score,
                })

    # Sort by relevance (highest first) and take top N
    chunks.sort(key=lambda c: c["relevance_score"], reverse=True)
    top_chunks = chunks[:final_size]

    # Log what files were found for debugging
    if top_chunks:
        files_found = set(c["document_name"] for c in top_chunks)
        scores = [c["relevance_score"] for c in top_chunks]
        logger.info(
            f"RAG returned {len(top_chunks)} chunks from files: {files_found} "
            f"| score range: {min(scores):.4f} – {max(scores):.4f}"
        )
    else:
        logger.warning(
            f"RAG found 0 relevant chunks (above threshold {threshold}) "
            f"for query: '{query[:100]}'"
        )

    return top_chunks


def add_documents(
    texts: list[str],
    metadatas: list[dict],
    ids: list[str],
) -> int:
    """
    Add document chunks to ChromaDB.
    ChromaDB generates embeddings internally using its default model.
    Returns number of chunks added.
    """
    collection = _get_collection()
    collection.add(
        documents=texts,
        metadatas=metadatas,
        ids=ids,
    )
    logger.info(f"Added {len(texts)} chunks to ChromaDB.")
    return len(texts)


def delete_collection() -> None:
    """Delete the entire collection (for rebuild)."""
    try:
        _get_client().delete_collection(name=COLLECTION_NAME)
        logger.info("ChromaDB collection deleted for rebuild.")
    except Exception as e:
        logger.warning(f"Could not delete collection: {e}")


def delete_document_chunks(document_name: str) -> None:
    """Delete all chunks belonging to a document from ChromaDB."""
    try:
        collection = _get_collection()
        collection.delete(where={"document_name": document_name})
        logger.info(f"Deleted chunks for document '{document_name}' from ChromaDB.")
    except Exception as e:
        logger.error(f"Error deleting chunks for '{document_name}' from ChromaDB: {e}")


def collection_count() -> int:
    """Return number of chunks in the collection."""
    try:
        return _get_collection().count()
    except Exception:
        return 0
