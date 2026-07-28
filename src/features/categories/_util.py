"""Shared helpers for category feature builders."""

from __future__ import annotations

import math
from typing import Sequence

from src.features.contracts import FeatureCategory, FeatureLineage, FeatureRecord, FeatureScale


def last(values: Sequence[float | None]) -> float | None:
    for v in reversed(values):
        if v is not None:
            return float(v)
    return None


def safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def log_return(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return math.log(a / b)


def pct_return(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return (a - b) / b


def slope(values: Sequence[float | None], lookback: int = 5) -> float | None:
    pts = [float(v) for v in values[-lookback:] if v is not None]
    if len(pts) < 2:
        return None
    n = len(pts)
    xs = list(range(n))
    mean_x = (n - 1) / 2
    mean_y = sum(pts) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, pts))
    den = sum((x - mean_x) ** 2 for x in xs) or 1.0
    return num / den


def feat(
    name: str,
    value: float | str | None,
    category: FeatureCategory,
    *,
    scale: FeatureScale = FeatureScale.RAW,
    asset: str = "BTCUSDT",
    timeframe: str = "1h",
    parents: list[str] | None = None,
    source: str | None = None,
    confidence: float = 1.0,
    flagged_outlier: bool = False,
) -> FeatureRecord:
    missing = value is None
    return FeatureRecord(
        name=name,
        value=value,
        category=category.value,
        scale=scale.value,
        asset=asset,
        timeframe=timeframe,
        lineage=FeatureLineage(feature=name, parents=parents or [], source=source),
        missing=missing,
        confidence=0.0 if missing else confidence,
        flagged_outlier=flagged_outlier,
    )
