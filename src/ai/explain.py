"""Explainability helpers — confidence calibration + conflict narrative (Ch.7 §7.9–§7.12)."""

from __future__ import annotations

from typing import Any

from src.ai.contracts import ConfidenceBand, EvidenceItem, ReasoningBlock, ScenarioAssessment, confidence_band
from src.analysis.contracts import MarketAnalysisOutput, SignalBias


def calibrate_confidence(
    analysis: MarketAnalysisOutput | dict[str, Any],
    evidence: list[EvidenceItem],
    scenarios: list[ScenarioAssessment],
) -> tuple[float, str, str]:
    """Return (confidence, band_label, explanation). High confidence ≠ guaranteed outcome."""
    if isinstance(analysis, MarketAnalysisOutput):
        base = float(analysis.confidence)
        conflicts = list(analysis.conflicts or [])
        mtf = analysis.timeframe_alignment or {}
        layer_results = analysis.layer_results
    else:
        base = float(analysis.get("confidence") or 50)
        conflicts = list(analysis.get("conflicts") or [])
        mtf = dict(analysis.get("timeframe_alignment") or {})
        layer_results = list(analysis.get("layer_results") or [])

    signals = [str(r.get("signal")) for r in layer_results]
    directional = [s for s in signals if s not in (SignalBias.NEUTRAL.value, SignalBias.HIGH_UNCERTAINTY.value)]
    agreement = 0.0
    if directional:
        bull = sum(1 for s in directional if "Bullish" in s)
        bear = sum(1 for s in directional if "Bearish" in s)
        agreement = max(bull, bear) / max(1, len(directional))

    avg_quality = sum(e.data_quality for e in evidence) / max(1, len(evidence))
    top_gap = 0.0
    if len(scenarios) >= 2:
        top_gap = abs(scenarios[0].probability - scenarios[1].probability) / 100.0

    conf = base
    conf = 0.55 * conf + 0.25 * (agreement * 100) + 0.12 * (avg_quality * 100) + 0.08 * (top_gap * 100)

    if conflicts:
        conf *= 0.85
    if mtf.get("divergent"):
        conf *= 0.9
    elif mtf.get("aligned"):
        conf = min(100.0, conf + 4)

    # Options + Futures confirmation boost
    layers_ok = {e.layer: e for e in evidence}
    fut = layers_ok.get("Futures")
    opt = layers_ok.get("Options")
    if fut and opt and "Bullish" in fut.signal and "Bullish" in opt.signal:
        conf = min(100.0, conf + 3)
    if fut and opt and "Bearish" in fut.signal and "Bearish" in opt.signal:
        conf = min(100.0, conf + 3)

    # Never claim impossible certainty
    conf = max(20.0, min(92.0, conf))

    band = confidence_band(conf)
    parts = [
        f"Calibrated confidence {conf:.0f}/100 ({band.value}).",
        f"Layer agreement ≈ {agreement:.0%}; average data quality {avg_quality:.0%}.",
    ]
    if conflicts:
        parts.append("Conflicts present — confidence reduced.")
    if mtf.get("aligned"):
        parts.append("Multi-timeframe biases aligned.")
    elif mtf.get("divergent"):
        parts.append("Multi-timeframe divergence detected.")
    parts.append("High confidence does not imply a guaranteed outcome.")
    return round(conf, 1), band.value, " ".join(parts)


def build_reasoning(
    *,
    market_bias: str,
    primary_narrative: str,
    confidence: float,
    confidence_explanation: str,
    evidence: list[EvidenceItem],
    conflicts: list[str],
    risk_explanation: str,
    scenarios: list[ScenarioAssessment],
) -> ReasoningBlock:
    supporting = [f"[{e.layer}] {e.evidence}" for e in evidence if _supports(e.signal, market_bias)]
    conflicting = [f"[{e.layer}] {e.evidence}" for e in evidence if _conflicts(e.signal, market_bias)]
    if not supporting:
        supporting = [f"[{e.layer}] {e.evidence}" for e in evidence[:3]]

    conflict_narrative = explain_conflicts(evidence, conflicts)
    primary = scenarios[0] if scenarios else None
    conclusion = (
        f"Primary narrative is '{primary_narrative}' with market bias '{market_bias}'. "
        f"Leading scenario: {primary.name if primary else 'n/a'} "
        f"({primary.probability if primary else 0:.0f}% evidence weight)."
    )

    uncertainty = ""
    if confidence < 60 or market_bias == SignalBias.HIGH_UNCERTAINTY.value:
        uncertainty = (
            "Evidence is insufficient for a high-conviction stance — uncertainty is elevated. "
            "Prefer defense, smaller size, or no-trade until confirmation improves."
        )

    return ReasoningBlock(
        primary_conclusion=conclusion,
        supporting_evidence=supporting[:6],
        conflicting_evidence=conflicting[:6],
        confidence_explanation=confidence_explanation,
        risk_explanation=risk_explanation,
        conflict_narrative=conflict_narrative,
        uncertainty_note=uncertainty,
    )


def explain_conflicts(evidence: list[EvidenceItem], conflicts: list[str]) -> str:
    """Transparent conflict explanation (Ch.7 §7.10) — never hide contradictions."""
    bull = [e for e in evidence if "Bullish" in e.signal]
    bear = [e for e in evidence if "Bearish" in e.signal]
    if not (bull and bear) and not conflicts:
        return "No material contradictory clusters detected across analytical layers."

    bull_txt = ", ".join(f"{e.layer} ({e.signal})" for e in bull[:3]) or "none"
    bear_txt = ", ".join(f"{e.layer} ({e.signal})" for e in bear[:3]) or "none"
    return (
        f"Conflicting evidence is present. Constructive side: {bull_txt}. "
        f"Pressured side: {bear_txt}. "
        "Rather than averaging blindly, the engine preserves both clusters, "
        "reduces confidence, and ranks scenarios probabilistically."
    )


def _supports(signal: str, bias: str) -> bool:
    if "Bullish" in bias:
        return "Bullish" in signal
    if "Bearish" in bias:
        return "Bearish" in signal
    return signal == SignalBias.NEUTRAL.value


def _conflicts(signal: str, bias: str) -> bool:
    if "Bullish" in bias:
        return "Bearish" in signal
    if "Bearish" in bias:
        return "Bullish" in signal
    return signal in (SignalBias.BULLISH.value, SignalBias.BEARISH.value)
