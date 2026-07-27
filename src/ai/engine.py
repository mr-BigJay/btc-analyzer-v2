"""AI Decision Engine — cognitive layer (Ch.7).

Consumes Analysis Engine output only. Never reads raw exchange data.
Deterministic: identical analysis inputs → identical reports.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.ai.contracts import AIDecisionReport
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
from src.logging_setup import get_logger
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository

log = get_logger("ai.engine")


class AIDecisionEngine:
    """Cognitive pipeline Ch.7 §7.3."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.analysis_engine = AnalysisEngine(self.repository)

    def decide(
        self,
        analysis: MarketAnalysisOutput | dict[str, Any] | None = None,
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
        fingerprint = _fingerprint(analysis_dict)

        # 1–2 Evidence aggregation + prioritization
        evidence = aggregate_evidence(analysis_dict)

        # 3 Narrative (single primary)
        narrative, narrative_bullets = detect_narrative(analysis_dict, evidence)

        # 4–5 Scenario reasoning + probability estimation (sum = 100)
        scenarios, distribution = estimate_probabilities(
            analysis_dict, evidence, primary_narrative=narrative
        )

        # 6 Risk assessment (independent of direction)
        risk_level, major_risks, risk_explanation = assess_risk(
            analysis_dict,
            evidence,
            near_options_expiry=near_options_expiry,
            macro_event=macro_event,
        )

        # 7 Confidence calibration + explainability
        confidence, band, conf_explanation = calibrate_confidence(analysis_dict, evidence, scenarios)
        conflicts = list(analysis_dict.get("conflicts") or [])
        market_bias = str(analysis_dict.get("market_bias") or "Neutral")
        market_regime = str(analysis_dict.get("market_regime") or "Range")
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

        key_drivers = key_drivers_from_evidence(evidence, narrative_bullets)

        # 8 Trading plan (advisory)
        plan = build_trading_plan(
            market_bias=market_bias,
            confidence=confidence,
            risk_level=risk_level,
            scenarios=scenarios,
            layer_results=layer_results,
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
            symbol=symbol,
            analysis_fingerprint=fingerprint,
        )

        if persist:
            self._persist(report, analysis_dict)

        log.info(
            "ai decision bias={} conf={:.1f} narrative={} risk={} primary={}",
            report.market_bias,
            report.confidence,
            report.primary_narrative,
            report.risk_level,
            report.primary_scenario,
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


def _fingerprint(analysis: dict[str, Any]) -> str:
    stable = {
        "market_bias": analysis.get("market_bias"),
        "confidence": analysis.get("confidence"),
        "market_regime": analysis.get("market_regime"),
        "volatility": analysis.get("volatility"),
        "layer_results": analysis.get("layer_results"),
        "scenarios": analysis.get("scenarios"),
        "weights": analysis.get("weights"),
        "conflicts": analysis.get("conflicts"),
    }
    raw = json.dumps(stable, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
