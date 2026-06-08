"""
Logger — structured logging with file rotation.
Separate files for api.log and error.log.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from config import settings

# Ensure log directory exists
os.makedirs(settings.LOG_DIR, exist_ok=True)

# ── Formatter ──
_fmt = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── API log handler (all levels) ──
_api_handler = RotatingFileHandler(
    os.path.join(settings.LOG_DIR, "api.log"),
    maxBytes=5 * 1024 * 1024,   # 5 MB
    backupCount=5,
    encoding="utf-8",
)
_api_handler.setFormatter(_fmt)
_api_handler.setLevel(logging.DEBUG)

# ── Error log handler (ERROR+ only) ──
_error_handler = RotatingFileHandler(
    os.path.join(settings.LOG_DIR, "error.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_error_handler.setFormatter(_fmt)
_error_handler.setLevel(logging.ERROR)

# ── Console handler ──
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)
_console_handler.setLevel(logging.DEBUG)

# ── Root logger for the app ──
logger = logging.getLogger("university_ai")
logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger.addHandler(_api_handler)
logger.addHandler(_error_handler)
logger.addHandler(_console_handler)
logger.propagate = False
