"""
Embedder — thin wrapper (ChromaDB handles embedding internally).
This module exists for API compatibility; ChromaDB uses its default
sentence-transformers model (all-MiniLM-L6-v2) when no custom
embedding function is provided.
"""


def embed(texts: list[str]) -> list[str]:
    """
    Passthrough — ChromaDB generates embeddings automatically
    when documents are added via collection.add(documents=...).
    This function is kept for interface consistency.
    """
    return texts
