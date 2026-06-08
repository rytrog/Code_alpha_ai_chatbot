"""
TextChunker — splits extracted text into overlapping chunks
for ChromaDB storage.

SMART SPLITTING:
  - Detects "Question:" / "Answer:" blocks and keeps them together.
  - Breaks at section headers (emoji lines, "##" lines) to keep sections intact.
  - Falls back to sentence-boundary splitting for plain prose.
"""
import re
from config import settings


def _split_into_sections(text: str) -> list[str]:
    """
    Split text into logical sections using common delimiters found in AITD data files.

    Priority of split points (in order):
      1. "Question:" headers (keeps Q&A pairs together)
      2. Double newlines followed by emoji/header lines
      3. Double newlines
    """
    # Pattern: split BEFORE lines that start with "Question:" (case-insensitive)
    # This keeps each Q&A pair as one section
    qa_pattern = re.compile(r'\n(?=Question\s*:)', re.IGNORECASE)
    parts = qa_pattern.split(text)

    # If Q&A splitting produced multiple sections, use them
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]

    # Otherwise, split on double newlines followed by header-like lines
    # (lines starting with emoji, or all-caps, or containing "📌" etc.)
    header_pattern = re.compile(r'\n\n+(?=[\U0001F300-\U0001FAFF]|[A-Z][A-Z\s&]+\n|#+\s)')
    parts = header_pattern.split(text)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]

    # Final fallback: just split on double newlines
    parts = re.split(r'\n\n+', text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(
    text: str,
    page_number: int = 1,
    document_name: str = "Unknown",
    source_type: str = "document",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """
    Split *text* into overlapping chunks, preserving Q&A pairs and sections.

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

    # Step 1: Split text into logical sections (preserving Q&A pairs)
    sections = _split_into_sections(text)

    # Step 2: Merge small sections into chunks up to chunk_size
    chunks: list[dict] = []
    current_buffer = ""
    idx = 0

    for section in sections:
        # If adding this section would exceed chunk_size...
        if current_buffer and (len(current_buffer) + len(section) + 2) > size:
            # Save the current buffer as a chunk
            if current_buffer.strip():
                chunks.append({
                    "text": current_buffer.strip(),
                    "page_number": page_number,
                    "document_name": document_name,
                    "source_type": source_type,
                    "chunk_index": idx,
                })
                idx += 1

            # Start new buffer — carry overlap from end of previous buffer
            if overlap > 0 and len(current_buffer) > overlap:
                # Take the last `overlap` characters as carry-over
                carry = current_buffer[-overlap:]
                # Try to start at a sentence/line boundary within the carry
                newline_pos = carry.find('\n')
                if newline_pos > 0:
                    carry = carry[newline_pos:]
                current_buffer = carry.strip() + "\n\n" + section
            else:
                current_buffer = section
        else:
            # Append section to current buffer
            if current_buffer:
                current_buffer += "\n\n" + section
            else:
                current_buffer = section

        # Safety: if a single section is bigger than chunk_size, force-split it
        if len(current_buffer) > size * 2:
            # Use the legacy character-based splitter for oversized sections
            sub_chunks = _force_split(current_buffer, size, overlap, page_number,
                                       document_name, source_type, idx)
            chunks.extend(sub_chunks)
            idx += len(sub_chunks)
            current_buffer = ""

    # Flush remaining buffer
    if current_buffer.strip():
        chunks.append({
            "text": current_buffer.strip(),
            "page_number": page_number,
            "document_name": document_name,
            "source_type": source_type,
            "chunk_index": idx,
        })

    return chunks


def _force_split(
    text: str,
    size: int,
    overlap: int,
    page_number: int,
    document_name: str,
    source_type: str,
    start_idx: int,
) -> list[dict]:
    """
    Character-based splitting for sections that exceed chunk_size.
    Tries to break at sentence boundaries.
    """
    chunks: list[dict] = []
    start = 0
    idx = start_idx

    while start < len(text):
        end = start + size

        # Try to break at a sentence boundary
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", "? ", "! "]:
                last_sep = text.rfind(sep, start, end)
                if last_sep > start:
                    end = last_sep + len(sep)
                    break

        chunk_str = text[start:end].strip()
        if chunk_str:
            chunks.append({
                "text": chunk_str,
                "page_number": page_number,
                "document_name": document_name,
                "source_type": source_type,
                "chunk_index": idx,
            })
            idx += 1

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
