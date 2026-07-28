"""Composite Risk Score aggregation (Ch.15 §15.5)."""

from __future__ import annotations

from typing import Any

from src.risk.contracts import CategoryScore, crs_to_level

# Deterministic weights — must sum to 1.0
CATEGORY_WEIGHTS: dict[str, float] = {
    "market": 0.20,
    "liquidity": 0.15,
    "volatility": 0.18,
    "leverage": 0.15,
    "event": 0.12,
    "data": 0.12,
    "execution": 0.08,
}


def composite_risk_score(categories: dict[str, CategoryScore]) -> tuple[float, str, dict[str, float]]:
    assert abs(sum(CATEGORY_WEIGHTS.values()) - 1.0) < 1e-9
    acc = 0.0
    parts: dict[str, float] = {}
    for name, weight in CATEGORY_WEIGHTS.items():
        cat = categories.get(name)
        score = float(cat.score) if cat else 40.0
        parts[name] = round(score, 2)
        acc += score * weight
    crs = round(max(0.0, min(100.0, acc)), 1)
    return crs, crs_to_level(crs), parts
