"""Market Health Index — MHI 0–100 (Ch.8 §8.12). Quality, not direction."""

from __future__ import annotations

from typing import Any

from src.intelligence.contracts import health_band
from src.intelligence.helpers import layer_map, signed


def compute_mhi(
    analysis: dict[str, Any],
    *,
    volatility_regime: str,
    liquidity_state: str,
    macro_bias: str,
    data_completeness: float,
) -> tuple[float, str, dict[str, float]]:
    layers = layer_map(analysis)
    components: dict[str, float] = {}

    spot = layers.get("Spot") or {}
    futures = layers.get("Futures") or {}
    options = layers.get("Options") or {}
    structure = layers.get("Market Structure") or {}
    liquidity = layers.get("Liquidity") or {}
    volatility = layers.get("Volatility") or {}

    # Spot strength (quality of participation, not just direction)
    components["spot_strength"] = _quality(spot) * 100

    # Futures stability — penalize squeeze/overcrowd tags
    fut_q = _quality(futures)
    fut_tags = set(futures.get("tags") or [])
    if "Overcrowded Market" in fut_tags or "Long Squeeze Risk" in fut_tags or "Short Squeeze Risk" in fut_tags:
        fut_q *= 0.7
    components["futures_stability"] = fut_q * 100

    # Options sentiment clarity
    components["options_sentiment"] = _quality(options) * 100

    # Market structure clarity
    struct_q = _quality(structure)
    if abs(signed(str(structure.get("signal") or ""))) > 0.4:
        struct_q = min(1.0, struct_q + 0.1)
    components["market_structure"] = struct_q * 100

    # Liquidity quality
    liq_q = float(liquidity.get("data_quality") or 0.5)
    if liquidity_state == "Liquidity Vacuum":
        liq_q *= 0.5
    elif liquidity_state == "Balanced":
        liq_q = min(1.0, liq_q + 0.1)
    components["liquidity_quality"] = liq_q * 100

    # Volatility — mid regimes healthier than extremes for "quality"
    vol_map = {"Very Low": 55, "Low": 70, "Normal": 80, "Elevated": 55, "Extreme": 30}
    components["volatility"] = float(vol_map.get(volatility_regime, 60))
    _ = volatility

    # Macro conditions
    macro_map = {"Neutral": 65, "Supportive": 80, "Risk-On": 75, "Cautious": 45, "Risk-Off": 35, "Uncertain": 40}
    components["macro_conditions"] = float(macro_map.get(macro_bias, 55))

    weights = {
        "spot_strength": 0.18,
        "futures_stability": 0.15,
        "options_sentiment": 0.12,
        "market_structure": 0.18,
        "liquidity_quality": 0.12,
        "volatility": 0.12,
        "macro_conditions": 0.13,
    }
    score = sum(components[k] * weights[k] for k in weights)
    score *= 0.7 + 0.3 * max(0.2, min(1.0, data_completeness))
    if analysis.get("conflicts"):
        score *= 0.92
    score = max(0.0, min(100.0, score))
    return round(score, 1), health_band(score).value, {k: round(v, 1) for k, v in components.items()}


def _quality(layer: dict[str, Any]) -> float:
    if not layer:
        return 0.4
    dq = float(layer.get("data_quality") if layer.get("data_quality") is not None else 0.7)
    conf = float(layer.get("confidence") or 50) / 100.0
    # Neutral high-confidence can still be "healthy" market quality
    return max(0.15, min(1.0, 0.55 * dq + 0.45 * conf))
