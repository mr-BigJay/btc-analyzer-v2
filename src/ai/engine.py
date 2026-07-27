"""AI Decision Engine — cognitive layer (Ch.7) with Market Intelligence context (Ch.8).

Consumes Analysis Engine output + Market Intelligence Framework.
Never reads raw exchange data. Deterministic for identical inputs.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.ai.contracts import AIDecisionReport, RiskCategory
from src.ai.evidence import aggregate_evidence
from src.ai.explain import build_reasoning, calibrate_confidence
from src.ai.learning import record_forecast
from src.ai.narrative import detect_narrative
from src.ai.nlg import key_drivers_from_evidence
from src.ai.outlook import build_daily_outlook
from src.ai.probability import estimate_probabilities
from src.ai.risk import assess_risk
from src.ai.trading_plan import build_trading_plan
from src.analysis.contracts import MarketAnalysisOutput
from src.analysis.engine import AnalysisEngine
from src.cache.keys import CacheKeys
from src.config import settings
from src.intelligence.contracts import MarketIntelligenceOutput
from src.intelligence.engine import MarketIntelligenceEngine
from src.logging_setup import get_logger
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository

log = get_logger("ai.engine")


class AIDecisionEngine:
    """Cognitive pipeline Ch.7 §7.3 — enriched by Ch.8 strategic context."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.analysis_engine = AnalysisEngine(self.repository)
        self.intelligence_engine = MarketIntelligenceEngine(self.repository)

    def decide(
        self,
        analysis: MarketAnalysisOutput | dict[str, Any] | None = None,
        intelligence: MarketIntelligenceOutput | dict[str, Any] | None = None,
        *,
        symbol: str | None = None,
        timeframe: str = "1h",
        multi_timeframe: bool = True,
        near_options_expiry: bool = False,
        macro_event: bool = False,
        persist: bool = True,
        run_analysis_if_missing: bool = True,
    ) -> AIDecisionReport:
        symbol = symbol or settings.binance_symbol

        if analysis is None:
            if not run_analysis_if_missing:
                cached = redis_cache.get("latest_market_analysis")
                if isinstance(cached, dict):
                    analysis = cached
                else:
                    raise ValueError("No Analysis Engine output available for AI Decision Engine")
            else:
                analysis = self.analysis_engine.analyze(
                    symbol=symbol,
                    timeframe=timeframe,
                    multi_timeframe=multi_timeframe,
                    near_options_expiry=near_options_expiry,
                )

        analysis_dict = analysis.to_dict() if isinstance(analysis, MarketAnalysisOutput) else dict(analysis)

        if intelligence is None:
            intelligence = self.intelligence_engine.evaluate(
                analysis=analysis_dict,
                symbol=symbol,
                near_options_expiry=near_options_expiry,
                macro_event=macro_event,
                persist=persist,
                run_analysis_if_missing=False,
            )
        intel = intelligence.to_dict() if isinstance(intelligence, MarketIntelligenceOutput) else dict(intelligence)

        fingerprint = _fingerprint(analysis_dict, intel)

        # 1–2 Evidence aggregation + prioritization
        evidence = aggregate_evidence(analysis_dict)

        # 3 Narrative (single primary) — intelligence cycle/regime as context bullets
        narrative, narrative_bullets = detect_narrative(analysis_dict, evidence)
        narrative_bullets = _enrich_narrative_bullets(narrative_bullets, intel)

        # 4–5 Scenario reasoning + probability estimation (sum = 100)
        scenarios, distribution = estimate_probabilities(
            analysis_dict, evidence, primary_narrative=narrative
        )
        scenarios, distribution = _apply_intelligence_to_scenarios(scenarios, distribution, intel)

        # 6 Risk assessment — MSI overrides when stress is elevated (Ch.8 §8.13)
        risk_level, major_risks, risk_explanation = assess_risk(
            analysis_dict,
            evidence,
            near_options_expiry=near_options_expiry,
            macro_event=macro_event,
            intelligence=intel,
        )

        # 7 Confidence calibration + explainability (MHI informs quality)
        confidence, band, conf_explanation = calibrate_confidence(
            analysis_dict, evidence, scenarios, intelligence=intel
        )
        conflicts = list(analysis_dict.get("conflicts") or [])
        market_bias = str(analysis_dict.get("market_bias") or "Neutral")
        # Prefer Ch.8 regime classification over Ch.6 coarse regime
        market_regime = str(intel.get("market_regime") or analysis_dict.get("market_regime") or "Range")
        layer_results = list(analysis_dict.get("layer_results") or [])

        reasoning = build_reasoning(
            market_bias=market_bias,
            primary_narrative=narrative,
            confidence=confidence,
            confidence_explanation=conf_explanation,
            evidence=evidence,
            conflicts=conflicts,
            risk_explanation=risk_explanation,
            scenarios=scenarios,
        )
        reasoning.primary_conclusion = (
            f"{reasoning.primary_conclusion} "
            f"Strategic context: cycle={intel.get('market_cycle')}, "
            f"dominant={intel.get('dominant_participant')}, "
            f"MHI={intel.get('market_health_index')}, MSI={intel.get('market_stress_index')}."
        )

        key_drivers = key_drivers_from_evidence(evidence, narrative_bullets)
        if intel.get("derivatives_thesis"):
            key_drivers.insert(0, f"Derivatives: {intel['derivatives_thesis']}")

        # 8 Trading plan — MSI can force no_trade even if direction favorable
        plan = build_trading_plan(
            market_bias=market_bias,
            confidence=confidence,
            risk_level=risk_level,
            scenarios=scenarios,
            layer_results=layer_results,
            intelligence=intel,
        )

        # 9 Daily Outlook NLG
        outlook = build_daily_outlook(
            symbol=symbol,
            market_bias=market_bias,
            confidence=confidence,
            market_regime=market_regime,
            risk_level=risk_level,
            primary_narrative=narrative,
            key_drivers=key_drivers,
            major_risks=major_risks,
            scenarios=scenarios,
            trading_plan=plan,
            reasoning=reasoning,
            layer_results=layer_results,
        )

        primary_scenario = scenarios[0].name if scenarios else "Sideways Consolidation"
        report = AIDecisionReport(
            market_bias=market_bias,
            confidence=confidence,
            confidence_band=band,
            market_regime=market_regime,
            risk_level=risk_level,
            primary_narrative=narrative,
            primary_scenario=primary_scenario,
            alternative_scenarios=[s.to_dict() for s in scenarios[1:]],
            scenarios=[s.to_dict() for s in scenarios],
            key_drivers=key_drivers,
            major_risks=major_risks,
            trading_plan=plan.to_dict(),
            reasoning=reasoning.to_dict(),
            daily_outlook=outlook.to_dict(),
            evidence=[e.to_dict() for e in evidence],
            probability_distribution=distribution,
            market_intelligence=intel,
            symbol=symbol,
            analysis_fingerprint=fingerprint,
        )

        if persist:
            self._persist(report, analysis_dict)

        log.info(
            "ai decision bias={} conf={:.1f} narrative={} risk={} regime={} cycle={}",
            report.market_bias,
            report.confidence,
            report.primary_narrative,
            report.risk_level,
            market_regime,
            intel.get("market_cycle"),
        )
        return report

    def _persist(self, report: AIDecisionReport, analysis_input: dict[str, Any]) -> None:
        payload = report.to_dict()
        redis_cache.set(CacheKeys.LATEST_DAILY_OUTLOOK, payload.get("daily_outlook"), ttl_sec=86400)
        redis_cache.set(CacheKeys.ACTIVE_TRADING_PLAN, payload.get("trading_plan"), ttl_sec=86400)
        redis_cache.set("latest_ai_decision", payload, ttl_sec=86400)
        try:
            self.repository.save_daily_outlook(payload)
        except Exception as exc:  # noqa: BLE001
            log.warning("DB outlook persist failed: {}", exc)
        try:
            record_forecast(payload, analysis_input=analysis_input)
        except Exception as exc:  # noqa: BLE001
            log.warning("forecast record failed: {}", exc)


