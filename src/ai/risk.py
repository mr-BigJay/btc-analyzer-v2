"""Independent risk assessment (Ch.7 §7.11) — separate from market direction."""

from __future__ import annotations

from typing import Any

from src.ai.contracts import EvidenceItem, RiskCategory
from src.analysis.contracts import MarketAnalysisOutput


def assess_risk(
    analysis: MarketAnalysisOutput | dict[str, Any],
    evidence: list[EvidenceItem],
    *,
    near_options_expiry: bool = False,
    macro_event: bool = False,
) -> tuple[str, list[str], str]:
    """Return (risk_level, major_risks, risk_explanation)."""
    if isinstance(analysis, MarketAnalysisOutput):
        volatility = analysis.volatility
        confidence = float(analysis.confidence)
        conflicts = list(analysis.conflicts or [])
        tags = {t for r in analysis.layer_results for t in (r.get("tags") or [])}
        layer_map = {r.get("layer"): r for r in analysis.layer_results}
    else:
        volatility = str(analysis.get("volatility") or "Medium")
        confidence = float(analysis.get("confidence") or 50)
        conflicts = list(analysis.get("conflicts") or [])
        tags = set()
        layer_map = {}
        for r in analysis.get("layer_results") or []:
            tags.update(r.get("tags") or [])
            layer_map[r.get("layer")] = r

    score = 0
    drivers: list[str] = []

    if "Overcrowded Market" in tags or "Long Squeeze Risk" in tags or "Short Squeeze Risk" in tags:
        score += 2
        drivers.append("Crowded leveraged positioning")
    if "High Volatility" in tags or volatility == "High" or "Expansion" in tags:
        score += 2
        drivers.append("Volatility expansion")
    if conflicts:
        score += 1
        drivers.append("Contradictory cross-layer evidence")
    if confidence < 45:
        score += 1
        drivers.append("Low evidence confidence / incomplete agreement")

    futures = layer_map.get("Futures") or {}
    fut_summary = str(futures.get("summary") or "").lower()
    if "funding" in fut_summary and ("extreme" in fut_summary or "imbalance" in fut_summary):
        score += 1
        drivers.append("Funding imbalance")

    liquidity = layer_map.get("Liquidity") or {}
    if float(liquidity.get("data_quality") or 1) < 0.4:
        score += 1
        drivers.append("Thin / low-quality liquidity map")
    if "Sweep Probability" in tags:
        score += 1
        drivers.append("Nearby stop-cluster / liquidity sweep risk")

    if near_options_expiry or "Gamma Pinning" in tags:
        score += 1
        drivers.append("Options expiration / gamma pinning effects")
    if macro_event:
        score += 2
        drivers.append("Major macro event window")

    if "Leveraged Bullish" in tags and "Leveraged Bearish" in tags:
        score += 1
        drivers.append("Two-sided excessive leverage")

    # evidence unused for score but kept for API symmetry / future learning
    _ = evidence

    if score >= 7:
        level = RiskCategory.EXTREME.value
    elif score >= 5:
        level = RiskCategory.HIGH.value
    elif score >= 3:
        level = RiskCategory.ELEVATED.value
    elif score >= 1:
        level = RiskCategory.MODERATE.value
    else:
        level = RiskCategory.LOW.value

    if not drivers:
        drivers.append("No elevated structural risk drivers detected")

    explanation = (
        f"Risk assessed as {level} based on {len(drivers)} driver(s): "
        + "; ".join(drivers[:5])
        + ". Risk is evaluated independently of directional bias."
    )
    return level, drivers[:8], explanation
