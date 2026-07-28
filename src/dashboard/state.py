"""Operational dashboard state detection (Ch.17 §17.20)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.dashboard.contracts import DashboardState


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def resolve_dashboard_state(
    *,
    has_payload: bool,
    analyzed_at: Any = None,
    connection_ok: bool = True,
    partial_services: bool = False,
    maintenance: bool = False,
    stale_after_sec: float = 900.0,
) -> str:
    if maintenance:
        return DashboardState.MAINTENANCE.value
    if not connection_ok and not has_payload:
        return DashboardState.OFFLINE.value
    if not has_payload:
        return DashboardState.LOADING.value
    if partial_services:
        return DashboardState.DEGRADED.value
    ts = _parse_ts(analyzed_at)
    if ts is not None:
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > stale_after_sec:
            return DashboardState.STALE.value
    if not connection_ok:
        return DashboardState.DEGRADED.value
    return DashboardState.LIVE.value
