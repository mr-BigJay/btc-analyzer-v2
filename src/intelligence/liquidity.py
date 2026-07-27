"""Liquidity intelligence (Ch.8 §8.7)."""

from __future__ import annotations

from typing import Any

from src.intelligence.helpers import all_tags, layer_map


def classify_liquidity(analysis: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    layers = layer_map(analysis)
    tags = all_tags(analysis)
    liq = layers.get("Liquidity") or {}
    details = dict(liq.get("details") or {})
    summary = str(liq.get("summary") or "")

    above = bool(details.get("liquidity_above") or "Liquidity Above" in tags or "above" in summary.lower())
    below = bool(details.get("liquidity_below") or "Liquidity Below" in tags or "below" in summary.lower())
    sweep = "Sweep Probability" in tags or bool(details.get("sweep_probability"))
    magnet = "Magnet Zones" in tags or bool(details.get("magnet_zones"))
    vacuum = "Liquidity Vacuum" in tags or bool(details.get("vacuum"))

    if vacuum:
        state = "Liquidity Vacuum"
    elif above and not below:
        state = "Liquidity Above"
    elif below and not above:
        state = "Liquidity Below"
    elif above and below:
        state = "Liquidity Both Sides"
    elif magnet:
        state = "Magnet Zone"
    else:
        state = "Balanced"

    meta = {
        "liquidity_above": details.get("liquidity_above"),
        "liquidity_below": details.get("liquidity_below"),
        "sweep_probability": sweep or details.get("sweep_probability"),
        "magnet_zones": details.get("magnet_zones"),
        "equal_highs": details.get("equal_highs"),
        "equal_lows": details.get("equal_lows"),
        "order_blocks": details.get("order_blocks"),
        "fair_value_gaps": details.get("fair_value_gaps"),
        "summary": summary,
    }
    return state, meta
