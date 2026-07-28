"""API observability metrics (Ch.18 §18.23)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any


class ApiMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.request_count = 0
        self.error_count = 0
        self.auth_failures = 0
        self.rate_limit_events = 0
        self._latencies: deque[float] = deque(maxlen=1000)
        self._by_path: dict[str, int] = defaultdict(int)
        self.ws_connections = 0
        self.started_at = time.time()

    def record_request(self, *, path: str, latency_ms: float, status_code: int) -> None:
        with self._lock:
            self.request_count += 1
            self._by_path[path] += 1
            self._latencies.append(latency_ms)
            if status_code >= 400:
                self.error_count += 1
            if status_code == 429:
                self.rate_limit_events += 1
            if status_code == 401:
                self.auth_failures += 1

    def record_auth_failure(self) -> None:
        with self._lock:
            self.auth_failures += 1

    def record_rate_limit(self) -> None:
        with self._lock:
            self.rate_limit_events += 1
            self.error_count += 1
            self.request_count += 1

    def set_ws_connections(self, n: int) -> None:
        with self._lock:
            self.ws_connections = n

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            lat = list(self._latencies)
            avg = sum(lat) / len(lat) if lat else 0.0
            p95 = sorted(lat)[int(len(lat) * 0.95)] if len(lat) >= 20 else (lat[-1] if lat else 0.0)
            return {
                "request_rate_total": self.request_count,
                "response_time_avg_ms": round(avg, 2),
                "response_time_p95_ms": round(p95, 2),
                "error_rate": round(self.error_count / self.request_count, 4) if self.request_count else 0.0,
                "authentication_failures": self.auth_failures,
                "active_websocket_connections": self.ws_connections,
                "rate_limit_events": self.rate_limit_events,
                "top_paths": dict(sorted(self._by_path.items(), key=lambda kv: kv[1], reverse=True)[:10]),
                "uptime_sec": round(time.time() - self.started_at, 1),
            }


api_metrics = ApiMetrics()
