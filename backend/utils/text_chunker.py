"""
TextChunker — splits extracted text into overlapping chunks
for ChromaDB storage.  Sentence-aware to avoid mid-word splits.
"""
from config import settings




def chunk_text(
    text: str,
    page_number: int = 1,
    document_name: str = "Unknown",
    source_type: str = "document",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """
    Split *text* into overlapping chunks.

    Returns list of dicts:
      [{"text": "...", "page_number": 1, "document_name": "...",
        "source_type": "...", "chunk_index": 0}, ...]
    """
    size = chunk_size or settings.CHUNK_SIZE
    overlap = chunk_overlap or settings.CHUNK_OVERLAP

    if not text or not text.strip():
        return []

    text = text.strip()

    # If text fits in one chunk, return it directly
    if len(text) <= size:
        return [{
            "text": text,
            "page_number": page_number,
            "document_name": document_name,
            "source_type": source_type,
            "chunk_index": 0,
        }]

    chunks: list[dict] = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + size

        # Try to break at a sentence boundary
        if end < len(text):
            # Look for last period, question mark, or newline within the window
            for sep in [". ", "? ", "! ", "\n"]:
                last_sep = text.rfind(sep, start, end)
                if last_sep > start:
                    end = last_sep + 1
                    break

        chunk_text_str = text[start:end].strip()
        if chunk_text_str:
            chunks.append({
                "text": chunk_text_str,
                "page_number": page_number,
                "document_name": document_name,
                "source_type": source_type,
                "chunk_index": idx,
            })
            idx += 1

        # Ensure we always make forward progress to avoid infinite loops
        next_start = end - overlap
        if next_start <= start:
            start = end
        else:
            start = next_start

        if start >= len(text):
            break

    return chunks


def chunk_pages(
    pages: list[dict],
    document_name: str = "Unknown",
    source_type: str = "document",
) -> list[dict]:
    """
    Chunk all pages from a document.
    *pages* is the output from pdf_loader.extract_pdf().
    """
    all_chunks: list[dict] = []
    for page in pages:
        page_chunks = chunk_text(
            text=page["text"],
            page_number=page["page_number"],
            document_name=document_name,
            source_type=source_type,
        )
        all_chunks.extend(page_chunks)
    return all_chunks
