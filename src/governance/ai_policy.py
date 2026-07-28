"""AI governance, explainability, and drift monitoring (Ch.23 §23.7–23.12)."""

from __future__ import annotations

from typing import Any

from src.ai.learning import list_forecasts
from src.governance.contracts import (
    AI_GOVERNANCE_REQUIREMENTS,
    DRIFT_SIGNALS,
    EXPLAINABILITY_REQUIREMENTS,
    HUMAN_IN_THE_LOOP_ACTIONS,
    MODEL_EVOLUTION,
    utc_now_iso,
)
from src.governance.prompts import prompt_registry
from src.observability.metrics import app_metrics


def ai_governance_status() -> dict[str, Any]:
    return {
        "requirements": AI_GOVERNANCE_REQUIREMENTS,
        "ai_recommendations": "advisory",
        "autonomous_execution": False,
        "prompt_registry": prompt_registry.list(),
        "model_configuration_versioned": True,
        "deterministic_output_structure": True,
        "continuous_validation": True,
        "timestamp": utc_now_iso(),
    }


def explainability_policy() -> dict[str, Any]:
    return {
        "required_elements": EXPLAINABILITY_REQUIREMENTS,
        "unsupported_conclusions": "forbidden",
        "reasoning_block_required": True,
        "contract": "src.ai.contracts.ReasoningBlock",
        "timestamp": utc_now_iso(),
    }


def human_in_the_loop_policy() -> dict[str, Any]:
    return {
        "required_for": HUMAN_IN_THE_LOOP_ACTIONS,
        "protects": "analytical quality",
        "bypass_allowed": False,
        "timestamp": utc_now_iso(),
    }


def model_evolution_catalog() -> dict[str, Any]:
    return {
        "future_upgrades": MODEL_EVOLUTION,
        "compatibility_rule": "Model replacement must preserve external API compatibility whenever possible",
        "timestamp": utc_now_iso(),
    }


def evaluate_model_drift(*, confidence_samples: list[float] | None = None) -> dict[str, Any]:
    """Lightweight drift signals from forecasts + confidence distribution."""
    forecasts = list_forecasts(limit=50)
    confidences = confidence_samples or [
        float(f.get("confidence")) for f in forecasts if f.get("confidence") is not None
    ]
    findings: list[dict[str, Any]] = []
    if len(confidences) >= 5:
        avg = sum(confidences) / len(confidences)
        # Simple dispersion check
        var = sum((c - avg) ** 2 for c in confidences) / len(confidences)
        if var > 400:  # std ~20
            findings.append(
                {
                    "signal": "Confidence distribution changes",
                    "detail": f"variance={round(var, 2)} mean={round(avg, 2)}",
                    "severity": "warning",
                }
            )
        if avg < 40 or avg > 90:
            findings.append(
                {
                    "signal": "Output consistency",
                    "detail": f"mean_confidence={round(avg, 2)} outside expected band",
                    "severity": "warning",
                }
            )

    snap = app_metrics.snapshot()
    if snap.get("ai_inference_time_ms", 0) >= 5000:
        findings.append(
            {
                "signal": "Validation failures",
                "detail": "elevated AI inference latency may indicate degraded path",
                "severity": "info",
            }
        )

    return {
        "monitored": DRIFT_SIGNALS,
        "forecasts_reviewed": len(forecasts),
        "confidence_samples": len(confidences),
        "findings": findings,
        "investigation_required": len(findings) > 0,
        "timestamp": utc_now_iso(),
    }


def validate_ai_conclusion(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Ensure an AI conclusion carries explainability elements (Ch.23 §23.9)."""
    payload = payload or {}
    missing = []
    reasoning = payload.get("reasoning") or payload.get("explainability") or {}
    if isinstance(reasoning, dict):
        evidence = reasoning.get("supporting_evidence") or payload.get("supporting_evidence")
        if not evidence:
            missing.append("Supporting evidence")
        if not (reasoning.get("confidence_explanation") or payload.get("confidence_rationale")):
            missing.append("Confidence rationale")
        if not (reasoning.get("alternative_scenarios") or payload.get("scenarios")):
            missing.append("Alternative scenarios")
    else:
        missing.extend(["Supporting evidence", "Confidence rationale", "Alternative scenarios"])

    indicators = payload.get("influential_indicators")
    if not indicators and isinstance(reasoning, dict):
        indicators = reasoning.get("influential_indicators")
    if not indicators and not payload.get("layer_scores"):
        missing.append("Influential indicators")
    if payload.get("layer_agreement") is None and not payload.get("conflicts"):
        # soft: layer agreement can be derived
        pass

    return {
        "ok": len(missing) == 0,
        "missing": missing,
        "required": EXPLAINABILITY_REQUIREMENTS,
        "timestamp": utc_now_iso(),
    }
