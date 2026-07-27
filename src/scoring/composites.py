"""Composite scores + decision matrix (Ch.9 §9.7–§9.8)."""

from __future__ import annotations

from typing import Any

# Decision matrix weights (must sum to 1.0)
MATRIX_WEIGHTS: dict[str, float] = {
    "market_bias_score": 0.40,
    "confidence_score": 0.25,
    "risk_score": 0.15,
    "market_health_index": 0.10,
    "market_stress_index": 0.10,
}


def market_bias_score(layer_scores: dict[str, float], weights: dict[str, float]) -> float:
    """Weighted directional bias in [-100, +100] (Ch.9 §9.7 MBS)."""
    total_w = 0.0
    acc = 0.0
    for layer, score in layer_scores.items():
        w = float(weights.get(layer, 0.0))
        acc += score * w
        total_w += w
    if total_w <= 0:
        return 0.0
    return round(max(-100.0, min(100.0, acc / total_w)), 2)


def risk_score_from_inputs(
    *,
    intelligence: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
    near_options_expiry: bool = False,
    macro_event: bool = False,
) -> float:
    """Execution risk 0–100 — higher is riskier (Ch.9 §9.7 / §9.11)."""
    intel = intelligence or {}
    analysis = analysis or {}
    score = float(intel.get("market_stress_score") or 0)
    if score <= 0:
        # Derive from MSI label if numeric missing
        msi = str(intel.get("market_stress_index") or "Moderate")
        score = {"Low": 18, "Moderate": 40, "Elevated": 58, "High": 75, "Extreme": 90}.get(msi, 40)

    tags = set()
    for row in analysis.get("layer_results") or []:
        tags.update(row.get("tags") or [])

    if "Overcrowded Market" in tags or "Long Squeeze Risk" in tags or "Short Squeeze Risk" in tags:
        score += 8
    if near_options_expiry or "Gamma Pinning" in tags:
        score += 6
    if macro_event or intel.get("macro_bias") in ("Cautious", "Risk-Off", "Uncertain"):
        score += 8
    vol = str(intel.get("volatility_regime") or analysis.get("volatility") or "")
    if vol in ("Elevated", "Extreme", "High"):
        score += 10
    if intel.get("liquidity_state") == "Liquidity Vacuum":
        score += 10
    if analysis.get("conflicts"):
        score += 5

    return round(max(0.0, min(100.0, score)), 1)


def decision_matrix_score(
    *,
    mbs: float,
    confidence: float,
    risk: float,
    mhi: float,
    msi: float,
) -> tuple[float, dict[str, float]]:
    """
    Combine composites (Ch.9 §9.8).

    Directional contribution uses MBS mapped to 0–100 via (mbs+100)/2.
    Risk and MSI enter as inverted quality (high risk/stress reduces matrix score).
    """
    directional = (float(mbs) + 100.0) / 2.0
    risk_quality = 100.0 - float(risk)
    stress_quality = 100.0 - float(msi)

    components = {
        "market_bias_score": directional,
        "confidence_score": float(confidence),
        "risk_score": risk_quality,
        "market_health_index": float(mhi),
        "market_stress_index": stress_quality,
    }
    # Verify weights sum
    assert abs(sum(MATRIX_WEIGHTS.values()) - 1.0) < 1e-9
    score = sum(components[k] * MATRIX_WEIGHTS[k] for k in MATRIX_WEIGHTS)
    return round(score, 2), {k: round(v, 2) for k, v in components.items()}
