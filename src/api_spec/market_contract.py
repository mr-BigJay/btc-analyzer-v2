"""Canonical market intelligence response builder (Ch.18 §18.25)."""

from __future__ import annotations

from typing import Any

from src.api_spec.contracts import MarketIntelligenceResponse, utc_now_iso
from src.cache.keys import CacheKeys
from src.storage.redis_cache import redis_cache


def build_market_intelligence_response(
    *,
    symbol: str = "BTCUSDT",
    ai_report: dict[str, Any] | None = None,
    intelligence: dict[str, Any] | None = None,
    scoring: dict[str, Any] | None = None,
    risk: dict[str, Any] | None = None,
) -> MarketIntelligenceResponse:
    ai = dict(ai_report or redis_cache.get("latest_ai_decision") or {})
    intel = dict(intelligence or ai.get("market_intelligence") or redis_cache.get(CacheKeys.LATEST_MARKET_INTELLIGENCE) or {})
    score = dict(scoring or ai.get("scoring") or redis_cache.get(CacheKeys.LATEST_DECISION_OBJECT) or {})
    risk_obj = dict(risk or ai.get("risk_object") or redis_cache.get(CacheKeys.LATEST_RISK_OBJECT) or {})

    mhi = intel.get("market_health_index")
    msi = intel.get("market_stress_index")
    # Normalize indexes to numeric when possible for external contract
    if isinstance(mhi, str):
        mhi_map = {"Healthy": 81, "Stable": 70, "Fragile": 45, "Stressed": 30}
        mhi = mhi_map.get(mhi, mhi)
    if isinstance(msi, str):
        msi_map = {"Low": 24, "Moderate": 45, "Elevated": 60, "High": 75, "Extreme": 90}
        msi_num = msi_map.get(msi, msi)
    else:
        msi_num = msi

    risk_score = risk_obj.get("composite_risk_score")
    if risk_score is None:
        risk_score = score.get("risk_score") or 40

    scenarios = ai.get("scenarios") or []
    primary = ai.get("primary_scenario") or (scenarios[0].get("name") if scenarios and isinstance(scenarios[0], dict) else "")

    return MarketIntelligenceResponse(
        asset=symbol.upper(),
        market_bias=str(score.get("market_bias") or ai.get("market_bias") or "Neutral"),
        market_regime=str(intel.get("market_regime") or ai.get("market_regime") or "Range"),
        confidence_score=float(score.get("confidence_score") or ai.get("confidence") or 50),
        risk_score=float(risk_score),
        market_health_index=mhi if mhi is not None else 50,
        market_stress_index=msi_num if msi_num is not None else 40,
        primary_scenario=str(primary or ""),
        last_updated=str(ai.get("analyzed_at") or score.get("scored_at") or utc_now_iso()),
    )
