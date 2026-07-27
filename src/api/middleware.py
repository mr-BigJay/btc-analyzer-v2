"""API middleware — request IDs, secure headers, rate limiting (Ch.5 §5.7 / §5.14)."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.responses import failure
from src.config import settings
from src.logging_setup import correlation_id_var, get_logger

log = get_logger("api.middleware")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request_id / correlation_id and secure headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = correlation_id_var.set(request_id)
        request.state.request_id = request_id
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001
            log.exception("Unhandled API error: {}", exc)
            return failure(
                "Internal server error",
                code="INTERNAL_ERROR",
                request_id=request_id,
                status_code=500,
            )
        finally:
            correlation_id_var.reset(token)

        duration_ms = (time.monotonic() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
        # Secure headers (Ch.5 §5.14)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-process sliding-window rate limiter."""

    def __init__(self, app, *, limit: int | None = None, window_sec: float = 60.0) -> None:
        super().__init__(app)
        self.limit = limit if limit is not None else settings.api_rate_limit_per_minute
        self.window_sec = window_sec
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/ws"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self._hits[client]
        while bucket and now - bucket[0] > self.window_sec:
            bucket.popleft()
        if len(bucket) >= self.limit:
            request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
            return failure(
                "Rate limit exceeded",
                code="RATE_LIMIT",
                request_id=request_id,
                status_code=429,
            )
        bucket.append(now)
        return await call_next(request)
