"""Shared retry, rate-limit, and structured logging for collectors (Ch.3 §3.15–3.17)."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger("btc_analyzer.collector")

T = TypeVar("T")

# Retry policy (Ch.3 §3.15): 5s → 15s → 30s then caller falls back to cache
RETRY_DELAYS_SEC = (5.0, 15.0, 30.0)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CollectorLogEntry:
    timestamp: str
    exchange: str
    endpoint: str
    response_time_ms: float
    status: str
    error_code: str | None = None
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "exchange": self.exchange,
            "endpoint": self.endpoint,
            "response_time_ms": self.response_time_ms,
            "status": self.status,
            "error_code": self.error_code,
            "retry_count": self.retry_count,
        }


def log_collector_event(
    exchange: str,
    endpoint: str,
    response_time_ms: float,
    status: str,
    error_code: str | None = None,
    retry_count: int = 0,
) -> None:
    entry = CollectorLogEntry(
        timestamp=utc_now_iso(),
        exchange=exchange,
        endpoint=endpoint,
        response_time_ms=response_time_ms,
        status=status,
        error_code=error_code,
        retry_count=retry_count,
    )
    logger.info("collector_event %s", entry.to_dict())


@dataclass
class TokenBucketLimiter:
    """Token-bucket rate limiter (Ch.3 §3.16)."""

    rate_per_sec: float = 10.0
    capacity: float = 10.0
    tokens: float = 10.0
    updated_at: float = field(default_factory=time.monotonic)
    paused_until: float = 0.0

    def pause(self, seconds: float) -> None:
        self.paused_until = max(self.paused_until, time.monotonic() + seconds)

    def acquire(self, tokens: float = 1.0) -> float:
        """Return seconds to wait before the request may proceed."""
        now = time.monotonic()
        if now < self.paused_until:
            return self.paused_until - now
        elapsed = now - self.updated_at
        self.updated_at = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_sec)
        if self.tokens >= tokens:
            self.tokens -= tokens
            return 0.0
        needed = tokens - self.tokens
        return needed / self.rate_per_sec

    async def wait(self, tokens: float = 1.0) -> None:
        delay = self.acquire(tokens)
        if delay > 0:
            await asyncio.sleep(delay)


@dataclass
class RetryHandler:
    """Retry with 5s → 15s → 30s backoff (Ch.3 §3.15)."""

    delays_sec: tuple[float, ...] = RETRY_DELAYS_SEC

    async def run(
        self,
        exchange: str,
        endpoint: str,
        operation: Callable[[], Awaitable[T]],
    ) -> tuple[T | None, int, str | None]:
        last_error: str | None = None
        attempts = (0.0, *self.delays_sec)
        for attempt, delay in enumerate(attempts):
            if delay:
                await asyncio.sleep(delay)
            started = time.monotonic()
            try:
                value = await operation()
                elapsed_ms = (time.monotonic() - started) * 1000
                log_collector_event(exchange, endpoint, elapsed_ms, "OK", retry_count=attempt)
                return value, attempt, None
            except Exception as exc:  # noqa: BLE001
                elapsed_ms = (time.monotonic() - started) * 1000
                last_error = str(exc)
                log_collector_event(
                    exchange,
                    endpoint,
                    elapsed_ms,
                    "ERROR",
                    error_code=type(exc).__name__,
                    retry_count=attempt,
                )
        return None, len(self.delays_sec), last_error


@dataclass(order=True)
class PriorityRequest:
    """Priority queue item — lower number = higher priority (Ch.3 §3.16)."""

    priority: int
    created_at: float = field(compare=True)
    endpoint: str = field(compare=False, default="")
    critical: bool = field(compare=False, default=False)


class RequestQueue:
    """Simple priority request queue for collectors."""

    CRITICAL = 0
    NORMAL = 5
    BACKGROUND = 10

    def __init__(self) -> None:
        self._items: list[PriorityRequest] = []

    def enqueue(self, endpoint: str, *, critical: bool = False, background: bool = False) -> None:
        if critical:
            priority = self.CRITICAL
        elif background:
            priority = self.BACKGROUND
        else:
            priority = self.NORMAL
        self._items.append(
            PriorityRequest(
                priority=priority,
                created_at=time.monotonic(),
                endpoint=endpoint,
                critical=critical,
            )
        )
        self._items.sort()

    def dequeue(self) -> PriorityRequest | None:
        if not self._items:
            return None
        return self._items.pop(0)

    def __len__(self) -> int:
        return len(self._items)
