"""Operational anomaly detection (Ch.21 §21.18)."""

from __future__ import annotations

from typing import Any

from src.observability.contracts import utc_now_iso
from src.observability.metrics import app_metrics


def detect_anomalies() -> dict[str, Any]:
    snap = app_metrics.snapshot()
    http = snap["http"]
    findings: list[dict[str, Any]] = []

    latency = snap["average_response_time_ms"]
    p95 = http.get("response_time_p95_ms", 0.0)
    if latency > 0 and p95 > latency * 3 and p95 >= 200:
        findings.append(
            {
                "type": "Unexpected latency spikes",
                "detail": f"p95={p95} avg={latency}",
                "severity": "warning",
            }
        )

    if snap["collector_latency_ms"] >= 500:
        findings.append(
            {
                "type": "Collector slowdown",
                "detail": f"collector_latency_ms={snap['collector_latency_ms']}",
                "severity": "warning",
            }
        )

    if snap["error_percentage"] >= 10:
        findings.append(
            {
                "type": "Sudden increase in failed requests",
                "detail": f"error_percentage={snap['error_percentage']}",
                "severity": "critical",
            }
        )

    if snap["websocket_reconnect_frequency"] >= 20:
        findings.append(
            {
                "type": "Abnormal market data gaps",
                "detail": f"ws_reconnects={snap['websocket_reconnect_frequency']}",
                "severity": "warning",
            }
        )

    return {
        "detected_at": utc_now_iso(),
        "count": len(findings),
        "findings": findings,
        "investigation_events": [
            {**f, "event": "anomaly_investigation", "timestamp": utc_now_iso()} for f in findings
        ],
    }
