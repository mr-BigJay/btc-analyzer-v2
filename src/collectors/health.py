"""Collector health monitoring (Ch.12 §12.18).

Dashboard states: Healthy · Degraded · Recovering · Offline
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CollectorHealthStatus(str, Enum):
    HEALTHY = "Healthy"
    DEGRADED = "Degraded"
    RECOVERING = "Recovering"
    OFFLINE = "Offline"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class CollectorHealth:
    collector: str
    status: CollectorHealthStatus = CollectorHealthStatus.OFFLINE
    latency_ms: float | None = None
    last_message: str | None = None
    error_rate: float = 0.0
    success_count: int = 0
    error_count: int = 0
    last_error: str | None = None
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collector": self.collector,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "last_message": self.last_message,
            "error_rate": round(self.error_rate, 4),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "updated_at": self.updated_at,
        }


class HealthMonitor:
    """Tracks per-collector operational health."""

    def __init__(self) -> None:
        self._states: dict[str, CollectorHealth] = {}
        self._lock = threading.RLock()

    def ensure(self, collector: str) -> CollectorHealth:
        with self._lock:
            if collector not in self._states:
                self._states[collector] = CollectorHealth(collector=collector)
            return self._states[collector]

    def record_success(self, collector: str, *, latency_ms: float | None = None) -> CollectorHealth:
        with self._lock:
            h = self.ensure(collector)
            h.success_count += 1
            h.latency_ms = latency_ms
            h.last_message = _utc_now()
            h.updated_at = h.last_message
            h.last_error = None
            total = h.success_count + h.error_count
            h.error_rate = (h.error_count / total) if total else 0.0
            if h.status == CollectorHealthStatus.OFFLINE:
                h.status = CollectorHealthStatus.RECOVERING
            elif h.status == CollectorHealthStatus.RECOVERING and h.success_count >= 2:
                h.status = CollectorHealthStatus.HEALTHY
            elif h.error_rate > 0.05:
                h.status = CollectorHealthStatus.DEGRADED
            else:
                h.status = CollectorHealthStatus.HEALTHY
            # Latency SLO soft signal (Ch.12 §12.20 spot < 250ms)
            if latency_ms is not None and latency_ms > 250:
                h.status = CollectorHealthStatus.DEGRADED
            return h

    def record_error(self, collector: str, error: str | None = None) -> CollectorHealth:
        with self._lock:
            h = self.ensure(collector)
            h.error_count += 1
            h.last_error = error
            h.updated_at = _utc_now()
            total = h.success_count + h.error_count
            h.error_rate = (h.error_count / total) if total else 1.0
            if h.error_rate >= 0.5 or h.success_count == 0:
                h.status = CollectorHealthStatus.OFFLINE
            else:
                h.status = CollectorHealthStatus.DEGRADED
            return h

    def mark_recovering(self, collector: str) -> CollectorHealth:
        with self._lock:
            h = self.ensure(collector)
            h.status = CollectorHealthStatus.RECOVERING
            h.updated_at = _utc_now()
            return h

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            collectors = {k: v.to_dict() for k, v in self._states.items()}
        statuses = [c["status"] for c in collectors.values()]
        if not statuses:
            overall = CollectorHealthStatus.OFFLINE.value
        elif all(s == CollectorHealthStatus.HEALTHY.value for s in statuses):
            overall = CollectorHealthStatus.HEALTHY.value
        elif all(s == CollectorHealthStatus.OFFLINE.value for s in statuses):
            overall = CollectorHealthStatus.OFFLINE.value
        elif any(s == CollectorHealthStatus.RECOVERING.value for s in statuses):
            overall = CollectorHealthStatus.RECOVERING.value
        else:
            overall = CollectorHealthStatus.DEGRADED.value
        return {"overall": overall, "collectors": collectors}


health_monitor = HealthMonitor()
