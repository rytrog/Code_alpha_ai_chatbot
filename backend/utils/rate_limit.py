"""
Rate Limiter — Dual-layer in-memory sliding-window limiter.
1. Session-based (X-Client-ID header or IP fallback): 20 req/min, 100 req/hour.
2. IP-based (client IP): 300 req/hour.
"""
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from config import settings
from utils.logger import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for session-level and IP-level traffic protection.
    """
    # Shared in-memory request records (class-level variables for easy access/testing)
    _session_requests: dict[str, list[float]] = defaultdict(list)
    _ip_requests: dict[str, list[float]] = defaultdict(list)

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit API endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # ── 1. Resolve Identifiers ──
        client_ip = request.client.host if request.client else "unknown"
        
        # Get client session UUID from the header
        client_id = request.headers.get("x-client-id")
        if not client_id:
            # Fallback to client IP if X-Client-ID is missing
            client_id = client_ip

        now = time.time()

        # ── 2. Session Rate Limiter (Dual Sliding Windows) ──
        session_min_window = 60
        session_hour_window = 3600
        
        session_min_limit = settings.SESSION_LIMIT_MIN
        session_hour_limit = settings.SESSION_LIMIT_HOUR

        # Fetch and prune session records (keep only the last hour)
        session_history = self._session_requests[client_id]
        pruned_session = [ts for ts in session_history if now - ts < session_hour_window]
        
        if not pruned_session:
            self._session_requests.pop(client_id, None)
            session_history = []
        else:
            self._session_requests[client_id] = pruned_session
            session_history = pruned_session

        # A. Check session minute limit
        recent_session_min = [ts for ts in session_history if now - ts < session_min_window]
        if len(recent_session_min) >= session_min_limit:
            logger.warning(
                f"RateLimit | Session '{client_id}' exceeded minute limit: "
                f"{len(recent_session_min)}/{session_min_limit} reqs"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Session rate limit exceeded (20 requests per minute). Please try again later.",
                    "retry_after_seconds": session_min_window,
                },
            )

        # B. Check session hourly limit
        if len(session_history) >= session_hour_limit:
            logger.warning(
                f"RateLimit | Session '{client_id}' exceeded hourly limit: "
                f"{len(session_history)}/{session_hour_limit} reqs"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Session rate limit exceeded (100 requests per hour). Please try again later.",
                    "retry_after_seconds": session_hour_window,
                },
            )

        # ── 3. IP Rate Limiter (Single Hourly Window) ──
        ip_window = 3600
        ip_limit = settings.IP_LIMIT_HOUR

        # Fetch and prune IP records
        ip_history = self._ip_requests[client_ip]
        pruned_ip = [ts for ts in ip_history if now - ts < ip_window]
        
        if not pruned_ip:
            self._ip_requests.pop(client_ip, None)
            ip_history = []
        else:
            self._ip_requests[client_ip] = pruned_ip
            ip_history = pruned_ip

        # Check IP hourly limit
        if len(ip_history) >= ip_limit:
            logger.warning(
                f"RateLimit | IP '{client_ip}' exceeded limit: "
                f"{len(ip_history)}/{ip_limit} reqs"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "IP rate limit exceeded (300 requests per hour). Please try again later.",
                    "retry_after_seconds": ip_window,
                },
            )

        # ── 4. Log Request and Proceed ──
        self._session_requests[client_id].append(now)
        self._ip_requests[client_ip].append(now)

        return await call_next(request)
