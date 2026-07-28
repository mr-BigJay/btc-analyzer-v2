"""Application / market / AI metric registries (Ch.21 §21.5–21.8)."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from src.api_spec.observability import api_metrics
from src.observability.contracts import utc_now_iso


class AppMetricStore:
    """Extended application metrics beyond HTTP ApiMetrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.cache_hits = 0
        self.cache_misses = 0
        self.ai_inference_ms: deque[float] = deque(maxlen=500)
        self.ai_confidence: deque[float] = deque(maxlen=500)
        self.scheduler_ms: deque[float] = deque(maxlen=200)
        self.collector_latency_ms: deque[float] = deque(maxlen=500)
        self.dqs_samples: deque[float] = deque(maxlen=200)
        self.ws_reconnects = 0
        self.db_latency_ms: deque[float] = deque(maxlen=500)
        self.active_sessions = 0
        self.started_at = time.time()

    def record_cache(self, *, hit: bool) -> None:
        with self._lock:
            if hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1

    def record_ai(self, *, inference_ms: float, confidence: float | None = None) -> None:
        with self._lock:
            self.ai_inference_ms.append(inference_ms)
            if confidence is not None:
                self.ai_confidence.append(confidence)

    def record_scheduler(self, duration_ms: float) -> None:
        with self._lock:
            self.scheduler_ms.append(duration_ms)

    def record_collector(self, latency_ms: float) -> None:
        with self._lock:
            self.collector_latency_ms.append(latency_ms)

    def record_dqs(self, score: float) -> None:
        with self._lock:
            self.dqs_samples.append(score)

    def record_ws_reconnect(self) -> None:
        with self._lock:
            self.ws_reconnects += 1

    def record_db(self, latency_ms: float) -> None:
        with self._lock:
            self.db_latency_ms.append(latency_ms)

    def set_active_sessions(self, n: int) -> None:
        with self._lock:
            self.active_sessions = n

    def _avg(self, values: deque[float]) -> float:
        return round(sum(values) / len(values), 3) if values else 0.0

    def snapshot(self) -> dict[str, Any]:
        http = api_metrics.snapshot()
        with self._lock:
            total_cache = self.cache_hits + self.cache_misses
            hit_ratio = (self.cache_hits / total_cache) if total_cache else 1.0
            uptime = max(time.time() - self.started_at, 1.0)
            rps = http["request_rate_total"] / uptime
            return {
                "http": http,
                "requests_per_second": round(rps, 3),
                "average_response_time_ms": http["response_time_avg_ms"],
                "error_percentage": round(http["error_rate"] * 100, 4),
                "active_sessions": self.active_sessions,
                "active_websocket_connections": http["active_websocket_connections"],
                "cache_hit_ratio": round(hit_ratio, 4),
                "collector_latency_ms": self._avg(self.collector_latency_ms),
                "ai_inference_time_ms": self._avg(self.ai_inference_ms),
                "ai_confidence_avg": self._avg(self.ai_confidence),
                "scheduler_execution_time_ms": self._avg(self.scheduler_ms),
                "database_response_time_ms": self._avg(self.db_latency_ms),
                "data_quality_score": self._avg(self.dqs_samples) if self.dqs_samples else 100.0,
                "websocket_reconnect_frequency": self.ws_reconnects,
                "updated_at": utc_now_iso(),
            }


app_metrics = AppMetricStore()
