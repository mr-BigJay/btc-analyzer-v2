"""Deterministic natural-language generation (Ch.7 §7.3 / §7.12).

Template-based so identical inputs → identical prose (Ch.7 §7.15 / §7.18).
No external LLM required for the core engine.
"""

from __future__ import annotations

from typing import Any

from src.ai.contracts import EvidenceItem, ReasoningBlock, ScenarioAssessment


def layer_blurb(layer_results: list[dict[str, Any]], name: str, *, fallback: str) -> str:
    for row in layer_results:
        if row.get("layer") == name:
            signal = row.get("signal", "Neutral")
            conf = row.get("confidence", 50)
            summary = row.get("summary") or ""
            return f"{name}: {signal} (confidence {conf:.0f}). {summary}".strip()
    return fallback


def executive_summary(
    *,
    bias: str,
    narrative: str,
    confidence: float,
    risk_level: str,
    primary: ScenarioAssessment | None,
    reasoning: ReasoningBlock,
) -> str:
    lead = (
        f"Market bias is {bias} under the dominant narrative '{narrative}'. "
        f"Calibrated confidence is {confidence:.0f}/100 with risk marked {risk_level}."
    )
    if primary:
        lead += f" Primary scenario: {primary.name} at {primary.probability:.0f}% evidence weight."
    if reasoning.uncertainty_note:
        lead += " " + reasoning.uncertainty_note
    else:
        lead += " This is an evidence-weighted assessment — not a price guarantee."
    return lead


def final_assessment(
    *,
    bias: str,
    narrative: str,
    scenarios: list[ScenarioAssessment],
    risk_level: str,
    key_drivers: list[str],
) -> str:
    alts = ", ".join(f"{s.name} ({s.probability:.0f}%)" for s in scenarios[1:3])
    drivers = "; ".join(key_drivers[:4]) if key_drivers else "mixed evidence"
    return (
        f"Final assessment: {bias} bias framed by '{narrative}'. "
        f"Watch alternative paths: {alts or 'n/a'}. "
        f"Key drivers: {drivers}. Risk posture: {risk_level}. "
        "Invalidate quickly if conflicting leverage and spot flows intensify."
    )


def key_drivers_from_evidence(evidence: list[EvidenceItem], narrative_bullets: list[str]) -> list[str]:
    drivers = [f"{e.layer}: {e.evidence}" for e in evidence[:5]]
    for b in narrative_bullets:
        if b not in drivers:
            drivers.append(b)
    return drivers[:8]


def liquidity_zone_lines(layer_results: list[dict[str, Any]]) -> list[str]:
    for row in layer_results:
        if row.get("layer") == "Liquidity":
            details = row.get("details") or {}
            lines = []
            for key in ("liquidity_above", "liquidity_below", "magnet_zones", "equal_highs", "equal_lows"):
                val = details.get(key)
                if val:
                    lines.append(f"{key.replace('_', ' ').title()}: {val}")
            if row.get("summary"):
                lines.insert(0, str(row["summary"]))
            return lines[:6] or [str(row.get("summary") or "Liquidity map unavailable")]
    return ["Liquidity map unavailable from Analysis Engine"]
