"""Governance catalog (Ch.23)."""

from __future__ import annotations

from typing import Any

from src.governance.ai_policy import (
    ai_governance_status,
    evaluate_model_drift,
    explainability_policy,
    human_in_the_loop_policy,
    model_evolution_catalog,
)
from src.governance.contracts import (
    GOVERNANCE_ENGINE_VERSION,
    GOVERNANCE_SCHEMA_VERSION,
    GovernanceObject,
)
from src.governance.roadmap import (
    architectural_statement,
    asset_expansion,
    documentation_policy,
    feedback_loop,
    governance_lifecycle,
    knowledge_base_catalog,
    maturity_status,
    plugin_architecture,
    roadmap_view,
    success_metrics,
    tech_debt_status,
)


def build_governance_object(**kwargs: Any) -> GovernanceObject:
    return GovernanceObject(**kwargs)


def governance_catalog() -> dict[str, Any]:
    return {
        "schema_version": GOVERNANCE_SCHEMA_VERSION,
        "engine_version": GOVERNANCE_ENGINE_VERSION,
        "purpose": (
            "Long-term evolution strategy, governance principles, and architectural roadmap "
            "preserving analytical consistency, stability, explainability, and compatibility."
        ),
        "governance_object": build_governance_object().to_dict(),
        "roadmap": roadmap_view(),
        "plugins": plugin_architecture(),
        "assets": asset_expansion(),
        "ai_governance": ai_governance_status(),
        "explainability": explainability_policy(),
        "human_in_the_loop": human_in_the_loop_policy(),
        "model_evolution": model_evolution_catalog(),
        "drift": evaluate_model_drift(),
        "knowledge": knowledge_base_catalog(),
        "feedback": feedback_loop(),
        "lifecycle": governance_lifecycle(),
        "documentation": documentation_policy(),
        "tech_debt": tech_debt_status(),
        "success_metrics": success_metrics(),
        "maturity": maturity_status(),
        "architecture": architectural_statement(),
        "book_complete": True,
        "chapters": 23,
        "endpoints": [
            "/api/v1/governance/status",
            "/api/v1/governance/object",
            "/api/v1/governance/roadmap",
            "/api/v1/governance/prompts",
            "/api/v1/governance/ai",
            "/api/v1/governance/drift",
            "/api/v1/governance/maturity",
            "/api/v1/governance/lifecycle",
        ],
    }
