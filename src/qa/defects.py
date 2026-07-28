"""Defect classification and continuous quality metrics (Ch.22 §22.21 / §22.23)."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any

from src.qa.contracts import DEFECT_SEVERITIES, DefectSeverity, QUALITY_METRICS, utc_now_iso


class DefectRegistry:
    def __init__(self, maxlen: int = 500) -> None:
        self._lock = threading.Lock()
        self._items: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def report(
        self,
        *,
        title: str,
        severity: str = DefectSeverity.MEDIUM.value,
        area: str = "general",
        status: str = "open",
    ) -> dict[str, Any]:
        if severity not in DEFECT_SEVERITIES:
            severity = DefectSeverity.MEDIUM.value
        row = {
            "defect_id": f"DEF-{len(self._items)+1}",
            "title": title,
            "severity": severity,
            "description": DEFECT_SEVERITIES[severity],
            "area": area,
            "status": status,
            "timestamp": utc_now_iso(),
        }
        with self._lock:
            self._items.append(row)
        return row

    def list(self, *, limit: int = 50, open_only: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(reversed(self._items))
        if open_only:
            rows = [r for r in rows if r.get("status") == "open"]
        return rows[:limit]

    def critical_open(self) -> int:
        with self._lock:
            return sum(
                1
                for r in self._items
                if r.get("severity") == DefectSeverity.CRITICAL.value and r.get("status") == "open"
            )

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


defect_registry = DefectRegistry()


def quality_metrics_snapshot(*, test_success_rate: float = 1.0) -> dict[str, Any]:
    open_defects = defect_registry.list(open_only=True, limit=500)
    density = len(open_defects)
    return {
        "metrics": QUALITY_METRICS,
        "test_success_rate": test_success_rate,
        "defect_density": density,
        "mean_time_to_detect_hours": None,
        "mean_time_to_resolve_hours": None,
        "escaped_defects": 0,
        "regression_frequency": 0,
        "release_stability": "stable" if defect_registry.critical_open() == 0 else "at_risk",
        "open_defects": len(open_defects),
        "critical_open": defect_registry.critical_open(),
        "timestamp": utc_now_iso(),
    }
