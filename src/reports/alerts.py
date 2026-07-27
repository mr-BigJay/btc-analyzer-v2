"""Event-driven alert generation (Ch.10 §10.15)."""

from __future__ import annotations

from typing import Any

from src.reports.contracts import AlertEvent, AlertSeverity
from src.storage.redis_cache import redis_cache

PREV_STATE_KEY = "report_alert_previous_state"


def detect_alerts(
    *,
    current: dict[str, Any],
    previous: dict[str, Any] | None = None,
    symbol: str = "BTCUSDT",
) -> list[AlertEvent]:
    prev = previous if previous is not None else (redis_cache.get(PREV_STATE_KEY) or {})
    if not isinstance(prev, dict):
        prev = {}

    alerts: list[AlertEvent] = []
    cur_regime = str(current.get("market_regime") or "")
    prev_regime = str(prev.get("market_regime") or "")
    if cur_regime and prev_regime and cur_regime != prev_regime:
        alerts.append(
            AlertEvent(
                alert_type="Market Regime Changed",
                severity=AlertSeverity.WARNING.value,
                message=f"Regime changed {prev_regime} → {cur_regime}",
                symbol=symbol,
                details={"from": prev_regime, "to": cur_regime},
            )
        )

    cur_conf = float(current.get("confidence") or 0)
    prev_conf = float(prev.get("confidence") or 0)
    if prev and cur_conf - prev_conf >= 10:
        alerts.append(
            AlertEvent(
                alert_type="Confidence Increased",
                severity=AlertSeverity.INFO.value,
                message=f"Confidence rose {prev_conf:.0f} → {cur_conf:.0f}",
                symbol=symbol,
            )
        )
    if prev and prev_conf - cur_conf >= 10:
        alerts.append(
            AlertEvent(
                alert_type="Confidence Dropped",
                severity=AlertSeverity.WATCH.value,
                message=f"Confidence fell {prev_conf:.0f} → {cur_conf:.0f}",
                symbol=symbol,
            )
        )

    intel = current.get("market_intelligence") or {}
    prev_intel = prev.get("market_intelligence") or {}
    tags = set()
    for row in (current.get("ai_report") or {}).get("evidence") or []:
        tags.update(row.get("tags") or [])

    if "Breakout Probability" in tags or "BOS" in tags:
        alerts.append(
            AlertEvent(
                alert_type="Breakout Confirmed",
                severity=AlertSeverity.WATCH.value,
                message="Breakout / BOS evidence present in analysis layers",
                symbol=symbol,
            )
        )
    if "Sweep" in str(intel.get("liquidity_state") or "") or "Sweep Probability" in tags:
        alerts.append(
            AlertEvent(
                alert_type="Liquidity Sweep Detected",
                severity=AlertSeverity.WARNING.value,
                message=f"Liquidity state: {intel.get('liquidity_state')}",
                symbol=symbol,
            )
        )
    thesis = str(intel.get("derivatives_thesis") or "")
    if "Gamma" in thesis or "expiration" in thesis.lower():
        alerts.append(
            AlertEvent(
                alert_type="Options Expiration Risk",
                severity=AlertSeverity.WATCH.value,
                message=thesis[:180],
                symbol=symbol,
            )
        )
    if "Funding" in thesis or "funding" in thesis.lower() or "Extreme" in thesis:
        alerts.append(
            AlertEvent(
                alert_type="Funding Extreme",
                severity=AlertSeverity.WARNING.value,
                message=thesis[:180] or "Funding-related derivatives stress",
                symbol=symbol,
            )
        )
    if "Liquidation" in thesis or "Squeeze" in thesis:
        alerts.append(
            AlertEvent(
                alert_type="High Liquidation Event",
                severity=AlertSeverity.CRITICAL.value,
                message=thesis[:180],
                symbol=symbol,
            )
        )

    # Persist current as previous for next cycle
    redis_cache.set(
        PREV_STATE_KEY,
        {
            "market_regime": cur_regime,
            "confidence": cur_conf,
            "market_intelligence": {
                "liquidity_state": intel.get("liquidity_state"),
                "derivatives_thesis": intel.get("derivatives_thesis"),
            },
            "market_bias": current.get("market_bias"),
        },
        ttl_sec=86400,
    )
    _ = prev_intel
    return alerts
