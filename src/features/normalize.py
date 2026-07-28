"""Feature value normalization (Ch.13 §13.14)."""

from __future__ import annotations

from typing import Any

from src.features.contracts import FeatureScale


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def normalize_directional(value: float | None, *, scale: float = 1.0) -> float | None:
    """Map roughly [-scale, +scale] into [-100, +100]."""
    if value is None:
        return None
    if scale <= 0:
        return 0.0
    return clamp(float(value) / scale * 100.0, -100.0, 100.0)


def normalize_probability(value: float | None) -> float | None:
    """Ensure 0..100 probability."""
    if value is None:
        return None
    v = float(value)
    if 0.0 <= v <= 1.0:
        v *= 100.0
    return clamp(v, 0.0, 100.0)


def normalize_ratio(value: float | None) -> float | None:
    if value is None:
        return None
    return clamp(float(value), 0.0, 1.0)


def apply_scale(value: float | None, scale: str) -> float | None:
    if value is None:
        return None
    if scale == FeatureScale.DIRECTIONAL.value:
        return clamp(float(value), -100.0, 100.0)
    if scale == FeatureScale.PROBABILITY.value:
        return normalize_probability(value)
    if scale == FeatureScale.RATIO.value:
        return normalize_ratio(value)
    return float(value)


def encode_categorical(value: Any) -> float | None:
    """Simple deterministic encoding for categorical states."""
    if value is None:
        return None
    mapping = {
        "bull": 1.0,
        "bullish": 1.0,
        "bear": -1.0,
        "bearish": -1.0,
        "neutral": 0.0,
        "range": 0.0,
        "expanding": 1.0,
        "compressing": -1.0,
        "high": 1.0,
        "low": -1.0,
        "up": 1.0,
        "down": -1.0,
    }
    key = str(value).strip().lower()
    if key in mapping:
        return mapping[key]
    # Stable hash-ish fold into [-1, 1] without randomness
    acc = sum(ord(c) for c in key) % 201
    return (acc - 100) / 100.0
