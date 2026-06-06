"""
RAG Service — retrieves relevant document chunks from ChromaDB.
Returns top-K chunks with source metadata.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
from utils.logger import logger

# ── Lazy ChromaDB client (initialised on first access) ──
_chroma_client = None

COLLECTION_NAME = "university_docs"
RELEVANCE_THRESHOLD = 0.35


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
    Search ChromaDB for the most relevant chunks.

    Returns list of dicts:
      [{"text": ..., "document_name": ..., "page_number": ..., "source_type": ...}, ...]
    """
    top_k = n_results or settings.RAG_TOP_K
    collection = _get_collection()

    if collection.count() == 0:
        logger.warning("ChromaDB collection is empty — no documents ingested yet.")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = round(1 - dist, 4)
            if score >= RELEVANCE_THRESHOLD:
                chunks.append({
                    "text": doc,
                    "document_name": meta.get("document_name", "Unknown"),
                    "page_number": meta.get("page_number", 0),
                    "source_type": meta.get("source_type", "document"),
                    "relevance_score": score,
                })

    return chunks


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