def _enrich_narrative_bullets(bullets: list[str], intel: dict[str, Any]) -> list[str]:
    extra = [
        f"Market cycle: {intel.get('market_cycle')}",
        f"Institutional activity: {intel.get('institutional_activity')}",
        f"Liquidity state: {intel.get('liquidity_state')}",
    ]
    if intel.get("transition_probability", 0) >= 40:
        extra.append(f"Transition probability {intel.get('transition_probability')}%")
    return list(dict.fromkeys(list(bullets) + extra))[:8]


def _apply_intelligence_to_scenarios(scenarios, distribution, intel: dict[str, Any]):
    """Light scenario reweight from cycle / transition (still sum 100)."""
    cycle = str(intel.get("market_cycle") or "")
    transition = float(intel.get("transition_probability") or 0)
    by_name = {s.name: s for s in scenarios}

    def bump(name: str, delta: float) -> None:
        if name in by_name:
            by_name[name].probability = max(5.0, by_name[name].probability + delta)

    if cycle == "Markup":
        bump("Bullish Continuation", 4)
        bump("Bearish Reversal", -2)
        bump("Sideways Consolidation", -2)
    elif cycle == "Markdown":
        bump("Bearish Reversal", 4)
        bump("Bullish Continuation", -2)
        bump("Sideways Consolidation", -2)
    elif cycle == "Distribution":
        bump("Bearish Reversal", 3)
        bump("Sideways Consolidation", 1)
        bump("Bullish Continuation", -4)
    elif cycle == "Accumulation":
        bump("Sideways Consolidation", 3)
        bump("Bullish Continuation", 1)
        bump("Bearish Reversal", -4)

    if transition >= 50:
        bump("Sideways Consolidation", 4)
        bump("Bullish Continuation", -2)
        bump("Bearish Reversal", -2)

    # Renormalize scenarios
    total = sum(s.probability for s in scenarios) or 1.0
    for s in scenarios:
        s.probability = s.probability / total * 100.0
    rounded = [round(s.probability, 1) for s in scenarios]
    drift = round(100.0 - sum(rounded), 1)
    rounded[0] = round(rounded[0] + drift, 1)
    for s, p in zip(scenarios, rounded):
        s.probability = p
    scenarios.sort(key=lambda s: s.probability, reverse=True)

    # Keep distribution keys; lightly tilt consolidation if transitioning
    if transition >= 50 and "consolidation" in distribution:
        distribution = dict(distribution)
        distribution["consolidation"] = float(distribution.get("consolidation") or 0) + 4
        keys = list(distribution.keys())
        vals = [max(0.0, float(distribution[k])) for k in keys]
        t = sum(vals) or 1.0
        vals = [v / t * 100 for v in vals]
        vals = [round(v, 1) for v in vals]
        vals[0] = round(vals[0] + (100.0 - sum(vals)), 1)
        distribution = dict(zip(keys, vals))

    _ = RiskCategory  # imported for risk mapping consumers
    return scenarios, distribution


def _fingerprint(analysis: dict[str, Any], intel: dict[str, Any]) -> str:
    stable = {
        "market_bias": analysis.get("market_bias"),
        "confidence": analysis.get("confidence"),
        "market_regime": analysis.get("market_regime"),
        "volatility": analysis.get("volatility"),
        "layer_results": analysis.get("layer_results"),
        "scenarios": analysis.get("scenarios"),
        "weights": analysis.get("weights"),
        "conflicts": analysis.get("conflicts"),
        "intelligence": {
            "market_regime": intel.get("market_regime"),
            "market_cycle": intel.get("market_cycle"),
            "market_health_index": intel.get("market_health_index"),
            "market_stress_index": intel.get("market_stress_index"),
            "transition_probability": intel.get("transition_probability"),
        },
    }
    raw = json.dumps(stable, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
