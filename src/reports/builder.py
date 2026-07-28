"""Build canonical reports from decision/AI objects (Ch.10 §10.5–§10.13).

Does not analyze or score — only formats validated intelligence.
"""

from __future__ import annotations

import re
from typing import Any

from src.reports.contracts import Audience, CanonicalReport, ReportMetadata, ReportType


SECTION_ORDER = (
    "executive_summary",
    "market_bias",
    "confidence",
    "market_regime",
    "market_narrative",
    "key_drivers",
    "spot_analysis",
    "futures_analysis",
    "options_analysis",
    "technical_analysis",
    "liquidity_analysis",
    "risk_assessment",
    "primary_scenario",
    "alternative_scenarios",
    "trading_plan",
    "invalidation_levels",
    "final_conclusion",
)


def build_report(
    *,
    report_type: str = ReportType.DAILY_OUTLOOK.value,
    ai_report: dict[str, Any] | None = None,
    decision_object: dict[str, Any] | None = None,
    intelligence: dict[str, Any] | None = None,
    audience: str = Audience.PROFESSIONAL.value,
    language: str = "en",
    timezone: str = "UTC",
) -> CanonicalReport:
    ai = dict(ai_report or {})
    decision = dict(decision_object or ai.get("scoring") or {})
    intel = dict(intelligence or ai.get("market_intelligence") or {})
    outlook = dict(ai.get("daily_outlook") or {})
    plan = dict(ai.get("trading_plan") or decision.get("trading_plan") or {})
    reasoning = dict(ai.get("reasoning") or {})
    scenarios = list(ai.get("scenarios") or [])
    primary = scenarios[0] if scenarios else dict(outlook.get("primary_scenario") or {})
    alternatives = scenarios[1:] if len(scenarios) > 1 else list(outlook.get("alternative_scenarios") or [])

    bias = str(decision.get("market_bias") or ai.get("market_bias") or "Neutral")
    confidence = float(decision.get("confidence_score") or ai.get("confidence") or 50)
    mbs = decision.get("market_bias_score")
    regime = str(intel.get("market_regime") or ai.get("market_regime") or "Range")
    narrative = str(ai.get("primary_narrative") or intel.get("market_cycle") or "")
    drivers = list(ai.get("key_drivers") or outlook.get("key_drivers") or [])[:6]
    risks = _risk_factors(ai, intel, decision)
    invalidations = list(outlook.get("invalidation_levels") or [])
    if primary.get("invalidation") is not None and primary["invalidation"] not in invalidations:
        invalidations.append(primary["invalidation"])

    executive = _executive_summary(
        bias=bias,
        confidence=confidence,
        regime=regime,
        narrative=narrative,
        primary=primary,
        drivers=drivers,
        source=outlook.get("executive_summary") or "",
    )
    final = str(
        outlook.get("final_assessment")
        or reasoning.get("primary_conclusion")
        or f"Final conclusion: {bias} bias under {regime} with confidence {confidence:.0f}."
    )

    sections = {
        "executive_summary": executive,
        "market_bias": {
            "bias": bias,
            "bias_score": mbs,
            "trend": narrative,
            "regime": regime,
            "confidence": confidence,
        },
        "confidence": {
            "score": confidence,
            "band": ai.get("confidence_band"),
            "explanation": reasoning.get("confidence_explanation"),
            "breakdown": _confidence_breakdown(decision, ai, intel),
        },
        "market_regime": {
            "regime": regime,
            "cycle": intel.get("market_cycle"),
            "volatility_regime": intel.get("volatility_regime"),
            "transition_probability": intel.get("transition_probability"),
        },
        "market_narrative": narrative,
        "key_drivers": drivers,
        "spot_analysis": _layer_section(ai, "Spot"),
        "futures_analysis": _layer_section(ai, "Futures"),
        "options_analysis": _layer_section(ai, "Options"),
        "technical_analysis": _layer_section(ai, "Technical"),
        "liquidity_analysis": _layer_section(ai, "Liquidity") or {
            "summary": intel.get("liquidity_state"),
            "state": intel.get("liquidity_state"),
        },
        "risk_assessment": {
            "risk_level": (ai.get("risk_object") or {}).get("risk_level")
            or ai.get("risk_level")
            or decision.get("risk_score"),
            "risk_score": decision.get("risk_score"),
            "composite_risk_score": (ai.get("risk_object") or {}).get("composite_risk_score"),
            "msi": intel.get("market_stress_index"),
            "factors": risks,
            "explanation": (ai.get("risk_object") or {}).get("explanation")
            or reasoning.get("risk_explanation"),
            "risk_object": ai.get("risk_object") or plan.get("risk_object") or {},
            "no_trade_zone": (ai.get("risk_object") or {}).get("no_trade_zone"),
            "suggested_exposure": (ai.get("risk_object") or {}).get("suggested_exposure"),
            "capital_preservation_mode": (ai.get("risk_object") or {}).get("capital_preservation_mode"),
        },
        "primary_scenario": primary,
        "alternative_scenarios": alternatives,
        "trading_plan": _trading_plan_format(plan),
        "invalidation_levels": invalidations,
        "final_conclusion": final,
        "explainability": {
            "primary_conclusion": reasoning.get("primary_conclusion"),
            "supporting_evidence": reasoning.get("supporting_evidence") or [],
            "conflicting_evidence": reasoning.get("conflicting_evidence") or [],
            "conflict_narrative": reasoning.get("conflict_narrative"),
            "uncertainty_note": reasoning.get("uncertainty_note"),
        },
    }

    meta = ReportMetadata(
        analysis_timestamp=str(ai.get("analyzed_at") or decision.get("scored_at") or ""),
        data_version=str(ai.get("analysis_fingerprint") or decision.get("analysis_fingerprint") or ""),
        symbol=str(ai.get("symbol") or decision.get("symbol") or "BTCUSDT"),
        language=language,
        timezone=timezone,
        audience=audience,
    )

    return CanonicalReport(
        report_type=report_type,
        market_bias=bias,
        confidence=confidence,
        market_bias_score=float(mbs) if mbs is not None else None,
        market_regime=regime,
        market_narrative=narrative,
        executive_summary=executive,
        key_drivers=drivers,
        risk_factors=risks,
        primary_scenario=primary if isinstance(primary, dict) else {},
        alternative_scenarios=alternatives,
        trading_plan=_trading_plan_format(plan),
        sections=sections,
        explainability=sections["explainability"],
        confidence_breakdown=sections["confidence"]["breakdown"],
        invalidation_levels=[float(x) for x in invalidations if x is not None],
        final_conclusion=final,
        disclaimer=str(ai.get("disclaimer") or CanonicalReport().disclaimer),
        metadata=meta.to_dict(),
        decision_object=decision,
        ai_report=ai,
        market_intelligence=intel,
    )


