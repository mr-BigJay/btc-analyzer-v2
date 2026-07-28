"""Structural features (Ch.13 §13.9)."""

from __future__ import annotations

from typing import Any

from src.features.categories._util import feat
from src.features.contracts import FeatureCategory, FeatureRecord, FeatureScale
from src.features.normalize import normalize_directional, normalize_probability


def _swings(highs: list[float], lows: list[float], left: int = 2, right: int = 2) -> tuple[list[int], list[int]]:
    sh: list[int] = []
    sl: list[int] = []
    n = min(len(highs), len(lows))
    for i in range(left, n - right):
        if highs[i] == max(highs[i - left : i + right + 1]):
            sh.append(i)
        if lows[i] == min(lows[i - left : i + right + 1]):
            sl.append(i)
    return sh, sl


def compute_structural_features(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    asset: str = "BTCUSDT",
    timeframe: str = "1h",
) -> dict[str, FeatureRecord]:
    cat = FeatureCategory.STRUCTURAL
    out: dict[str, FeatureRecord] = {}

    hh = hl = lh = ll = False
    bos = choch = False
    sfp = False
    continuation = None
    trend = "neutral"

    if len(highs) >= 10 and len(lows) >= 10:
        sh, sl = _swings(highs, lows)
        if len(sh) >= 2:
            hh = highs[sh[-1]] > highs[sh[-2]]
            lh = highs[sh[-1]] < highs[sh[-2]]
        if len(sl) >= 2:
            hl = lows[sl[-1]] > lows[sl[-2]]
            ll = lows[sl[-1]] < lows[sl[-2]]
        if hh and hl:
            trend = "bull"
            continuation = True
        elif lh and ll:
            trend = "bear"
            continuation = True
        else:
            continuation = False
        # BOS: close breaks last swing high/low
        if sh and closes and closes[-1] > highs[sh[-1]]:
            bos = True
        if sl and closes and closes[-1] < lows[sl[-1]]:
            bos = True
        # CHoCH: structure flips vs prior trend
        if trend == "bull" and ll:
            choch = True
        if trend == "bear" and hh:
            choch = True
        # Swing failure: pierce then close back
        if sh and len(highs) > sh[-1] + 1 and closes:
            if max(highs[sh[-1] :]) > highs[sh[-1]] and closes[-1] < highs[sh[-1]]:
                sfp = True

    structure_quality = None
    if continuation is not None:
        structure_quality = normalize_probability(75 if continuation and not choch else (40 if bos else 55))
    trend_integrity = normalize_directional(1.0 if trend == "bull" else (-1.0 if trend == "bear" else 0.0), scale=1.0)
    reversal = normalize_probability(70 if choch or sfp else (30 if bos else 20))

    def add(name: str, value: Any, scale: FeatureScale = FeatureScale.RAW, parents: list[str] | None = None) -> None:
        out[name] = feat(
            name,
            None if value is None else (value if isinstance(value, (bool, str)) else round(float(value), 8)),
            cat,
            scale=scale,
            asset=asset,
            timeframe=timeframe,
            parents=parents or ["high", "low", "close"],
            source="market_structure",
        )

    add("higher_high", 1.0 if hh else 0.0, FeatureScale.RATIO)
    add("higher_low", 1.0 if hl else 0.0, FeatureScale.RATIO)
    add("lower_high", 1.0 if lh else 0.0, FeatureScale.RATIO)
    add("lower_low", 1.0 if ll else 0.0, FeatureScale.RATIO)
    add("bos", 1.0 if bos else 0.0, FeatureScale.RATIO)
    add("choch", 1.0 if choch else 0.0, FeatureScale.RATIO)
    add("swing_failure_pattern", 1.0 if sfp else 0.0, FeatureScale.RATIO)
    add("trend_continuation", 1.0 if continuation else (0.0 if continuation is False else None), FeatureScale.RATIO)
    add("trend_state", trend, FeatureScale.CATEGORICAL)
    add("structure_quality", structure_quality, FeatureScale.PROBABILITY)
    add("trend_integrity", trend_integrity, FeatureScale.DIRECTIONAL)
    add("reversal_probability", reversal, FeatureScale.PROBABILITY)
    return out
