"""In-process distributed tracing (Ch.21 §21.12)."""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator

from src.logging_setup import correlation_id_var
from src.observability.contracts import utc_now_iso

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
span_id_var: ContextVar[str | None] = ContextVar("span_id", default=None)


@dataclass
class Span:
    span_id: str
    trace_id: str
    name: str
    service: str = "api"
    parent_span_id: str | None = None
    correlation_id: str | None = None
    started_at: str = field(default_factory=utc_now_iso)
    ended_at: str | None = None
    duration_ms: float | None = None
    status: str = "ok"
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TraceStore:
    """Ring buffer of completed spans for request reconstruction."""

    def __init__(self, maxlen: int = 2000) -> None:
        self._lock = threading.Lock()
        self._spans: deque[Span] = deque(maxlen=maxlen)

    def add(self, span: Span) -> None:
        with self._lock:
            self._spans.append(span)

    def list(
        self,
        *,
        limit: int = 50,
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._spans)
        if trace_id:
            rows = [s for s in rows if s.trace_id == trace_id]
        if correlation_id:
            rows = [s for s in rows if s.correlation_id == correlation_id]
        rows = list(reversed(rows))[:limit]
        return [s.to_dict() for s in rows]

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()


trace_store = TraceStore()


def start_span(
    name: str,
    *,
    service: str = "api",
    attributes: dict[str, Any] | None = None,
) -> tuple[Span, float, Any, Any]:
    parent = span_id_var.get()
    trace_id = trace_id_var.get() or str(uuid.uuid4())
    span = Span(
        span_id=str(uuid.uuid4()),
        trace_id=trace_id,
        name=name,
        service=service,
        parent_span_id=parent,
        correlation_id=correlation_id_var.get(),
        attributes=dict(attributes or {}),
    )
    t_token = trace_id_var.set(trace_id)
    s_token = span_id_var.set(span.span_id)
    return span, time.monotonic(), t_token, s_token


def end_span(
    span: Span,
    started_mono: float,
    t_token: Any,
    s_token: Any,
    *,
    status: str = "ok",
    attributes: dict[str, Any] | None = None,
) -> Span:
    span.ended_at = utc_now_iso()
    span.duration_ms = round((time.monotonic() - started_mono) * 1000, 3)
    span.status = status
    if attributes:
        span.attributes.update(attributes)
    trace_store.add(span)
    span_id_var.reset(s_token)
    # Keep trace_id for sibling spans under same request; reset only when returning to parent-less
    if span.parent_span_id is None:
        trace_id_var.reset(t_token)
    return span


@contextmanager
def traced(
    name: str,
    *,
    service: str = "api",
    attributes: dict[str, Any] | None = None,
) -> Iterator[Span]:
    span, started, t_token, s_token = start_span(name, service=service, attributes=attributes)
    status = "ok"
    try:
        yield span
    except Exception:
        status = "error"
        raise
    finally:
        end_span(span, started, t_token, s_token, status=status)


TRACKED_OPERATIONS = [
    "API request lifecycle",
    "Market analysis",
    "Feature generation",
    "AI inference",
    "Database access",
    "Collector execution",
]
