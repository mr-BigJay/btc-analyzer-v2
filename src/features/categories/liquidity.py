"""Liquidity features (Ch.13 §13.10)."""

from __future__ import annotations

from typing import Any

from src.features.categories._util import feat, safe_div
from src.features.contracts import FeatureCategory, FeatureRecord, FeatureScale
from src.features.normalize import clamp, normalize_probability


def compute_liquidity_features(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    order_book: dict[str, Any] | None = None,
    asset: str = "BTCUSDT",
    timeframe: str = "1h",
) -> dict[str, FeatureRecord]:
    cat = FeatureCategory.LIQUIDITY
    out: dict[str, FeatureRecord] = {}
    spot = closes[-1] if closes else None

    # Equal highs density
    eq_high = 0
    if len(highs) >= 5 and spot:
        tol = spot * 0.001
        last_h = highs[-1]
        eq_high = sum(1 for h in highs[-20:] if abs(h - last_h) <= tol)

    # FVG width proxy: gap between candle[i].low and candle[i-2].high
    fvg_width = None
    if len(highs) >= 3 and len(lows) >= 3 and spot:
        gap = lows[-1] - highs[-3]
        if gap > 0:
            fvg_width = gap / spot
        gap2 = lows[-3] - highs[-1]
        if gap2 > 0:
            fvg_width = max(fvg_width or 0.0, gap2 / spot)

    # Untapped liquidity: distance to recent swing high/low
    dist_liq = None
    if spot and highs and lows:
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        dist_liq = min(abs(recent_high - spot), abs(spot - recent_low)) / spot

    density = None
    ob = order_book or {}
    bids = ob.get("bids") or []
    asks = ob.get("asks") or []
    if bids and asks:
        try:
            bid_sz = sum(float(b[1]) for b in bids[:10] if isinstance(b, (list, tuple)) and len(b) >= 2)
            ask_sz = sum(float(a[1]) for a in asks[:10] if isinstance(a, (list, tuple)) and len(a) >= 2)
            tot = bid_sz + ask_sz
            density = tot
            imbalance = (bid_sz - ask_sz) / tot if tot else 0.0
        except (TypeError, ValueError, IndexError):
            imbalance = None
    else:
        imbalance = None

    ob_strength = None
    if imbalance is not None:
        ob_strength = clamp(abs(imbalance), 0, 1)

    liq_pressure = normalize_probability((1.0 - (dist_liq or 0.5)) * 100) if dist_liq is not None else None
    sweep = normalize_probability(((eq_high / 5.0) * 40 + (1.0 - (dist_liq or 0.5)) * 40)) if dist_liq is not None else None
    magnet = normalize_probability((fvg_width or 0) / 0.01 * 50 + (eq_high / 5.0) * 40) if fvg_width is not None or eq_high else None

    def add(name: str, value: Any, scale: FeatureScale = FeatureScale.RAW, parents: list[str] | None = None) -> None:
        out[name] = feat(
            name,
            None if value is None else round(float(value), 8),
            cat,
            scale=scale,
            asset=asset,
            timeframe=timeframe,
            parents=parents or ["high", "low", "order_book"],
            source="liquidity",
        )

    add("distance_to_liquidity", dist_liq, FeatureScale.RATIO)
    add("liquidity_density", density, FeatureScale.RAW, ["order_book"])
    add("untapped_liquidity", dist_liq, FeatureScale.RATIO)
    add("fvg_width", fvg_width, FeatureScale.RATIO)
    add("order_block_strength", ob_strength, FeatureScale.RATIO, ["order_book"])
    add("equal_high_density", float(eq_high), FeatureScale.RAW)
    add("liquidity_pressure", liq_pressure, FeatureScale.PROBABILITY)
    add("sweep_probability", sweep, FeatureScale.PROBABILITY)
    add("magnet_strength", magnet, FeatureScale.PROBABILITY)
    _ = safe_div
    return out
