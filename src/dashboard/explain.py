"""Explainability panel builder (Ch.17 §17.11)."""

from __future__ import annotations

from typing import Any

from src.dashboard.contracts import ExplainabilityBlock


def build_explainability(
    *,
    market_bias: str,
    intelligence: dict[str, Any],
    scoring: dict[str, Any],
    risk: dict[str, Any],
    reasoning: dict[str, Any] | None = None,
) -> ExplainabilityBlock:
    bias = str(market_bias or "Neutral")
    question = f"Why {bias}?" if bias and bias != "Neutral" else "Why Neutral / wait?"

    bullets: list[dict[str, Any]] = []
    supporting = list((reasoning or {}).get("supporting_evidence") or [])
    for text in supporting[:5]:
        bullets.append({"ok": True, "text": str(text)})

    # Structured heuristics when reasoning sparse
    if intelligence.get("market_stress_index") in ("Low", "Moderate"):
        bullets.append({"ok": True, "text": f"Market stress {intelligence.get('market_stress_index')}"})
    elif intelligence.get("market_stress_index") in ("High", "Extreme"):
        bullets.append({"ok": False, "text": f"Elevated market stress ({intelligence.get('market_stress_index')})"})

    if intelligence.get("liquidity_state"):
        vacuum = "Vacuum" in str(intelligence.get("liquidity_state"))
        bullets.append(
            {
                "ok": not vacuum,
                "text": f"Liquidity: {intelligence.get('liquidity_state')}",
            }
        )

    agreement = ((scoring.get("details") or {}).get("confidence_meta") or {}).get("agreement_label")
    if agreement:
        bullets.append({"ok": "conflict" not in agreement.lower() and "Significant" not in agreement, "text": f"Layer agreement: {agreement}"})

    if risk.get("no_trade_zone"):
        bullets.append({"ok": False, "text": "No Trade Zone active — capital preservation"})
    elif risk.get("risk_level"):
        ok = str(risk.get("risk_level")) in ("Very Low", "Low", "Moderate")
        bullets.append({"ok": ok, "text": f"Execution risk: {risk.get('risk_level')} (CRS={risk.get('composite_risk_score')})"})

    conflicting = list((reasoning or {}).get("conflicting_evidence") or [])
    for text in conflicting[:3]:
        bullets.append({"ok": False, "text": str(text)})

    # Dedupe by text
    seen: set[str] = set()
    unique = []
    for b in bullets:
        t = b["text"]
        if t in seen:
            continue
        seen.add(t)
        unique.append(b)

    if not unique:
        unique = [{"ok": True, "text": "Insufficient structured evidence — inspect detailed layers."}]

    return ExplainabilityBlock(question=question, bullets=unique[:8])
