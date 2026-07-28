"""Feature Engineering Engine (Ch.13).

Transforms MarketContext / normalized observations into validated FeatureSets.
"""

from __future__ import annotations

import time
from typing import Any

from src.analysis.context import MarketContext, build_market_context
from src.features.categories import (
    compute_futures_features,
    compute_liquidity_features,
    compute_options_features,
    compute_price_features,
    compute_structural_features,
    compute_technical_features,
    compute_volatility_features,
    compute_volume_features,
)
from src.features.cleaning import clean_series, drop_invalid_ohlcv, missing_ratio
from src.features.composite import compute_composites
from src.features.contracts import FeatureSet, utc_now_iso
from src.features.mtf import synchronize_timeframes
from src.features.outliers import detect_outliers
from src.features.store import feature_store_memory, persist_feature_set
from src.features.validation import validate_feature_set
from src.logging_setup import get_logger
from src.storage.repository import CentralRepository

log = get_logger("features.engine")

OUTPUT_KEYS = (
    "price_strength",
    "trend_velocity",
    "price_acceleration",
    "buy_pressure",
    "sell_pressure",
    "volume_quality",
    "leveraged_pressure",
    "squeeze_probability",
    "crowded_trade_score",
    "dealer_bias",
    "hedging_pressure",
    "options_sentiment",
    "technical_strength",
    "momentum_state",
    "breakout_readiness",
    "structure_quality",
    "trend_integrity",
    "reversal_probability",
    "liquidity_pressure",
    "sweep_probability",
    "magnet_strength",
    "volatility_state",
    "expansion_probability",
    "market_pressure_index",
    "institutional_activity_score",
)


class FeatureEngineeringEngine:
    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()

    def engineer(
        self,
        context: MarketContext | dict[str, Any] | None = None,
        *,
        symbol: str | None = None,
        timeframe: str = "1h",
        persist: bool = True,
        multi_timeframe: bool = False,
    ) -> FeatureSet | dict[str, Any]:
        if multi_timeframe:
            return synchronize_timeframes(lambda tf: self.engineer(context, symbol=symbol, timeframe=tf, persist=persist, multi_timeframe=False))  # type: ignore[return-value]

        t0 = time.perf_counter()
        if context is None:
            ctx = build_market_context(self.repository, symbol=symbol, timeframe=timeframe)
        elif isinstance(context, MarketContext):
            ctx = context
            ctx.timeframe = timeframe or ctx.timeframe
            if symbol:
                ctx.symbol = symbol
        else:
            ctx = build_market_context(self.repository, symbol=symbol, timeframe=timeframe)
            # Overlay dict fields when provided
            for k, v in context.items():
                if hasattr(ctx, k):
                    setattr(ctx, k, v)

        ohlcv = drop_invalid_ohlcv(list(ctx.ohlcv or []))
        closes = [float(r["close"]) for r in ohlcv]
        highs = [float(r["high"]) for r in ohlcv]
        lows = [float(r["low"]) for r in ohlcv]
        volumes = [float(r.get("volume") or 0.0) for r in ohlcv]
        closes = [v for v in clean_series(closes, forward_fill=False) if v is not None]
        # Re-align highs/lows/volumes to cleaned close length if needed
        if len(highs) != len(closes):
            highs = highs[-len(closes) :] if closes else []
            lows = lows[-len(closes) :] if closes else []
            volumes = volumes[-len(closes) :] if closes else []

        features = {}
        features.update(compute_price_features(closes, highs, lows, volumes=volumes, asset=ctx.symbol, timeframe=timeframe))
        features.update(
            compute_volume_features(
                volumes,
                asset=ctx.symbol,
                timeframe=timeframe,
            )
        )
        features.update(
            compute_futures_features(
                funding_rate=ctx.funding_rate,
                open_interest=ctx.open_interest,
                long_ratio=ctx.long_short_ratio,
                short_ratio=(1.0 - ctx.long_short_ratio) if ctx.long_short_ratio is not None else None,
                liquidation_long=(ctx.liquidations or {}).get("long"),
                liquidation_short=(ctx.liquidations or {}).get("short"),
                asset=ctx.symbol,
                timeframe=timeframe,
            )
        )
        features.update(
            compute_options_features(
                put_call_ratio=ctx.put_call_ratio,
                iv=ctx.implied_volatility_mean,
                iv_rank=ctx.iv_rank,
                iv_percentile=ctx.iv_percentile,
                gamma_exposure=ctx.gamma_exposure,
                dealer_gamma=ctx.dealer_gamma,
                dealer_delta=ctx.dealer_delta,
                max_pain=ctx.max_pain,
                spot=ctx.mark_price or ctx.spot_price,
                asset=ctx.symbol,
                timeframe=timeframe,
            )
        )
        features.update(compute_technical_features(closes, highs, lows, asset=ctx.symbol, timeframe=timeframe))
        features.update(compute_structural_features(highs, lows, closes, asset=ctx.symbol, timeframe=timeframe))
        features.update(
            compute_liquidity_features(highs, lows, closes, order_book=ctx.order_book, asset=ctx.symbol, timeframe=timeframe)
        )
        features.update(
            compute_volatility_features(
                closes,
                highs,
                lows,
                implied_volatility=ctx.implied_volatility_mean,
                asset=ctx.symbol,
                timeframe=timeframe,
            )
        )
        features.update(compute_composites(features, asset=ctx.symbol, timeframe=timeframe))

        # Outlier flags on aggregate payload
        payload_probe = {
            "price": ctx.mark_price or (closes[-1] if closes else None),
            "funding_rate": ctx.funding_rate,
            "volume": volumes[-1] if volumes else None,
            "volume_spike_score": features["volume_spike_score"].value if "volume_spike_score" in features else None,
            "timestamp": utc_now_iso(),
        }
        outlier_flags = detect_outliers(payload_probe)
        for flag in outlier_flags:
            if flag.field in features:
                features[flag.field].flagged_outlier = True

        missing_count = sum(1 for f in features.values() if f.missing or f.value is None)
        total = max(1, len(features))
        completeness = 1.0 - (missing_count / total)
        # Also penalize sparse OHLCV
        ohlcv_pen = missing_ratio(closes) if closes else 1.0
        data_quality = max(0.0, min(1.0, completeness * (1.0 - 0.4 * ohlcv_pen) - 0.05 * len(outlier_flags)))

        outputs = {k: (features[k].value if k in features else None) for k in OUTPUT_KEYS}
        composites = {
            "market_pressure_index": features["market_pressure_index"].value if "market_pressure_index" in features else None,
            "institutional_activity_score": features["institutional_activity_score"].value
            if "institutional_activity_score" in features
            else None,
        }

        fs = FeatureSet(
            asset=ctx.symbol,
            timeframe=timeframe,
            timestamp=utc_now_iso(),
            features=features,
            composites=composites,
            outputs=outputs,
            missing_count=missing_count,
            outlier_flags=[f"{o.field}:{o.code}" for o in outlier_flags],
            data_quality=round(data_quality, 4),
        )
        fs, _report = validate_feature_set(fs)
        fs.elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        feature_store_memory.put(fs)
        if persist:
            try:
                persist_feature_set(fs, module="features")
            except Exception as exc:  # noqa: BLE001
                log.warning("feature_store persist failed: {}", exc)

        log.info(
            "features asset={} tf={} missing={} dq={} elapsed_ms={}",
            fs.asset,
            fs.timeframe,
            fs.missing_count,
            fs.data_quality,
            fs.elapsed_ms,
        )
        return fs
