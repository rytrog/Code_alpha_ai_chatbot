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

import threading
from chromadb import EmbeddingFunction, Documents, Embeddings

# ── Lazy ChromaDB client & collection (initialised on first access) ──
_chroma_client = None
_collection = None
_chroma_lock = threading.RLock()

COLLECTION_NAME = "university_docs"


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom embedding function using Google Gemini API to save container RAM."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        from google import genai
        self.client = genai.Client(api_key=api_key)

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []
        try:
            response = self.client.models.embed_content(
                model="text-embedding-004",
                contents=input,
            )
            if hasattr(response, "embeddings"):
                return [e.values for e in response.embeddings]
            elif hasattr(response, "embedding"):
                return [response.embedding.values]
            else:
                return []
        except Exception as e:
            logger.error(f"Gemini remote embedding API call failed: {e}")
            raise e


def _get_embedding_function():
    """Determine the embedding function based on Gemini API key availability to minimize RAM usage."""
    # Temporarily disabled remote API check to use local embedding function (saves startup time)
    return None

    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "SET_YOUR_GEMINI_API_KEY_HERE":
        if settings.LLM_PROVIDER.lower().strip() == "gemini":
            api_key = settings.LLM_API_KEY
            
    if api_key and api_key != "SET_YOUR_GEMINI_API_KEY_HERE":
        try:
            logger.info("Testing remote Gemini API for ChromaDB embeddings (text-embedding-004)...")
            from google import genai
            client = genai.Client(api_key=api_key)
            client.models.embed_content(
                model="text-embedding-004",
                contents="healthcheck",
            )
            logger.info("Using remote Gemini API for ChromaDB embeddings (low memory mode).")
            return GeminiEmbeddingFunction(api_key=api_key)
        except Exception as e:
            logger.warning(
                f"Failed to verify Gemini API key for embeddings: {e}. "
                "Falling back to local in-process embeddings (high memory usage!)."
            )
            
    return None



def _get_client():
    """Get or create the ChromaDB client (lazy singleton)."""
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                logger.info("Initializing ChromaDB client (first access)...")
                _chroma_client = chromadb.PersistentClient(
                    path=settings.CHROMA_PATH,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                logger.info("ChromaDB client initialized.")
    return _chroma_client


def _get_collection():
    """Get or create the university docs collection."""
    global _collection
    if _collection is None:
        with _chroma_lock:
            if _collection is None:
                ef = _get_embedding_function()
                if ef is None:
                    from chromadb.utils import embedding_functions
                    ef = embedding_functions.DefaultEmbeddingFunction()
                    
                client = _get_client()
                try:
                    _collection = client.get_or_create_collection(
                        name=COLLECTION_NAME,
                        embedding_function=ef,
                        metadata={"hnsw:space": "cosine"},
                    )
                except Exception as e:
                    logger.warning(f"Error loading ChromaDB collection, recreating due to model change/dimension mismatch: {e}")
                    try:
                        client.delete_collection(name=COLLECTION_NAME)
                    except Exception as de:
                        logger.error(f"Could not delete collection: {de}")
                    _collection = client.get_or_create_collection(
                        name=COLLECTION_NAME,
                        embedding_function=ef,
                        metadata={"hnsw:space": "cosine"},
                    )
    return _collection


def init_chroma() -> None:
    """Pre-initialize ChromaDB client and collection to avoid multithreaded race conditions."""
    _get_collection()





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
    global _collection
    with _chroma_lock:
        try:
            _get_client().delete_collection(name=COLLECTION_NAME)
            logger.info("ChromaDB collection deleted for rebuild.")
        except Exception as e:
            logger.warning(f"Could not delete collection: {e}")
        finally:
            _collection = None


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
