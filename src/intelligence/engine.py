"""Market Intelligence Framework engine (Ch.8).

Consumes Analysis Engine output (+ optional macro/cross-asset cache).
Produces strategic context for the AI Decision Engine.
Deterministic for identical inputs.
"""

from __future__ import annotations

from typing import Any

from src.analysis.contracts import MarketAnalysisOutput
from src.analysis.engine import AnalysisEngine
from src.cache.keys import CacheKeys
from src.config import settings
from src.intelligence.contracts import MarketIntelligenceOutput
from src.intelligence.cross_asset import assess_cross_asset
from src.intelligence.cycle import classify_cycle
from src.intelligence.derivatives import analyze_derivatives
from src.intelligence.health import compute_mhi
from src.intelligence.helpers import as_dict
from src.intelligence.liquidity import classify_liquidity
from src.intelligence.macro import assess_macro
from src.intelligence.participants import estimate_participants
from src.intelligence.regime import classify_regime
from src.intelligence.stress import compute_msi
from src.intelligence.transitions import detect_transitions
from src.intelligence.volatility import classify_volatility
from src.logging_setup import get_logger
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository

log = get_logger("intelligence.engine")


class MarketIntelligenceEngine:
    """Strategic context layer (Ch.8 §8.2)."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.analysis_engine = AnalysisEngine(self.repository)

    def evaluate(
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
    ) -> MarketIntelligenceOutput:
        symbol = symbol or settings.binance_symbol

        if analysis is None:
            if not run_analysis_if_missing:
                cached = redis_cache.get("latest_market_analysis")
                if isinstance(cached, dict):
                    analysis = cached
                else:
                    raise ValueError("No Analysis Engine output available for Market Intelligence")
            else:
                analysis = self.analysis_engine.analyze(
                    symbol=symbol,
                    timeframe=timeframe,
                    multi_timeframe=multi_timeframe,
                    near_options_expiry=near_options_expiry,
                )

        data = as_dict(analysis)
        market_regime, regime_scores = classify_regime(data)
        market_cycle, cycle_scores = classify_cycle(data, market_regime=market_regime)
        dominant, inst_activity, participant_scores = estimate_participants(data)
        liquidity_state, liquidity_meta = classify_liquidity(data)
        vol_regime = classify_volatility(data)
        derivatives_thesis = analyze_derivatives(data)
        macro_bias, macro_events, macro_completeness = assess_macro(macro_event=macro_event)
        cross_bias, cross_snapshot, cross_completeness = assess_cross_asset()

        completeness = round(
            0.55 * 1.0  # analysis layers assumed present
            + 0.25 * macro_completeness
            + 0.20 * cross_completeness,
            3,
        )

        mhi, mhi_band, mhi_components = compute_mhi(
            data,
            volatility_regime=vol_regime,
            liquidity_state=liquidity_state,
            macro_bias=macro_bias,
            data_completeness=completeness,
        )
        msi_level, msi_score, msi_drivers = compute_msi(
            data,
            volatility_regime=vol_regime,
            liquidity_state=liquidity_state,
            macro_bias=macro_bias,
            near_options_expiry=near_options_expiry,
        )
        transition_p, transitions = detect_transitions(
            data,
            market_regime=market_regime,
            market_cycle=market_cycle,
            volatility_regime=vol_regime,
            regime_scores=regime_scores,
        )

        # If transition probability dominates, promote Transition regime
        if transition_p >= 55 and market_regime not in (
            "Compression",
            "Expansion",
        ):
            # Keep strong trends unless transition is decisive
            if transition_p >= 70 or "Competing regimes" in " ".join(transitions):
                market_regime = "Transition"

        output = MarketIntelligenceOutput(
            market_regime=market_regime,
            market_cycle=market_cycle,
            dominant_participant=dominant,
            institutional_activity=inst_activity,
            market_health_index=mhi,
            market_health_band=mhi_band,
            market_stress_index=msi_level,
            market_stress_score=msi_score,
            volatility_regime=vol_regime,
            macro_bias=macro_bias,
            cross_asset_bias=cross_bias,
            liquidity_state=liquidity_state,
            transition_probability=transition_p,
            detected_transitions=transitions,
            derivatives_thesis=derivatives_thesis,
            participant_scores={k: round(v, 2) for k, v in participant_scores.items()},
            macro_events=macro_events,
            cross_asset=cross_snapshot,
            details={
                "regime_scores": {k: round(v, 2) for k, v in regime_scores.items()},
                "cycle_scores": {k: round(v, 2) for k, v in cycle_scores.items()},
                "mhi_components": mhi_components,
                "msi_drivers": msi_drivers,
                "liquidity": liquidity_meta,
                "analysis_bias": data.get("market_bias"),
                "analysis_confidence": data.get("confidence"),
            },
            data_completeness=completeness,
            symbol=symbol,
        )

        if persist:
            redis_cache.set(CacheKeys.LATEST_MARKET_INTELLIGENCE, output.to_dict(), ttl_sec=settings.redis_hot_ttl_sec)
            redis_cache.set("latest_market_intelligence", output.to_dict(), ttl_sec=settings.redis_hot_ttl_sec)

        log.info(
            "intelligence regime={} cycle={} mhi={} msi={} participant={} transition={}",
            output.market_regime,
            output.market_cycle,
            output.market_health_index,
            output.market_stress_index,
            output.dominant_participant,
            output.transition_probability,
        )
        return output
