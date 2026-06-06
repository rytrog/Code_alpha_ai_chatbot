"""
Source Service — formats source citations for every answer.

Example output:
  "Hostel Fee Circular 2026 (Page 3), Admission Brochure 2026 (Page 12)"
"""


def format_sources(context_chunks: list[dict]) -> str:
    """
    Build a human-readable source citation string
    from the RAG context metadata.
    """
    if not context_chunks:
        return ""

    sources: list[str] = []
    for chunk in context_chunks:
        doc_name = chunk.get("document_name", "Unknown Document")
        page = chunk.get("page_number", "")
        label = f"{doc_name} (Page {page})" if page else doc_name
        if label not in sources:
            sources.append(label)

    return ", ".join(sources)
