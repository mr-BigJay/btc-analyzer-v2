"""Scoring & Decision Model engine (Ch.9).

Deterministic quantitative foundation before AI reasoning.
"""

from __future__ import annotations

from typing import Any

from src.analysis.contracts import MarketAnalysisOutput
from src.analysis.engine import AnalysisEngine
from src.cache.keys import CacheKeys
from src.config import settings
from src.intelligence.contracts import MarketIntelligenceOutput
from src.intelligence.engine import MarketIntelligenceEngine
from src.logging_setup import get_logger
from src.scoring.composites import decision_matrix_score, market_bias_score, risk_score_from_inputs
from src.scoring.confidence import calibrate_confidence_score
from src.scoring.contracts import DecisionObject, classify_bias
from src.scoring.layers import layer_score_details, score_all_layers
from src.scoring.quality import compute_dqs
from src.scoring.rules import publication_gate
from src.scoring.validation import record_decision
from src.scoring.weights import select_weights
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository

log = get_logger("scoring.engine")


class ScoringEngine:
    """Quantitative scoring pipeline (Ch.9 §9.3)."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.analysis_engine = AnalysisEngine(self.repository)
        self.intelligence_engine = MarketIntelligenceEngine(self.repository)

    def score(
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
        run_upstream_if_missing: bool = True,
    ) -> DecisionObject:
        symbol = symbol or settings.binance_symbol

        if analysis is None:
            if not run_upstream_if_missing:
                cached = redis_cache.get("latest_market_analysis")
                if isinstance(cached, dict):
                    analysis = cached
                else:
                    raise ValueError("No Analysis Engine output available for Scoring Engine")
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

        # 1–2 Normalization + layer scores
        layer_scores = score_all_layers(analysis_dict)

        # 3 Dynamic weighting by regime
        weights, weight_regime = select_weights(
            market_regime=str(intel.get("market_regime") or ""),
            volatility_regime=str(intel.get("volatility_regime") or ""),
            analysis_regime=str(analysis_dict.get("market_regime") or ""),
            layer_scores=layer_scores,
            layer_results=list(analysis_dict.get("layer_results") or []),
            near_options_expiry=near_options_expiry,
        )

        # 4 Composite scores
        mbs = market_bias_score(layer_scores, weights)
        dqs, dqs_label, dqs_details = compute_dqs(analysis_dict, intelligence=intel)
        cs, alignment, penalties, conf_meta = calibrate_confidence_score(
            layer_scores=layer_scores,
            analysis=analysis_dict,
            intelligence=intel,
            data_quality_score=dqs,
            near_macro=macro_event,
        )
        rs = risk_score_from_inputs(
            intelligence=intel,
            analysis=analysis_dict,
            near_options_expiry=near_options_expiry,
            macro_event=macro_event,
        )
        mhi = float(intel.get("market_health_index") or 50.0)
        # MSI as 0–100 numeric for composites
        msi_numeric = float(intel.get("market_stress_score") or 0)
        if msi_numeric <= 0:
            msi_label = str(intel.get("market_stress_index") or "Moderate")
            msi_numeric = {"Low": 18, "Moderate": 40, "Elevated": 58, "High": 75, "Extreme": 90}.get(msi_label, 40)

        matrix_score, matrix_components = decision_matrix_score(
            mbs=mbs, confidence=cs, risk=rs, mhi=mhi, msi=msi_numeric
        )

        bias = classify_bias(mbs)
        # Extreme multi-layer conflict can soften published decision toward Neutral
        if any(p.get("pair") == "multi-layer contradiction" for p in penalties) and abs(mbs) < 40:
            bias = classify_bias(mbs * 0.5)
            # keep MBS as-is for transparency; decision label may soft-neutralize via classify on dampened

        publish, notes = publication_gate(
            data_quality_score=dqs,
            confidence_score=cs,
            composites_ok=True,
        )
        if cs < float(getattr(settings, "scoring_min_confidence", 55.0)):
            notes.append("Elevated uncertainty — confidence below preferred publication threshold")

        decision = DecisionObject(
            market_bias=bias,
            market_bias_score=mbs,
            confidence_score=cs,
            risk_score=rs,
            market_health_index=round(mhi, 1),
            market_stress_index=round(msi_numeric, 1),
            data_quality_score=dqs,
            timeframe_alignment=alignment,
            decision=bias,
            publish=publish,
            layer_scores=layer_scores,
            weights=weights,
            weight_regime=weight_regime,
            composite_matrix={
                "matrix_score": matrix_score,
                "components": matrix_components,
                "component_weights": {
                    "market_bias_score": 0.40,
                    "confidence_score": 0.25,
                    "risk_score": 0.15,
                    "market_health_index": 0.10,
                    "market_stress_index": 0.10,
                },
            },
            conflict_penalties=penalties,
            publication_notes=notes,
            details={
                "layer_interpretations": layer_score_details(layer_scores),
                "confidence_meta": conf_meta,
                "dqs": dqs_details,
                "dqs_band": dqs_label,
                "intelligence_regime": intel.get("market_regime"),
                "intelligence_cycle": intel.get("market_cycle"),
                "msi_label": intel.get("market_stress_index"),
            },
            symbol=symbol,
        )

        if persist:
            redis_cache.set(CacheKeys.LATEST_DECISION_OBJECT, decision.to_dict(), ttl_sec=settings.redis_hot_ttl_sec)
            redis_cache.set("latest_decision_object", decision.to_dict(), ttl_sec=settings.redis_hot_ttl_sec)
            try:
                record_decision(decision.to_dict(), analysis_input=analysis_dict)
            except Exception as exc:  # noqa: BLE001
                log.warning("scoring validation record failed: {}", exc)
            try:
                self.repository.append_market_score(decision.to_dict())
            except Exception as exc:  # noqa: BLE001
                log.warning("market_scores DB persist failed: {}", exc)

        log.info(
            "scoring bias={} mbs={} cs={} rs={} dqs={} publish={} regime_weights={}",
            decision.market_bias,
            decision.market_bias_score,
            decision.confidence_score,
            decision.risk_score,
            decision.data_quality_score,
            decision.publish,
            decision.weight_regime,
        )
        return decision
