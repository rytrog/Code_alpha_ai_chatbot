"""
Input Validator — sanitises user messages and validates file uploads.
"""
import re
from config import settings


def validate_message(text: str) -> tuple[bool, str]:
    """
    Validate a chat message.
    Returns (is_valid, error_message).
    """
    if not text or not text.strip():
        return False, "Message cannot be empty."

    text = text.strip()

    if len(text) > settings.MAX_MESSAGE_LENGTH:
        return False, f"Message exceeds {settings.MAX_MESSAGE_LENGTH} characters."

    # Block HTML / script injection
    if re.search(r"<\s*script", text, re.IGNORECASE):
        return False, "Invalid input detected."

    # Block SQL injection patterns
    sql_patterns = [
        r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER)\s",
        r"('|\")\s*(OR|AND)\s*('|\")\s*=\s*('|\")",
        r"UNION\s+SELECT",
    ]
    for pattern in sql_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Invalid input detected."

    return True, ""


def validate_file(filename: str, file_size_bytes: int) -> tuple[bool, str]:
    """
    Validate an uploaded file by extension and size.
    Returns (is_valid, error_message).
    """
    if not filename:
        return False, "No filename provided."

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
        return False, f"File type '.{ext}' not allowed. Accepted: {allowed}."

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        return False, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit."

    return True, ""
