"""Operational alert evaluation (Ch.21 §21.16)."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any

from src.observability.contracts import ALERT_CONDITIONS, utc_now_iso
from src.observability.metrics import app_metrics
from src.observability.slo import evaluate_slos


class AlertStore:
    def __init__(self, maxlen: int = 500) -> None:
        self._lock = threading.Lock()
        self._alerts: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def emit(self, *, condition: str, severity: str, detail: str, service: str = "api") -> dict[str, Any]:
        row = {
            "alert_id": f"obs-{len(self._alerts)+1}-{int(__import__('time').time())}",
            "condition": condition,
            "severity": severity,
            "detail": detail,
            "service": service,
            "timestamp": utc_now_iso(),
            "status": "active",
        }
        with self._lock:
            self._alerts.append(row)
        return row

    def list(self, *, limit: int = 50, active_only: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(reversed(self._alerts))
        if active_only:
            rows = [r for r in rows if r.get("status") == "active"]
        return rows[:limit]

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._alerts if r.get("status") == "active")

    def clear(self) -> None:
        with self._lock:
            self._alerts.clear()


alert_store = AlertStore()


def evaluate_alerts(*, db_ok: bool = True, exchange_connected: bool = True) -> dict[str, Any]:
    snap = app_metrics.snapshot()
    slo = evaluate_slos()
    fired: list[dict[str, Any]] = []

    latency = snap["average_response_time_ms"]
    error_pct = snap["error_percentage"]
    dqs = snap["data_quality_score"]

    if not db_ok:
        fired.append(alert_store.emit(condition="Database connection failures", severity="critical", detail="DB probe failed"))
    if latency >= 250:
        fired.append(
            alert_store.emit(
                condition="API latency exceeds threshold",
                severity="warning",
                detail=f"avg_latency_ms={latency}",
            )
        )
    if error_pct >= 5.0:
        fired.append(
            alert_store.emit(
                condition="High error rate",
                severity="warning",
                detail=f"error_percentage={error_pct}",
            )
        )
    if dqs < 90:
        fired.append(
            alert_store.emit(
                condition="Data Quality Score degradation",
                severity="warning",
                detail=f"dqs={dqs}",
            )
        )
    if not exchange_connected:
        fired.append(alert_store.emit(condition="Exchange disconnection", severity="critical", detail="exchange offline"))

    ai_ms = snap["ai_inference_time_ms"]
    if ai_ms >= 5000:
        fired.append(
            alert_store.emit(
                condition="AI response timeout",
                severity="warning",
                detail=f"ai_inference_ms={ai_ms}",
            )
        )

    return {
        "conditions": ALERT_CONDITIONS,
        "evaluated_at": utc_now_iso(),
        "fired": fired,
        "active_alerts": alert_store.active_count(),
        "slo_breaches": [r for r in slo["slos"] if not r["ok"]],
        "recent": alert_store.list(limit=20),
    }
