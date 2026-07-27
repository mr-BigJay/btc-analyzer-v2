"""Daily Outlook report builder (Ch.7 §7.13)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.ai.contracts import (
    DailyOutlookReport,
    ReasoningBlock,
    ScenarioAssessment,
    TradingPlanSpec,
)
from src.ai.nlg import executive_summary, final_assessment, layer_blurb, liquidity_zone_lines


def build_daily_outlook(
    *,
    symbol: str,
    market_bias: str,
    confidence: float,
    market_regime: str,
    risk_level: str,
    primary_narrative: str,
    key_drivers: list[str],
    major_risks: list[str],
    scenarios: list[ScenarioAssessment],
    trading_plan: TradingPlanSpec,
    reasoning: ReasoningBlock,
    layer_results: list[dict[str, Any]],
) -> DailyOutlookReport:
    primary = scenarios[0] if scenarios else None
    alternatives = [s.to_dict() for s in scenarios[1:]]
    invalidations = []
    for s in scenarios:
        if s.invalidation is not None:
            invalidations.append(float(s.invalidation))

    return DailyOutlookReport(
        executive_summary=executive_summary(
            bias=market_bias,
            narrative=primary_narrative,
            confidence=confidence,
            risk_level=risk_level,
            primary=primary,
            reasoning=reasoning,
        ),
        market_bias=market_bias,
        confidence_score=confidence,
        market_regime=market_regime,
        key_drivers=key_drivers,
        options_analysis=layer_blurb(
            layer_results, "Options", fallback="Options layer unavailable."
        ),
        futures_analysis=layer_blurb(
            layer_results, "Futures", fallback="Futures layer unavailable."
        ),
        technical_summary=layer_blurb(
            layer_results, "Technical", fallback="Technical layer unavailable."
        ),
        liquidity_zones=liquidity_zone_lines(layer_results),
        major_risks=major_risks,
        primary_scenario=primary.to_dict() if primary else {},
        alternative_scenarios=alternatives,
        trading_plan=trading_plan.to_dict(),
        invalidation_levels=invalidations,
        final_assessment=final_assessment(
            bias=market_bias,
            narrative=primary_narrative,
            scenarios=scenarios,
            risk_level=risk_level,
            key_drivers=key_drivers,
        ),
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        symbol=symbol,
    )
