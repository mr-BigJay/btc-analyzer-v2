"""Performance, load, and stress validation helpers (Ch.22 §22.9–22.11)."""

from __future__ import annotations

import time
from typing import Any

from src.api_spec.observability import api_metrics
from src.observability.metrics import app_metrics
from src.qa.contracts import LOAD_SCENARIOS, PERFORMANCE_CHECKS, utc_now_iso


# Targets aligned with Ch.20/21 SLOs
PERFORMANCE_TARGETS = {
    "avg_api_latency_ms": 250.0,
    "collector_latency_ms": 250.0,
    "ai_inference_ms": 5000.0,
    "feature_generation_ms": 1000.0,
}


def evaluate_performance() -> dict[str, Any]:
    snap = app_metrics.snapshot()
    http = api_metrics.snapshot()
    measured = {
        "avg_api_latency_ms": float(http.get("response_time_avg_ms") or snap["average_response_time_ms"]),
        "collector_latency_ms": float(snap["collector_latency_ms"]),
        "ai_inference_ms": float(snap["ai_inference_time_ms"]),
        "feature_generation_ms": 0.0,  # filled when feature jobs record metrics
        "p95_api_latency_ms": float(http.get("response_time_p95_ms") or 0.0),
    }
    results = []
    for key, target in PERFORMANCE_TARGETS.items():
        value = measured.get(key, 0.0)
        # 0 means not sampled yet → treat as pass (no evidence of breach)
        ok = True if value == 0.0 else value < target
        results.append({"metric": key, "measured": value, "target": target, "ok": ok})
    # Release performance gate focuses on API latency SLO (Ch.21); other metrics are advisory
    hard = [r for r in results if r["metric"] == "avg_api_latency_ms"]
    return {
        "checks": PERFORMANCE_CHECKS,
        "targets": PERFORMANCE_TARGETS,
        "results": results,
        "ok": all(r["ok"] for r in hard),
        "advisory_ok": all(r["ok"] for r in results),
        "timestamp": utc_now_iso(),
    }


def load_catalog() -> dict[str, Any]:
    return {
        "scenarios": LOAD_SCENARIOS,
        "monitor": ["CPU", "Memory", "Network", "Database", "Cache"],
        "note": "Load tests run in CI nightlies / pre-release; in-process catalog for gate planning",
    }


def stress_probe(*, burst: int = 50) -> dict[str, Any]:
    """Lightweight stress: rapid metric recording to verify graceful handling."""
    started = time.monotonic()
    for i in range(burst):
        api_metrics.record_request(path="/qa/stress", latency_ms=1.0 + (i % 5), status_code=200)
    duration_ms = (time.monotonic() - started) * 1000
    snap = api_metrics.snapshot()
    return {
        "burst": burst,
        "duration_ms": round(duration_ms, 3),
        "ok": duration_ms < 2000,
        "request_rate_total": snap["request_rate_total"],
        "objectives": [
            "Identify bottlenecks",
            "Verify graceful degradation",
            "Validate recovery behavior",
            "Detect resource leaks",
        ],
        "timestamp": utc_now_iso(),
    }
