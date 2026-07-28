"""Volume features (Ch.13 §13.5)."""

from __future__ import annotations

from src.features.categories._util import feat, safe_div, slope
from src.features.contracts import FeatureCategory, FeatureRecord, FeatureScale
from src.features.normalize import clamp, normalize_directional, normalize_probability


def compute_volume_features(
    volumes: list[float],
    *,
    bid_volume: float | None = None,
    ask_volume: float | None = None,
    asset: str = "BTCUSDT",
    timeframe: str = "1h",
) -> dict[str, FeatureRecord]:
    cat = FeatureCategory.VOLUME
    out: dict[str, FeatureRecord] = {}
    if not volumes:
        for name in (
            "relative_volume",
            "volume_acceleration",
            "delta_volume",
            "buyer_seller_imbalance",
            "rolling_avg_volume",
            "volume_spike_score",
            "buy_pressure",
            "sell_pressure",
            "volume_quality",
        ):
            out[name] = feat(name, None, cat, asset=asset, timeframe=timeframe, parents=["volume"], source="OHLCV")
        return out

    v = volumes[-1]
    avg = sum(volumes[-20:]) / min(20, len(volumes))
    rel = safe_div(v, avg)
    vel = slope(volumes, 5)
    accel = slope(volumes, 8)
    delta = None
    imbalance = None
    if bid_volume is not None and ask_volume is not None:
        delta = bid_volume - ask_volume
        tot = bid_volume + ask_volume
        imbalance = safe_div(bid_volume - ask_volume, tot) if tot else None
    elif len(volumes) >= 2:
        # Proxy delta from volume change sign vs price not available here
        delta = volumes[-1] - volumes[-2]

    spike = None
    if rel is not None:
        spike = clamp((rel - 1.0) / 3.0, 0.0, 1.0)

    buy_p = None
    sell_p = None
    if imbalance is not None:
        buy_p = normalize_probability((imbalance + 1) / 2 * 100)
        sell_p = normalize_probability((1 - imbalance) / 2 * 100)
    elif delta is not None and avg:
        buy_p = normalize_probability(50 + clamp(delta / avg, -1, 1) * 50)
        sell_p = normalize_probability(100 - (buy_p or 50))

    quality = None
    if rel is not None:
        # Prefer moderate relative volume as higher quality participation signal
        quality = normalize_probability(100 - abs(rel - 1.0) * 40)

    def add(name, value, scale=FeatureScale.RAW, parents=None):
        out[name] = feat(
            name,
            None if value is None else round(float(value), 8),
            cat,
            scale=scale,
            asset=asset,
            timeframe=timeframe,
            parents=parents or ["volume"],
            source="OHLCV",
        )

    add("relative_volume", rel, FeatureScale.RAW)
    add("volume_acceleration", accel, FeatureScale.RAW)
    add("delta_volume", delta, FeatureScale.RAW)
    add("buyer_seller_imbalance", imbalance, FeatureScale.RAW, ["bid_volume", "ask_volume"])
    add("rolling_avg_volume", avg, FeatureScale.RAW)
    add("volume_spike_score", spike, FeatureScale.RATIO)
    add("buy_pressure", buy_p, FeatureScale.PROBABILITY, ["delta_volume"])
    add("sell_pressure", sell_p, FeatureScale.PROBABILITY, ["delta_volume"])
    add("volume_quality", quality, FeatureScale.PROBABILITY, ["relative_volume"])
    _ = vel  # reserved for lineage completeness
    return out
