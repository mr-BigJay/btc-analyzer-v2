"""Market Stress Index — MSI (Ch.8 §8.13). Systemic risk, independent of direction."""

from __future__ import annotations

from typing import Any

from src.intelligence.contracts import StressLevel
from src.intelligence.helpers import all_tags, layer_map


def compute_msi(
    analysis: dict[str, Any],
    *,
    volatility_regime: str,
    liquidity_state: str,
    macro_bias: str,
    near_options_expiry: bool = False,
) -> tuple[str, float, list[str]]:
    """Return (level_label, numeric_score 0–100, drivers)."""
    tags = all_tags(analysis)
    layers = layer_map(analysis)
    score = 15.0
    drivers: list[str] = []

    if "Overcrowded Market" in tags:
        score += 15
        drivers.append("Funding / overcrowded positioning extremes")
    if "Long Squeeze Risk" in tags or "Short Squeeze Risk" in tags:
        score += 18
        drivers.append("Liquidation cascade risk")
    if volatility_regime in ("Elevated", "Extreme"):
        score += 12 if volatility_regime == "Elevated" else 22
        drivers.append(f"Volatility regime: {volatility_regime}")
    if liquidity_state in ("Liquidity Vacuum",):
        score += 14
        drivers.append("Liquidity imbalance / vacuum")
    elif liquidity_state == "Liquidity Both Sides" and "Sweep Probability" in tags:
        score += 8
        drivers.append("Two-sided liquidity with sweep probability")
    if analysis.get("conflicts"):
        score += 8
        drivers.append("Cross-layer conflict elevates uncertainty")
    if macro_bias in ("Cautious", "Risk-Off", "Uncertain"):
        score += 10
        drivers.append(f"Macro uncertainty ({macro_bias})")
    if near_options_expiry or "Gamma Pinning" in tags:
        score += 7
        drivers.append("Options expiration / gamma effects")

    fut = layers.get("Futures") or {}
    if float(fut.get("confidence") or 0) >= 75 and "Leveraged" in str(fut.get("tags") or []):
        score += 6
        drivers.append("High-conviction leveraged futures stance")

    oi_hint = str(fut.get("summary") or "").lower()
    if "concentrat" in oi_hint or "extreme" in oi_hint:
        score += 10
        drivers.append("Open interest concentration / extreme funding language")

    score = max(0.0, min(100.0, score))
    if score >= 80:
        level = StressLevel.EXTREME.value
    elif score >= 65:
        level = StressLevel.HIGH.value
    elif score >= 45:
        level = StressLevel.ELEVATED.value
    elif score >= 25:
        level = StressLevel.MODERATE.value
    else:
        level = StressLevel.LOW.value

    if not drivers:
        drivers.append("No elevated systemic stress drivers")
    return level, round(score, 1), drivers[:8]
