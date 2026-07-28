"""Futures / derivatives features (Ch.13 §13.6)."""

from __future__ import annotations

from typing import Any

from src.features.categories._util import feat
from src.features.contracts import FeatureCategory, FeatureRecord, FeatureScale
from src.features.normalize import clamp, normalize_directional, normalize_probability


def compute_futures_features(
    *,
    funding_rate: float | None = None,
    open_interest: float | None = None,
    open_interest_prev: float | None = None,
    funding_prev: float | None = None,
    long_ratio: float | None = None,
    short_ratio: float | None = None,
    liquidation_long: float | None = None,
    liquidation_short: float | None = None,
    asset: str = "BTCUSDT",
    timeframe: str = "1h",
) -> dict[str, FeatureRecord]:
    cat = FeatureCategory.DERIVATIVES
    out: dict[str, FeatureRecord] = {}

    oi_mom = None
    if open_interest is not None and open_interest_prev is not None and open_interest_prev != 0:
        oi_mom = (open_interest - open_interest_prev) / abs(open_interest_prev)
    oi_vel = oi_mom  # single-step proxy without history series

    fund_trend = None
    if funding_rate is not None and funding_prev is not None:
        fund_trend = funding_rate - funding_prev
    elif funding_rate is not None:
        fund_trend = funding_rate

    fund_accel = fund_trend  # without deeper history
    long_trend = long_ratio
    short_trend = short_ratio

    liq_pressure = None
    if liquidation_long is not None or liquidation_short is not None:
        ll = liquidation_long or 0.0
        ls = liquidation_short or 0.0
        tot = ll + ls
        liq_pressure = ((ls - ll) / tot) if tot else 0.0

    leveraged = None
    if funding_rate is not None or oi_mom is not None:
        parts = []
        if funding_rate is not None:
            parts.append(clamp(funding_rate / 0.001, -1, 1))
        if oi_mom is not None:
            parts.append(clamp(oi_mom / 0.05, -1, 1))
        leveraged = normalize_directional(sum(parts) / len(parts), scale=1.0)

    squeeze = None
    if funding_rate is not None and oi_mom is not None:
        # Crowded long + rising OI → squeeze risk toward shorts when funding extreme
        squeeze = normalize_probability(abs(funding_rate) / 0.001 * 40 + abs(oi_mom) / 0.05 * 40)

    crowded = None
    if long_ratio is not None:
        crowded = normalize_probability(abs(long_ratio - 0.5) * 200)
    elif funding_rate is not None:
        crowded = normalize_probability(min(100.0, abs(funding_rate) / 0.0005 * 50))

    def add(name: str, value: Any, scale: FeatureScale = FeatureScale.RAW, parents: list[str] | None = None) -> None:
        out[name] = feat(
            name,
            None if value is None else round(float(value), 8),
            cat,
            scale=scale,
            asset=asset,
            timeframe=timeframe,
            parents=parents or [],
            source="Futures API",
        )

    add("oi_momentum", oi_mom, FeatureScale.RAW, ["open_interest"])
    add("oi_velocity", oi_vel, FeatureScale.RAW, ["open_interest"])
    add("funding_trend", fund_trend, FeatureScale.RAW, ["funding_rate"])
    add("funding_acceleration", fund_accel, FeatureScale.RAW, ["funding_rate"])
    add("long_ratio_trend", long_trend, FeatureScale.RATIO, ["long_ratio"])
    add("short_ratio_trend", short_trend, FeatureScale.RATIO, ["short_ratio"])
    add("liquidation_pressure", liq_pressure, FeatureScale.RAW, ["liquidation_long", "liquidation_short"])
    add("leveraged_pressure", leveraged, FeatureScale.DIRECTIONAL, ["funding_trend", "oi_momentum"])
    add("squeeze_probability", squeeze, FeatureScale.PROBABILITY, ["funding_rate", "oi_momentum"])
    add("crowded_trade_score", crowded, FeatureScale.PROBABILITY, ["long_ratio", "funding_rate"])
    return out
