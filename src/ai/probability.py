"""Scenario reasoning + probability estimation (Ch.7 §7.7–§7.8)."""

from __future__ import annotations

from typing import Any

from src.ai.contracts import EvidenceItem, RiskCategory, ScenarioAssessment
from src.analysis.contracts import MarketAnalysisOutput, SignalBias


def estimate_probabilities(
    analysis: MarketAnalysisOutput | dict[str, Any],
    evidence: list[EvidenceItem],
    *,
    primary_narrative: str,
) -> tuple[list[ScenarioAssessment], dict[str, float]]:
    """Evidence-derived probabilities that always sum to 100% (Ch.7 §7.8)."""
    if isinstance(analysis, MarketAnalysisOutput):
        bias = analysis.market_bias
        confidence = float(analysis.confidence)
        base_scenarios = list(analysis.scenarios or [])
        conflicts = list(analysis.conflicts or [])
        risk = analysis.risk_level
    else:
        bias = str(analysis.get("market_bias") or SignalBias.NEUTRAL.value)
        confidence = float(analysis.get("confidence") or 50)
        base_scenarios = list(analysis.get("scenarios") or [])
        conflicts = list(analysis.get("conflicts") or [])
        risk = str(analysis.get("risk_level") or "Moderate")

    named = {str(s.get("name")): dict(s) for s in base_scenarios if isinstance(s, dict)}

    bull_p = float(named.get("Bullish Continuation", {}).get("probability") or 0)
    side_p = float(named.get("Sideways Consolidation", {}).get("probability") or 0)
    bear_p = float(named.get("Bearish Reversal", {}).get("probability") or 0)

    if bull_p + side_p + bear_p < 1:
        bull_p, side_p, bear_p = _seed_from_bias(bias, confidence)

    if primary_narrative == "Bullish Trend Expansion":
        bull_p += 8
        bear_p -= 4
        side_p -= 4
    elif primary_narrative == "Short Squeeze":
        bull_p += 10
        side_p -= 5
        bear_p -= 5
    elif primary_narrative in ("Distribution", "Long Squeeze Risk"):
        bear_p += 10
        bull_p -= 5
        side_p -= 5
    elif primary_narrative == "Range / Indecision":
        side_p += 12
        bull_p -= 6
        bear_p -= 6
    elif primary_narrative == "Volatility Expansion Setup":
        side_p -= 6
        bull_p += 3
        bear_p += 3
    elif primary_narrative == "Liquidity Sweep Setup":
        side_p += 4
        bull_p -= 2
        bear_p -= 2

    if conflicts:
        side_p += 6
        bull_p -= 3
        bear_p -= 3

    vol_p = 0.0
    liq_p = 0.0
    if primary_narrative == "Volatility Expansion Setup":
        vol_p = 12.0
        bull_p -= 4
        bear_p -= 4
        side_p -= 4
    if primary_narrative == "Liquidity Sweep Setup":
        liq_p = 10.0
        side_p -= 6
        bull_p -= 2
        bear_p -= 2

    dist = _normalize(
        {
            "trend_continuation": max(0.0, bull_p),
            "trend_reversal": max(0.0, bear_p),
            "consolidation": max(0.0, side_p),
            "volatility_expansion": max(0.0, vol_p),
            "liquidity_sweep": max(0.0, liq_p),
        }
    )

    cont_p = dist["trend_continuation"] + 0.35 * dist["volatility_expansion"] + 0.25 * dist["liquidity_sweep"]
    rev_p = dist["trend_reversal"] + 0.35 * dist["volatility_expansion"] + 0.25 * dist["liquidity_sweep"]
    cons_p = dist["consolidation"] + 0.30 * dist["volatility_expansion"] + 0.50 * dist["liquidity_sweep"]
    named_probs = _normalize(
        {
            "Bullish Continuation": cont_p,
            "Sideways Consolidation": cons_p,
            "Bearish Reversal": rev_p,
        }
    )

    supporting = [e.evidence for e in evidence if "Bullish" in e.signal][:4]
    invalidating = [e.evidence for e in evidence if "Bearish" in e.signal][:4]
    if bias in (SignalBias.BEARISH.value, SignalBias.SLIGHTLY_BEARISH.value):
        supporting, invalidating = invalidating, supporting

    risk_label = _scenario_risk(risk, conflicts)

    scenarios = [
        ScenarioAssessment(
            name="Bullish Continuation",
            probability=named_probs["Bullish Continuation"],
            trigger=str(named.get("Bullish Continuation", {}).get("trigger") or "Hold structure + buyer defense"),
            supporting_evidence=supporting or [e.evidence for e in evidence[:2]],
            invalidating_evidence=invalidating[:2],
            risk_level=risk_label,
            time_horizon="1–5 sessions",
            target_zones=list(named.get("Bullish Continuation", {}).get("target_zones") or []),
            invalidation=named.get("Bullish Continuation", {}).get("invalidation"),
            confidence=min(100.0, confidence + 5) if "Bullish" in bias else confidence * 0.75,
        ),
        ScenarioAssessment(
            name="Sideways Consolidation",
            probability=named_probs["Sideways Consolidation"],
            trigger=str(named.get("Sideways Consolidation", {}).get("trigger") or "Range between liquidity magnets"),
            supporting_evidence=[e.evidence for e in evidence if e.signal == SignalBias.NEUTRAL.value][:3]
            or ["Mixed cross-layer evidence"],
            invalidating_evidence=["Decisive breakout with volume expansion"],
            risk_level=RiskCategory.MODERATE.value,
            time_horizon="intraday–several sessions",
            target_zones=list(named.get("Sideways Consolidation", {}).get("target_zones") or []),
            confidence=max(40.0, 80 - abs(50 - confidence) * 0.3),
        ),
        ScenarioAssessment(
            name="Bearish Reversal",
            probability=named_probs["Bearish Reversal"],
            trigger=str(named.get("Bearish Reversal", {}).get("trigger") or "Break of support with seller absorption"),
            supporting_evidence=invalidating or [e.evidence for e in evidence if "Bearish" in e.signal][:3],
            invalidating_evidence=supporting[:2],
            risk_level=risk_label,
            time_horizon="1–5 sessions",
            target_zones=list(named.get("Bearish Reversal", {}).get("target_zones") or []),
            invalidation=named.get("Bearish Reversal", {}).get("invalidation"),
            confidence=min(100.0, confidence + 5) if "Bearish" in bias else confidence * 0.75,
        ),
    ]
    scenarios.sort(key=lambda s: s.probability, reverse=True)
    scenarios = _fix_probability_sum(scenarios)
    distribution = _fix_dict_sum({k: round(v, 1) for k, v in dist.items()})
    return scenarios, distribution


