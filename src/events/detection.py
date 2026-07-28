"""Deterministic event detection rules (Ch.16 §16.7). Version-controlled."""

from __future__ import annotations

from typing import Any

from src.events.contracts import (
    RULES_VERSION,
    EventCategory,
    EventObject,
    EventSeverity,
    EventState,
    utc_now_iso,
)

CONFIDENCE_DELTA_THRESHOLD = 10.0


def _fingerprint(category: str, event_type: str, asset: str, key: str = "") -> str:
    return f"{category}|{event_type}|{asset.upper()}|{key}".lower()


def detect_events(
    *,
    current: dict[str, Any],
    previous: dict[str, Any] | None = None,
    asset: str = "BTCUSDT",
    system: dict[str, Any] | None = None,
) -> list[EventObject]:
    """Detect events from decision/AI/intel/risk snapshots. No event skips validation later."""
    prev = previous or {}
    events: list[EventObject] = []
    asset = (asset or "BTCUSDT").upper()
    now = utc_now_iso()

    intel = current.get("market_intelligence") or {}
    prev_intel = prev.get("market_intelligence") or {}
    scoring = current.get("scoring") or current.get("decision") or {}
    risk = current.get("risk_object") or {}
    tags: set[str] = set()
    for row in current.get("evidence") or (current.get("ai_report") or {}).get("evidence") or []:
        if isinstance(row, dict):
            tags.update(row.get("tags") or [])

    # --- Trend / regime ---
    cur_regime = str(current.get("market_regime") or intel.get("market_regime") or "")
    prev_regime = str(prev.get("market_regime") or prev_intel.get("market_regime") or "")
    if cur_regime and prev_regime and cur_regime != prev_regime:
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.TREND.value,
                type="Market Regime Change",
                severity=EventSeverity.HIGH.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=f"Market transitioned from {prev_regime} to {cur_regime}.",
                explanation=f"Regime changed {prev_regime} → {cur_regime}",
                trigger_conditions={"from": prev_regime, "to": cur_regime},
                related_metrics={"market_regime": cur_regime},
                fingerprint=_fingerprint(EventCategory.TREND.value, "Market Regime Change", asset, f"{prev_regime}->{cur_regime}"),
                rules_version=RULES_VERSION,
            )
        )

    # --- Bias change ---
    cur_bias = str(current.get("market_bias") or scoring.get("market_bias") or "")
    prev_bias = str(prev.get("market_bias") or "")
    if cur_bias and prev_bias and cur_bias != prev_bias:
        severity = EventSeverity.HIGH.value if {"Bullish", "Bearish"} & {cur_bias.split()[-1], prev_bias.split()[-1]} else EventSeverity.MEDIUM.value
        # Stronger if bullish↔bearish flip
        if ("Bull" in cur_bias and "Bear" in prev_bias) or ("Bear" in cur_bias and "Bull" in prev_bias):
            severity = EventSeverity.HIGH.value
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.TREND.value,
                type="Market Bias Change",
                severity=severity,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=f"Market bias changed from {prev_bias} to {cur_bias}.",
                trigger_conditions={"from": prev_bias, "to": cur_bias},
                related_metrics={"market_bias": cur_bias, "confidence": current.get("confidence")},
                fingerprint=_fingerprint(EventCategory.TREND.value, "Market Bias Change", asset, f"{prev_bias}->{cur_bias}"),
            )
        )

    # --- Confidence delta ---
    cur_conf = float(current.get("confidence") or scoring.get("confidence_score") or 0)
    prev_conf = float(prev.get("confidence") or 0)
    if prev and abs(cur_conf - prev_conf) >= CONFIDENCE_DELTA_THRESHOLD:
        up = cur_conf > prev_conf
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.TREND.value,
                type="Confidence Increased" if up else "Confidence Dropped",
                severity=EventSeverity.INFORMATIONAL.value if up else EventSeverity.MEDIUM.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=f"Confidence {'rose' if up else 'fell'} {prev_conf:.0f} → {cur_conf:.0f}.",
                trigger_conditions={"threshold": CONFIDENCE_DELTA_THRESHOLD, "delta": cur_conf - prev_conf},
                related_metrics={"confidence": cur_conf},
                fingerprint=_fingerprint(EventCategory.TREND.value, "Confidence", asset, "up" if up else "down"),
            )
        )

    # --- Price / breakout ---
    if "Breakout Probability" in tags or "BOS" in tags:
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.PRICE.value,
                type="Breakout Confirmed",
                severity=EventSeverity.MEDIUM.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary="Breakout / BOS evidence present in analysis layers.",
                trigger_conditions={"tags": sorted(t for t in tags if t in {"Breakout Probability", "BOS"})},
                fingerprint=_fingerprint(EventCategory.PRICE.value, "Breakout Confirmed", asset),
            )
        )
    if "Breakdown" in tags or "ChoCH Bearish" in tags:
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.PRICE.value,
                type="Breakdown Confirmed",
                severity=EventSeverity.MEDIUM.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary="Breakdown evidence present in analysis layers.",
                fingerprint=_fingerprint(EventCategory.PRICE.value, "Breakdown Confirmed", asset),
            )
        )

    # --- Liquidity ---
    liq = str(intel.get("liquidity_state") or "")
    if "Sweep" in liq or "Sweep Probability" in tags or liq == "Liquidity Vacuum":
        sev = EventSeverity.CRITICAL.value if liq == "Liquidity Vacuum" else EventSeverity.HIGH.value
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.LIQUIDITY.value,
                type="Liquidity Sweep Detected" if "Sweep" in liq or "Sweep Probability" in tags else "Liquidity Vacuum",
                severity=sev,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=f"Liquidity condition: {liq or 'sweep risk'}.",
                related_metrics={"liquidity_state": liq},
                fingerprint=_fingerprint(EventCategory.LIQUIDITY.value, "Liquidity", asset, liq or "sweep"),
            )
        )

    # --- Futures ---
    thesis = str(intel.get("derivatives_thesis") or "")
    if "Funding" in thesis or "funding" in thesis.lower():
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.FUTURES.value,
                type="Funding Extreme",
                severity=EventSeverity.HIGH.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=thesis[:180] or "Funding-related derivatives stress.",
                related_metrics={"derivatives_thesis": thesis[:200]},
                fingerprint=_fingerprint(EventCategory.FUTURES.value, "Funding Extreme", asset),
            )
        )
    if "Open Interest" in thesis or "OI" in thesis:
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.FUTURES.value,
                type="Open Interest Spike",
                severity=EventSeverity.MEDIUM.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=thesis[:180] or "Abnormal open interest activity.",
                fingerprint=_fingerprint(EventCategory.FUTURES.value, "Open Interest Spike", asset),
            )
        )
    if "Liquidation" in thesis or "Squeeze" in thesis:
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.FUTURES.value,
                type="High Liquidation Event",
                severity=EventSeverity.CRITICAL.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=thesis[:180] or "Elevated liquidation / squeeze risk.",
                fingerprint=_fingerprint(EventCategory.FUTURES.value, "High Liquidation Event", asset),
            )
        )

    # --- Options ---
    if "Gamma" in thesis or "expiration" in thesis.lower():
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.OPTIONS.value,
                type="Gamma Shift",
                severity=EventSeverity.MEDIUM.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=thesis[:180] or "Options gamma / expiry window active.",
                fingerprint=_fingerprint(EventCategory.OPTIONS.value, "Gamma Shift", asset),
            )
        )

    # --- Volatility regime change ---
    cur_vol = str(intel.get("volatility_regime") or current.get("volatility") or "")
    prev_vol = str(prev_intel.get("volatility_regime") or prev.get("volatility") or "")
    if cur_vol and prev_vol and cur_vol != prev_vol:
        sev = EventSeverity.HIGH.value if cur_vol in ("Elevated", "Extreme", "Expansion") else EventSeverity.LOW.value
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.TREND.value,
                type="Volatility Regime Change",
                severity=sev,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=f"Volatility regime changed {prev_vol} → {cur_vol}.",
                trigger_conditions={"from": prev_vol, "to": cur_vol},
                fingerprint=_fingerprint(EventCategory.TREND.value, "Volatility Regime Change", asset, f"{prev_vol}->{cur_vol}"),
            )
        )

    # --- Risk / MSI / DQS / NTZ ---
    msi = str(intel.get("market_stress_index") or "")
    if msi in ("High", "Extreme"):
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.RISK.value,
                type="Market Stress Extreme",
                severity=EventSeverity.CRITICAL.value if msi == "Extreme" else EventSeverity.HIGH.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=f"Market Stress Index entered {msi}.",
                related_metrics={"market_stress_index": msi},
                fingerprint=_fingerprint(EventCategory.RISK.value, "Market Stress Extreme", asset, msi),
            )
        )

    dqs = scoring.get("data_quality_score")
    if dqs is not None and float(dqs) < 60:
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.RISK.value,
                type="Data Quality Degraded",
                severity=EventSeverity.HIGH.value if float(dqs) < 50 else EventSeverity.MEDIUM.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=f"Data Quality Score degraded to {float(dqs):.0f}.",
                related_metrics={"data_quality_score": float(dqs)},
                fingerprint=_fingerprint(EventCategory.RISK.value, "Data Quality Degraded", asset),
            )
        )

    if risk.get("no_trade_zone"):
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.RISK.value,
                type="No Trade Zone",
                severity=EventSeverity.CRITICAL.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary="No Trade Zone active — new exposure suppressed.",
                explanation="; ".join(risk.get("no_trade_reasons") or []) or risk.get("explanation") or "",
                related_metrics={
                    "composite_risk_score": risk.get("composite_risk_score"),
                    "risk_level": risk.get("risk_level"),
                },
                trigger_conditions={"reasons": risk.get("no_trade_reasons") or []},
                fingerprint=_fingerprint(EventCategory.RISK.value, "No Trade Zone", asset),
            )
        )
    elif risk.get("risk_level") in ("High", "Extreme") or float(risk.get("composite_risk_score") or 0) >= 61:
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.RISK.value,
                type="Elevated Execution Risk",
                severity=EventSeverity.HIGH.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=f"Execution risk elevated (CRS={risk.get('composite_risk_score')}, {risk.get('risk_level')}).",
                related_metrics={"composite_risk_score": risk.get("composite_risk_score")},
                fingerprint=_fingerprint(EventCategory.RISK.value, "Elevated Execution Risk", asset, str(risk.get("risk_level"))),
            )
        )

    # --- Macro ---
    if current.get("macro_event") or intel.get("macro_event"):
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.MACRO.value,
                type="High-Impact Economic Release",
                severity=EventSeverity.HIGH.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary="High-impact macro event window active.",
                fingerprint=_fingerprint(EventCategory.MACRO.value, "High-Impact Economic Release", asset),
            )
        )

    # --- System ---
    sys = system or current.get("system") or {}
    if sys.get("collector_failure") or sys.get("exchange_degraded"):
        events.append(
            EventObject(
                asset=asset,
                category=EventCategory.SYSTEM.value,
                type="Collector Failure" if sys.get("collector_failure") else "Exchange Connectivity Degraded",
                severity=EventSeverity.CRITICAL.value,
                state=EventState.DETECTED.value,
                timestamp=now,
                summary=str(sys.get("message") or "System degradation detected."),
                trigger_conditions=dict(sys),
                fingerprint=_fingerprint(EventCategory.SYSTEM.value, "System", asset, str(sys.get("collector_failure") or "degraded")),
            )
        )

    return events
