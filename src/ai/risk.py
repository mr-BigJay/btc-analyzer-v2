"""Independent risk assessment (Ch.7 §7.11) — MSI-aware via Ch.8."""

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
    intelligence: dict[str, Any] | None = None,
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

    intel = intelligence or {}
    msi = str(intel.get("market_stress_index") or "")
    if msi == "Extreme":
        score += 4
        drivers.append("Market Stress Index: Extreme")
    elif msi == "High":
        score += 3
        drivers.append("Market Stress Index: High")
    elif msi == "Elevated":
        score += 2
        drivers.append("Market Stress Index: Elevated")
    if float(intel.get("transition_probability") or 0) >= 60:
        score += 1
        drivers.append("Elevated regime transition probability")
    if intel.get("macro_bias") in ("Cautious", "Risk-Off", "Uncertain"):
        score += 1
        drivers.append(f"Macro bias {intel.get('macro_bias')}")

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

    # MSI can escalate the label even when directional bias is favorable (Ch.8 §8.13)
    msi_map = {
        "Extreme": RiskCategory.EXTREME.value,
        "High": RiskCategory.HIGH.value,
        "Elevated": RiskCategory.ELEVATED.value,
    }
    if msi in msi_map:
        order = [
            RiskCategory.LOW.value,
            RiskCategory.MODERATE.value,
            RiskCategory.ELEVATED.value,
            RiskCategory.HIGH.value,
            RiskCategory.EXTREME.value,
        ]
        if order.index(msi_map[msi]) > order.index(level):
            level = msi_map[msi]

    if not drivers:
        drivers.append("No elevated structural risk drivers detected")

    explanation = (
        f"Risk assessed as {level} based on {len(drivers)} driver(s): "
        + "; ".join(drivers[:5])
        + ". Risk is evaluated independently of directional bias"
        + (f"; MSI={msi}" if msi else "")
        + "."
    )
    return level, drivers[:8], explanation