def _seed_from_bias(bias: str, confidence: float) -> tuple[float, float, float]:
    if bias in (SignalBias.BULLISH.value, SignalBias.SLIGHTLY_BULLISH.value):
        bull = 45 + confidence / 4
        side = 30
        return bull, side, 100 - bull - side
    if bias in (SignalBias.BEARISH.value, SignalBias.SLIGHTLY_BEARISH.value):
        bear = 45 + confidence / 4
        side = 30
        return 100 - bear - side, side, bear
    if bias == SignalBias.HIGH_UNCERTAINTY.value:
        return 30.0, 40.0, 30.0
    return 28.0, 44.0, 28.0


def _normalize(raw: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, v) for v in raw.values()) or 1.0
    return {k: (max(0.0, v) / total) * 100.0 for k, v in raw.items()}


def _fix_probability_sum(scenarios: list[ScenarioAssessment]) -> list[ScenarioAssessment]:
    rounded = [round(s.probability, 1) for s in scenarios]
    drift = round(100.0 - sum(rounded), 1)
    rounded[0] = round(rounded[0] + drift, 1)
    for s, p in zip(scenarios, rounded):
        s.probability = p
    return scenarios


def _fix_dict_sum(d: dict[str, float]) -> dict[str, float]:
    keys = list(d.keys())
    vals = [round(d[k], 1) for k in keys]
    drift = round(100.0 - sum(vals), 1)
    if keys:
        vals[0] = round(vals[0] + drift, 1)
    return dict(zip(keys, vals))


def _scenario_risk(analysis_risk: str, conflicts: list[str]) -> str:
    if conflicts or analysis_risk in ("High", "High Risk"):
        return RiskCategory.ELEVATED.value
    if analysis_risk in ("Low", "Low Risk"):
        return RiskCategory.LOW.value
    return RiskCategory.MODERATE.value
