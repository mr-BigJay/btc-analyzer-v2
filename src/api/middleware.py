"""API middleware — request IDs, secure headers, rate limiting (Ch.5 / Ch.18 / Ch.19)."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.responses import failure
from src.api_spec.auth import authenticate_headers, effective_rate_limit
from src.api_spec.observability import api_metrics
from src.config import settings
from src.logging_setup import correlation_id_var, get_logger
from src.security.contracts import AuditAction
from src.security.hardening import apply_security_headers

log = get_logger("api.middleware")


def _is_streaming_path(path: str) -> bool:
    return path.startswith("/ws") or path.startswith("/api/v1/ws")


def _is_https(request: Request) -> bool:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    return str(proto).lower() == "https"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request_id / correlation_id and secure headers (Ch.19 §19.23)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = correlation_id_var.set(request_id)
        request.state.request_id = request_id
        request.state.principal = authenticate_headers(request.headers)
        started = time.monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
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
        if not _is_streaming_path(request.url.path):
            api_metrics.record_request(path=request.url.path, latency_ms=duration_ms, status_code=status_code)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
        response.headers["X-API-Version"] = "v1"
        apply_security_headers(response.headers, https=_is_https(request))
        # Legacy XSS header retained for older browsers
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter with authenticated higher limits + abuse audit."""

    def __init__(self, app, *, limit: int | None = None, window_sec: float = 60.0) -> None:
        super().__init__(app)
        self.default_limit = limit if limit is not None else settings.api_rate_limit_per_minute
        self.window_sec = window_sec
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if _is_streaming_path(request.url.path):
            return await call_next(request)

        principal = authenticate_headers(request.headers)
        limit = effective_rate_limit(principal) if principal else self.default_limit
        client = request.client.host if request.client else "unknown"
        bucket_key = f"{client}:{getattr(principal, 'subject', 'anon')}"
        now = time.monotonic()
        bucket = self._hits[bucket_key]
        while bucket and now - bucket[0] > self.window_sec:
            bucket.popleft()
        if len(bucket) >= limit:
            request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
            api_metrics.record_rate_limit()
            try:
                from src.security.audit import audit_trail

                audit_trail.append(
                    AuditAction.RATE_LIMIT,
                    actor=getattr(principal, "subject", "anonymous") if principal else "anonymous",
                    outcome="denied",
                    resource=request.url.path,
                    detail=f"limit={limit}",
                    request_id=request_id,
                    ip=client,
                )
            except Exception:  # noqa: BLE001
                pass
            resp = failure(
                "Rate limit exceeded",
                code="RATE_LIMIT",
                request_id=request_id,
                details={"limit": limit, "window_sec": self.window_sec, "retry_after_sec": int(self.window_sec)},
                status_code=429,
            )
            resp.headers["Retry-After"] = str(int(self.window_sec))
            resp.headers["X-RateLimit-Limit"] = str(limit)
            resp.headers["X-RateLimit-Remaining"] = "0"
            return resp
        bucket.append(now)
        response = await call_next(request)
        remaining = max(0, limit - len(bucket))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
