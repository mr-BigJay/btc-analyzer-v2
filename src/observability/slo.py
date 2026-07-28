"""SLI / SLO / error budget evaluation (Ch.21 §21.14–21.19)."""

from __future__ import annotations

from typing import Any

from src.observability.contracts import SLIS, SLOS
from src.observability.metrics import app_metrics


def evaluate_slos(*, api_availability: float | None = None, collector_availability: float | None = None) -> dict[str, Any]:
    snap = app_metrics.snapshot()
    http = snap["http"]
    # Derive availability from successful requests
    req = http["request_rate_total"]
    err = http.get("error_rate", 0.0) * req if req else 0.0
    derived_avail = ((req - err) / req * 100.0) if req else 100.0
    api_avail = api_availability if api_availability is not None else derived_avail
    coll_avail = collector_availability if collector_availability is not None else 100.0
    latency = float(snap["average_response_time_ms"])
    freshness = 0.0  # seconds; 0 means fresh when unknown in-process

    measured = {
        "api_availability": round(api_avail, 4),
        "collector_availability": round(coll_avail, 4),
        "dashboard_availability": round(api_avail, 4),
        "avg_api_latency_ms": latency,
        "market_data_freshness_sec": freshness,
    }

    results = []
    for key, meta in SLOS.items():
        target = float(meta["target"])
        value = float(measured[key])
        comparator = meta.get("comparator", ">=")
        if comparator == "<":
            ok = value < target
            budget_used = max(0.0, (value - target) / target) if target else 0.0
            remaining = max(0.0, 1.0 - budget_used) if not ok else 1.0
        else:
            # availability-style: target is minimum %
            ok = value >= target
            allowed_failure = max(0.0, 100.0 - target)
            actual_failure = max(0.0, 100.0 - value)
            budget_used = (actual_failure / allowed_failure) if allowed_failure else 0.0
            remaining = max(0.0, 1.0 - budget_used)
        results.append(
            {
                "key": key,
                "label": meta["label"],
                "target": target,
                "unit": meta["unit"],
                "comparator": comparator,
                "measured": value,
                "ok": ok,
                "error_budget_remaining": round(remaining, 4),
                "error_budget_consumed": round(min(budget_used, 1.0), 4),
            }
        )

    return {
        "slis": SLIS,
        "slos": results,
        "all_ok": all(r["ok"] for r in results),
        "error_budget_example": {
            "availability_target": "99.9%",
            "allowed_failure_budget": "0.1%",
        },
    }
