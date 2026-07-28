"""Structured logging schema helpers (Ch.21 §21.9–21.11)."""

from __future__ import annotations

from typing import Any

from src.logging_setup import correlation_id_var
from src.observability.contracts import LogLevel, utc_now_iso


def structured_log_record(
    *,
    message: str,
    level: str = LogLevel.INFO.value,
    service: str = "api",
    module: str = "app",
    request_id: str | None = None,
    duration_ms: float | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a structured log object (Ch.21 schema)."""
    record: dict[str, Any] = {
        "timestamp": utc_now_iso(),
        "level": level.upper(),
        "service": service,
        "module": module,
        "request_id": request_id or correlation_id_var.get() or "-",
        "message": message,
    }
    if duration_ms is not None:
        record["duration_ms"] = round(float(duration_ms), 3)
    if extra:
        record["extra"] = extra
    return record


LOG_LEVELS = {level.value: purpose for level, purpose in [
    (LogLevel.TRACE, "Deep diagnostics"),
    (LogLevel.DEBUG, "Development"),
    (LogLevel.INFO, "Normal operations"),
    (LogLevel.WARNING, "Recoverable issues"),
    (LogLevel.ERROR, "Failed operation"),
    (LogLevel.CRITICAL, "Service-threatening condition"),
]}