def build_specialized(
    report_type: str,
    *,
    ai_report: dict[str, Any],
    decision_object: dict[str, Any] | None = None,
    intelligence: dict[str, Any] | None = None,
    audience: str = Audience.PROFESSIONAL.value,
) -> CanonicalReport:
    base = build_report(
        report_type=report_type,
        ai_report=ai_report,
        decision_object=decision_object,
        intelligence=intelligence,
        audience=audience,
    )
    if report_type == ReportType.FUTURES.value:
        base.sections = {"futures_analysis": base.sections.get("futures_analysis"), "risk_assessment": base.sections.get("risk_assessment")}
        base.executive_summary = _clip(
            f"Futures positioning: {base.sections.get('futures_analysis', {}).get('summary', 'n/a')}. "
            f"Bias {base.market_bias}.",
            100,
        )
    elif report_type == ReportType.OPTIONS.value:
        base.sections = {"options_analysis": base.sections.get("options_analysis"), "risk_assessment": base.sections.get("risk_assessment")}
    elif report_type == ReportType.LIQUIDITY.value:
        base.sections = {"liquidity_analysis": base.sections.get("liquidity_analysis")}
    elif report_type == ReportType.RISK.value:
        base.sections = {"risk_assessment": base.sections.get("risk_assessment"), "confidence": base.sections.get("confidence")}
    elif report_type == ReportType.MARKET_SNAPSHOT.value:
        base.sections = {
            k: base.sections[k]
            for k in ("market_bias", "confidence", "market_regime", "key_drivers", "risk_assessment")
            if k in base.sections
        }
    elif report_type == ReportType.INTRADAY_PLAN.value:
        base.sections = {
            "trading_plan": base.sections.get("trading_plan"),
            "primary_scenario": base.sections.get("primary_scenario"),
            "invalidation_levels": base.sections.get("invalidation_levels"),
            "risk_assessment": base.sections.get("risk_assessment"),
        }
        base.executive_summary = _clip(
            f"Intraday plan: {base.trading_plan.get('direction', 'no_trade')} "
            f"under {base.market_bias} bias (confidence {base.confidence:.0f}).",
            100,
        )
    return base


def _executive_summary(*, bias, confidence, regime, narrative, primary, drivers, source: str) -> str:
    if source:
        return _clip(source, 100)
    primary_name = primary.get("name") if isinstance(primary, dict) else None
    primary_p = primary.get("probability") if isinstance(primary, dict) else None
    driver = drivers[0] if drivers else "mixed evidence"
    text = (
        f"Market is {bias} in a {regime} regime"
        + (f" under '{narrative}'" if narrative else "")
        + f". Confidence {confidence:.0f}%. "
        + (f"Primary scenario {primary_name} ({primary_p}%). " if primary_name else "")
        + f"Monitor: {driver}."
    )
    return _clip(text, 100)


def _clip(text: str, max_words: int) -> str:
    words = re.findall(r"\S+", text.strip())
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(",.;:") + "."


