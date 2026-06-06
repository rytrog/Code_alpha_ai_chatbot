"""
PDF Loader — extracts text page-by-page using PyMuPDF (fitz).
"""
import fitz  # PyMuPDF
from pathlib import Path
from utils.logger import logger


def extract_pdf(file_path: str) -> list[dict]:
    """
    Extract text from a PDF file.

    Returns list of dicts:
      [{"text": "...", "page_number": 1}, ...]
    """
    pages: list[dict] = []
    path = Path(file_path)

    if not path.exists():
        logger.error(f"PDF file not found: {file_path}")
        return pages

    try:
        doc = fitz.open(str(path))
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()
                if text:
                    # Clean up excessive whitespace
                    cleaned = " ".join(text.split())
                    pages.append({
                        "text": cleaned,
                        "page_number": page_num + 1,
                    })
            logger.info(f"Extracted {len(pages)} pages from {path.name}")
        finally:
            doc.close()
    except Exception as e:
        logger.error(f"PDF extraction error for {file_path}: {e}")

    return pages
