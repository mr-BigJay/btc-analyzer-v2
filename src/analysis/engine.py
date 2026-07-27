"""Analysis Engine — core intelligence pipeline (Ch.6).

No AI inference here. No trade execution.
"""

from __future__ import annotations

from typing import Iterable

from src.analysis.conflict import resolve_conflicts
from src.analysis.context import MarketContext, build_market_context
from src.analysis.contracts import LayerResult, MarketAnalysisOutput, SignalBias
from src.analysis.layers import ALL_LAYERS
from src.analysis.scenarios import generate_scenarios
from src.analysis.weights import compute_weights
from src.config import settings
from src.logging_setup import get_logger
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository

log = get_logger("analysis.engine")

TIMEFRAMES = ("5m", "15m", "1h", "4h", "1d")


class AnalysisEngine:
    """Multi-layer evidence model (Ch.6 §6.2–§6.11)."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.layers = [cls() for cls in ALL_LAYERS]

    def analyze(
        self,
        *,
        symbol: str | None = None,
        timeframe: str = "1h",
        context: MarketContext | None = None,
        near_options_expiry: bool = False,
        multi_timeframe: bool = True,
    ) -> MarketAnalysisOutput:
        symbol = symbol or settings.binance_symbol
        ctx = context or build_market_context(self.repository, symbol=symbol, timeframe=timeframe)

        layer_results = self._run_layers(ctx)
        weights = compute_weights(layer_results, near_options_expiry=near_options_expiry)
        resolution = resolve_conflicts(layer_results, weights)

        mtf = {}
        if multi_timeframe:
            mtf = self._multi_timeframe(symbol, primary=timeframe)

        scenarios = generate_scenarios(
            market_bias=resolution.market_bias,
            confidence=resolution.confidence,
            ctx=ctx,
            layer_results=layer_results,
        )
        primary = scenarios[0].name if scenarios else "Sideways Consolidation"

        vol_label = _volatility_label(layer_results)
        regime = _market_regime(resolution.market_bias, layer_results)
        risk = _risk_level(resolution.confidence, resolution.mixed, vol_label)

        output = MarketAnalysisOutput(
            market_bias=resolution.market_bias,
            confidence=round(resolution.confidence, 1),
            market_regime=regime,
            volatility=vol_label,
            primary_scenario=primary,
            risk_level=risk,
            layer_results=[r.to_dict() for r in layer_results],
            scenarios=[s.to_dict() for s in scenarios],
            weights={k: round(v, 4) for k, v in weights.items()},
            conflicts=resolution.conflicts,
            timeframe_alignment=mtf,
            symbol=symbol,
        )

        # Cache for AI Decision Engine (Ch.7) — not the Daily Outlook itself
        redis_cache.set("latest_market_analysis", output.to_dict(), ttl_sec=settings.redis_hot_ttl_sec)
        log.info(
            "analysis bias={} conf={:.1f} regime={} primary={}",
            output.market_bias,
            output.confidence,
            output.market_regime,
            output.primary_scenario,
        )
        return output

    def _run_layers(self, ctx: MarketContext) -> list[LayerResult]:
        results: list[LayerResult] = []
        for layer in self.layers:
            try:
                results.append(layer.analyze(ctx))
            except Exception as exc:  # noqa: BLE001
                log.warning("layer {} failed: {}", layer.NAME, exc)
                results.append(
                    LayerResult(
                        layer=layer.NAME,
                        signal=SignalBias.HIGH_UNCERTAINTY.value,
                        confidence=20,
                        summary=f"Layer error: {exc}",
                        timeframe=ctx.timeframe,
                        data_quality=0.0,
                        tags=["ERROR"],
                    )
                )
        return results

    def _multi_timeframe(self, symbol: str, *, primary: str) -> dict:
        """Reconcile bias across timeframes (Ch.6 §6.9)."""
        biases: dict[str, str] = {}
        for tf in TIMEFRAMES:
            ctx = build_market_context(self.repository, symbol=symbol, timeframe=tf)
            # Reuse same OHLCV if DB only has one TF — still run structure/technical lightly
            if not ctx.ohlcv and tf != primary:
                continue
            results = self._run_layers(ctx)
            weights = compute_weights(results)
            resolution = resolve_conflicts(results, weights)
            biases[tf] = resolution.market_bias

        values = list(biases.values())
        aligned = len(set(values)) == 1 and len(values) >= 2
        divergent = len(set(values)) >= 3
        return {
            "biases": biases,
            "aligned": aligned,
            "divergent": divergent,
            "summary": "aligned" if aligned else "divergent" if divergent else "partial",
        }


def _volatility_label(results: Iterable[LayerResult]) -> str:
    for r in results:
        if r.layer == "Volatility":
            if "High Volatility" in r.tags or "Expansion" in r.tags:
                return "High"
            if "Low Volatility" in r.tags or "Compression" in r.tags:
                return "Low"
            return "Medium"
    return "Medium"


def _market_regime(bias: str, results: list[LayerResult]) -> str:
    tags = {t for r in results for t in r.tags}
    if "Compression" in tags:
        return "Compression"
    if "Expansion" in tags or "Breakout Probability" in tags:
        return "Breakout"
    if bias in (SignalBias.BULLISH.value, SignalBias.BEARISH.value) and "Trend Strength" in tags:
        return "Trend"
    if bias == SignalBias.HIGH_UNCERTAINTY.value:
        return "Uncertain"
    return "Range"


def _risk_level(confidence: float, mixed: bool, vol: str) -> str:
    if mixed or vol == "High" or confidence < 40:
        return "High"
    if confidence >= 70 and vol == "Low":
        return "Low"
    return "Moderate"
