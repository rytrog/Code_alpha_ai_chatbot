"""
Rate Limiter — sliding-window in-memory limiter keyed by client IP.
Implemented as FastAPI middleware.
"""
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP sliding-window rate limiter.
    Configured via settings.RATE_LIMIT_REQUESTS / RATE_LIMIT_WINDOW_SECONDS.
    """

    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit API endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        limit = settings.RATE_LIMIT_REQUESTS

        # Prune old timestamps
        pruned_timestamps = [
            ts for ts in self._requests[client_ip]
            if now - ts < window
        ]
        if not pruned_timestamps:
            self._requests.pop(client_ip, None)
        else:
            self._requests[client_ip] = pruned_timestamps

        if len(self._requests[client_ip]) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded. Please try again later.",
                    "retry_after_seconds": window,
                },
            )

        self._requests[client_ip].append(now)
        response = await call_next(request)
        return response
