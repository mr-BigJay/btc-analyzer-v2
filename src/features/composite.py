"""Composite features (Ch.13 §13.13)."""

from __future__ import annotations

from typing import Any

from src.features.categories._util import feat
from src.features.contracts import FeatureCategory, FeatureRecord, FeatureScale
from src.features.normalize import clamp, normalize_directional, normalize_probability


def _num(features: dict[str, FeatureRecord], name: str) -> float | None:
    rec = features.get(name)
    if rec is None or rec.value is None or isinstance(rec.value, str):
        return None
    try:
        return float(rec.value)
    except (TypeError, ValueError):
        return None


def compute_composites(features: dict[str, FeatureRecord], *, asset: str = "BTCUSDT", timeframe: str = "1h") -> dict[str, FeatureRecord]:
    cat = FeatureCategory.COMPOSITE
    out: dict[str, FeatureRecord] = {}

    buy = _num(features, "buy_pressure")
    oi = _num(features, "oi_momentum")
    fund = _num(features, "funding_trend")
    delta = _num(features, "delta_volume")
    liq = _num(features, "liquidity_pressure")

    parts: list[float] = []
    if buy is not None:
        parts.append((buy - 50) / 50)
    if oi is not None:
        parts.append(clamp(oi / 0.05, -1, 1))
    if fund is not None:
        parts.append(clamp(fund / 0.001, -1, 1))
    if delta is not None:
        parts.append(clamp(delta / (abs(delta) + 1), -1, 1))
    if liq is not None:
        parts.append((liq - 50) / 50)
    mpi = normalize_directional(sum(parts) / len(parts), scale=1.0) if parts else None

    # Institutional activity score
    gamma = _num(features, "hedging_pressure")
    dealer = _num(features, "dealer_bias")
    vol_q = _num(features, "volume_quality")
    opt_sent = _num(features, "options_sentiment")
    iparts: list[float] = []
    if gamma is not None:
        iparts.append(gamma / 100)
    if dealer is not None:
        iparts.append(abs(dealer) / 100)
    if vol_q is not None:
        iparts.append(vol_q / 100)
    if opt_sent is not None:
        iparts.append(abs(opt_sent) / 100)
    if buy is not None and buy >= 60:
        iparts.append(0.7)
    ias = normalize_probability(sum(iparts) / len(iparts) * 100) if iparts else None

    def add(name: str, value: Any, parents: list[str]) -> None:
        out[name] = feat(
            name,
            None if value is None else round(float(value), 6),
            cat,
            scale=FeatureScale.DIRECTIONAL if "index" in name or "bias" in name else FeatureScale.PROBABILITY,
            asset=asset,
            timeframe=timeframe,
            parents=parents,
            source="composite",
        )

    add(
        "market_pressure_index",
        mpi,
        ["buy_pressure", "oi_momentum", "funding_trend", "delta_volume", "liquidity_pressure"],
    )
    # Override scale for MPI to directional
    if "market_pressure_index" in out:
        out["market_pressure_index"].scale = FeatureScale.DIRECTIONAL.value

    add(
        "institutional_activity_score",
        ias,
        ["hedging_pressure", "dealer_bias", "volume_quality", "options_sentiment", "buy_pressure"],
    )
    if "institutional_activity_score" in out:
        out["institutional_activity_score"].scale = FeatureScale.PROBABILITY.value

    return out
