"""Collection quality metrics contributing to DQS (Ch.12 §12.11 / §12.20)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


# Performance targets (Ch.12 §12.20)
PERFORMANCE_TARGETS: dict[str, float] = {
    "spot_latency_ms": 250.0,
    "websocket_reconnect_s": 5.0,
    "validation_time_ms": 10.0,
    "normalization_time_ms": 5.0,
    "api_availability": 0.999,
    "collector_uptime": 0.9995,
}


@dataclass
class CollectorMetrics:
    collector: str
    samples: int = 0
    latency_sum_ms: float = 0.0
    validation_sum_ms: float = 0.0
    normalization_sum_ms: float = 0.0
    success: int = 0
    failure: int = 0
    message_loss: int = 0
    sync_delay_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float | None:
        return (self.latency_sum_ms / self.samples) if self.samples else None

    @property
    def availability(self) -> float:
        total = self.success + self.failure
        return (self.success / total) if total else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "collector": self.collector,
            "samples": self.samples,
            "avg_latency_ms": round(self.avg_latency_ms, 3) if self.avg_latency_ms is not None else None,
            "avg_validation_ms": round(self.validation_sum_ms / self.samples, 3) if self.samples else None,
            "avg_normalization_ms": round(self.normalization_sum_ms / self.samples, 3) if self.samples else None,
            "availability": round(self.availability, 6),
            "message_loss": self.message_loss,
            "sync_delay_ms": self.sync_delay_ms,
            "success": self.success,
            "failure": self.failure,
        }


class MetricsRegistry:
    def __init__(self) -> None:
        self._metrics: dict[str, CollectorMetrics] = {}
        self._lock = threading.RLock()

    def record(
        self,
        collector: str,
        *,
        success: bool,
        latency_ms: float | None = None,
        validation_ms: float | None = None,
        normalization_ms: float | None = None,
        message_loss: int = 0,
        sync_delay_ms: float | None = None,
    ) -> CollectorMetrics:
        with self._lock:
            m = self._metrics.setdefault(collector, CollectorMetrics(collector=collector))
            m.samples += 1
            if success:
                m.success += 1
            else:
                m.failure += 1
            if latency_ms is not None:
                m.latency_sum_ms += latency_ms
            if validation_ms is not None:
                m.validation_sum_ms += validation_ms
            if normalization_ms is not None:
                m.normalization_sum_ms += normalization_ms
            m.message_loss += message_loss
            if sync_delay_ms is not None:
                m.sync_delay_ms = sync_delay_ms
            return m

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            collectors = {k: v.to_dict() for k, v in self._metrics.items()}
        return {
            "targets": PERFORMANCE_TARGETS,
            "collectors": collectors,
            "dqs_inputs": self.dqs_contribution(),
        }

    def dqs_contribution(self) -> dict[str, Any]:
        """Aggregate inputs for system-wide Data Quality Score."""
        with self._lock:
            items = list(self._metrics.values())
        if not items:
            return {
                "availability": 0.0,
                "avg_latency_ms": None,
                "error_pressure": 1.0,
                "score_hint": 50.0,
            }
        avail = sum(i.availability for i in items) / len(items)
        latencies = [i.avg_latency_ms for i in items if i.avg_latency_ms is not None]
        avg_lat = sum(latencies) / len(latencies) if latencies else None
        failures = sum(i.failure for i in items)
        successes = sum(i.success for i in items)
        total = failures + successes
        error_pressure = (failures / total) if total else 1.0
        # Hint 0–100: availability ↑, latency/error ↓
        score = avail * 100.0
        if avg_lat is not None and avg_lat > PERFORMANCE_TARGETS["spot_latency_ms"]:
            score -= min(25.0, (avg_lat - PERFORMANCE_TARGETS["spot_latency_ms"]) / 20.0)
        score -= error_pressure * 40.0
        score = max(0.0, min(100.0, score))
        return {
            "availability": round(avail, 6),
            "avg_latency_ms": round(avg_lat, 3) if avg_lat is not None else None,
            "error_pressure": round(error_pressure, 4),
            "score_hint": round(score, 1),
        }


metrics_registry = MetricsRegistry()
