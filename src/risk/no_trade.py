"""No Trade Zone detection (Ch.15 §15.7)."""

from __future__ import annotations

from typing import Any

from src.config import settings


def evaluate_no_trade_zone(
    *,
    decision: dict[str, Any],
    intelligence: dict[str, Any],
    analysis: dict[str, Any],
    crs: float,
    data_risk_score: float,
    event_risk_label: str,
    liquidity_label: str,
    macro_event: bool = False,
    exchange_degraded: bool = False,
    unresolved_validation: bool = False,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    min_dqs = float(getattr(settings, "scoring_min_dqs", 60.0))
    dqs = float(decision.get("data_quality_score") or 100)
    if dqs < min_dqs:
        reasons.append(f"Data Quality Score {dqs:.0f} below minimum {min_dqs:.0f}")
    if data_risk_score >= 55:
        reasons.append("Elevated data integrity risk")

    msi = str(intelligence.get("market_stress_index") or "")
    if msi in ("High", "Extreme"):
        reasons.append(f"Extreme/high Market Stress Index ({msi})")

    conflicts = list(analysis.get("conflicts") or decision.get("conflict_penalties") or [])
    if len(conflicts) >= 2 or (decision.get("timeframe_alignment") == "Complete Divergence"):
        reasons.append("Conflicting analytical layers / complete divergence")

    if macro_event or event_risk_label == "High" or intelligence.get("macro_event"):
        reasons.append("Major macro event imminent or active risk window")

    if exchange_degraded or intelligence.get("exchange_degraded"):
        reasons.append("Exchange connectivity degradation")

    if unresolved_validation or decision.get("validation_errors"):
        reasons.append("Unresolved validation errors")

    if crs >= 81:
        reasons.append(f"Composite Risk Score extreme ({crs:.0f})")

    if not decision.get("publish", True):
        reasons.append("Scoring publication gate closed")

    if str(analysis.get("market_bias")) == "High Uncertainty":
        reasons.append("Analysis Engine High Uncertainty")

    if liquidity_label == "Critical":
        reasons.append("Critical liquidity conditions")

    return bool(reasons), reasons
