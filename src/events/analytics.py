"""Event analytics / operational metrics (Ch.16 §16.18)."""

from __future__ import annotations

from typing import Any


def compute_analytics(events: list[dict[str, Any]]) -> dict[str, Any]:
    generated = len(events)
    delivered = 0
    failed = 0
    duplicates = 0
    correlated = 0
    delivery_latencies: list[float] = []

    for e in events:
        if e.get("suppressed") or e.get("duplicate_of"):
            duplicates += 1
        if e.get("correlated") or e.get("correlation_label"):
            correlated += 1
        for h in e.get("notification_history") or []:
            if not isinstance(h, dict):
                continue
            st = h.get("status")
            if st in ("Sent", "Delivered"):
                delivered += 1
            elif st == "Failed":
                failed += 1

    dup_rate = round(duplicates / generated * 100, 1) if generated else 0.0
    return {
        "events_generated": generated,
        "alerts_delivered": delivered,
        "duplicate_rate": dup_rate,
        "correlated_events": correlated,
        "average_delivery_time_ms": None,  # filled when timed deliveries available
        "failed_deliveries": failed,
        "suppressed": duplicates,
    }