def _layer_section(ai: dict[str, Any], name: str) -> dict[str, Any]:
    for row in ai.get("evidence") or []:
        if row.get("layer") == name:
            return {
                "layer": name,
                "signal": row.get("signal"),
                "confidence": row.get("confidence"),
                "summary": row.get("evidence") or row.get("summary"),
                "priority": row.get("priority"),
            }
    scoring = ai.get("scoring") or {}
    layer_scores = scoring.get("layer_scores") or {}
    if name in layer_scores:
        return {"layer": name, "score": layer_scores[name], "summary": f"{name} score {layer_scores[name]}"}
    outlook = ai.get("daily_outlook") or {}
    key_map = {
        "Options": "options_analysis",
        "Futures": "futures_analysis",
        "Technical": "technical_summary",
    }
    if name in key_map and outlook.get(key_map[name]):
        return {"layer": name, "summary": outlook[key_map[name]]}
    return {}


def _trading_plan_format(plan: dict[str, Any]) -> dict[str, Any]:
    """Structured operational guidance (Ch.10 §10.10) — no guarantees."""
    if not plan:
        return {
            "direction": "no_trade",
            "preferred_entry_zone": [],
            "confirmation": [],
            "targets": [],
            "stop_area": None,
            "risk_level": None,
            "expected_holding_time": "n/a",
            "position_size_recommendation": "Flat",
            "advisory": True,
        }
    return {
        "direction": plan.get("preferred_direction") or plan.get("direction") or "no_trade",
        "preferred_entry_zone": plan.get("entry_zone") or [],
        "confirmation": plan.get("confirmation_conditions") or [],
        "targets": plan.get("target_levels") or plan.get("take_profits") or [],
        "stop_area": plan.get("stop_loss_zone") or plan.get("stop_loss"),
        "risk_level": plan.get("risk_reward"),
        "expected_holding_time": plan.get("expected_holding_time") or "intraday–few sessions",
        "position_size_recommendation": plan.get("position_sizing_guidance") or "Risk ≤1% equity",
        "session_notes": plan.get("session_notes"),
        "invalidation": plan.get("invalidation"),
        "confidence": plan.get("confidence"),
        "advisory": True,
    }


def _risk_factors(ai: dict[str, Any], intel: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    risks = list(ai.get("major_risks") or [])
    risk_obj = ai.get("risk_object") or {}
    if risk_obj.get("explanation"):
        risks.insert(0, str(risk_obj["explanation"]))
    for reason in risk_obj.get("no_trade_reasons") or []:
        risks.append(f"NTZ: {reason}")
    catalog = []
    if intel.get("macro_bias") in ("Cautious", "Risk-Off", "Uncertain"):
        catalog.append("Macro event / macro uncertainty")
    if "Funding" in str(intel.get("derivatives_thesis") or "") or "funding" in " ".join(risks).lower():
        catalog.append("Funding imbalance")
    if "Sweep" in str(intel.get("liquidity_state") or "") or "sweep" in " ".join(risks).lower():
        catalog.append("Liquidity sweep")
    if intel.get("volatility_regime") in ("Elevated", "Extreme"):
        catalog.append("Volatility expansion")
    if "Gamma" in str(intel.get("derivatives_thesis") or "") or "expiration" in " ".join(risks).lower():
        catalog.append("Options expiration")
    catalog.append("False breakout")
    # Prefer AI risks then fill from catalog
    out = list(dict.fromkeys(risks + catalog))
    return out[:8]


def _confidence_breakdown(decision: dict[str, Any], ai: dict[str, Any], intel: dict[str, Any]) -> list[dict[str, Any]]:
    """Decompose confidence factors (Ch.10 §10.13)."""
    meta = ((decision.get("details") or {}).get("confidence_meta") or {})
    factors: list[dict[str, Any]] = []
    agreement = meta.get("agreement_label") or "Mixed signals"
    impact_map = {
        "All layers aligned": 18,
        "Minor disagreement": 10,
        "Mixed signals": 0,
        "Significant conflict": -12,
    }
    factors.append({"factor": "Layer Agreement", "impact": impact_map.get(agreement, 0), "detail": agreement})
    if "Uptrend" in str(intel.get("market_regime") or "") or "Downtrend" in str(intel.get("market_regime") or ""):
        factors.append({"factor": "Strong Structure", "impact": 14, "detail": intel.get("market_regime")})
    opt = next((e for e in ai.get("evidence") or [] if e.get("layer") == "Options"), None)
    if opt and ("Bullish" in str(opt.get("signal")) or "Bearish" in str(opt.get("signal"))):
        factors.append({"factor": "Options Confirmation", "impact": 10, "detail": opt.get("signal")})
    for p in decision.get("conflict_penalties") or []:
        factors.append({"factor": str(p.get("pair") or "Conflict"), "impact": float(p.get("penalty") or 0), "detail": "conflict penalty"})
    if intel.get("volatility_regime") in ("Elevated", "Extreme"):
        factors.append({"factor": "High Volatility", "impact": -4, "detail": intel.get("volatility_regime")})
    mtf = meta.get("mtf_delta")
    if mtf:
        factors.append({"factor": "Timeframe Consensus", "impact": float(mtf), "detail": meta.get("mtf_alignment")})
    return factors
