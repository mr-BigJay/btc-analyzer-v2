"""Volatility regime classification (Ch.8 §8.9)."""

from __future__ import annotations

from typing import Any

from src.intelligence.contracts import VolatilityRegime
from src.intelligence.helpers import all_tags, layer_map


def classify_volatility(analysis: dict[str, Any]) -> str:
    tags = all_tags(analysis)
    vol_label = str(analysis.get("volatility") or "Medium")
    vol_layer = layer_map(analysis).get("Volatility") or {}
    details = vol_layer.get("details") or {}
    iv_rank = details.get("iv_rank")
    atr_pct = details.get("atr_pct")

    if "Compression" in tags or vol_label == "Low":
        if iv_rank is not None and float(iv_rank) < 20:
            return VolatilityRegime.VERY_LOW.value
        return VolatilityRegime.LOW.value
    if "Expansion" in tags or "High Volatility" in tags or vol_label == "High":
        if atr_pct is not None and float(atr_pct) > 5:
            return VolatilityRegime.EXTREME.value
        if "Extreme" in str(vol_layer.get("summary") or ""):
            return VolatilityRegime.EXTREME.value
        return VolatilityRegime.ELEVATED.value
    if vol_label == "Medium":
        return VolatilityRegime.NORMAL.value
    return VolatilityRegime.NORMAL.value
