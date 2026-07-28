"""Governance engine (Ch.23)."""

from __future__ import annotations

from typing import Any

from src.governance.ai_policy import (
    ai_governance_status,
    evaluate_model_drift,
    explainability_policy,
    human_in_the_loop_policy,
    model_evolution_catalog,
    validate_ai_conclusion,
)
from src.governance.catalog import build_governance_object, governance_catalog
from src.governance.contracts import PromptRecord
from src.governance.prompts import prompt_registry
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
    tech_debt_registry,
    tech_debt_status,
)


class GovernanceEngine:
    def status(self) -> dict[str, Any]:
        return governance_catalog()

    def governance_object(self, **kwargs: Any) -> dict[str, Any]:
        return build_governance_object(**kwargs).to_dict()

    def roadmap(self) -> dict[str, Any]:
        return roadmap_view()

    def plugins(self) -> dict[str, Any]:
        return plugin_architecture()

    def assets(self) -> dict[str, Any]:
        return asset_expansion()

    def ai(self) -> dict[str, Any]:
        return {
            "governance": ai_governance_status(),
            "explainability": explainability_policy(),
            "human_in_the_loop": human_in_the_loop_policy(),
            "model_evolution": model_evolution_catalog(),
        }

    def prompts(self) -> dict[str, Any]:
        return {"prompts": prompt_registry.list(), "count": len(prompt_registry.list())}

    def register_prompt(self, **kwargs: Any) -> dict[str, Any]:
        record = PromptRecord(**kwargs)
        # Human-in-the-loop: new versions flagged for review
        needs_review = prompt_registry.requires_human_review(record.prompt_id, record.version)
        saved = prompt_registry.register(record)
        return {"prompt": saved, "human_review_required": needs_review or record.status != "active"}

    def drift(self, **kwargs: Any) -> dict[str, Any]:
        return evaluate_model_drift(**kwargs)

    def explainability_check(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return validate_ai_conclusion(payload)

    def maturity(self, **kwargs: Any) -> dict[str, Any]:
        return maturity_status(**kwargs)

    def lifecycle(self) -> dict[str, Any]:
        return governance_lifecycle()

    def knowledge(self) -> dict[str, Any]:
        return knowledge_base_catalog()

    def feedback(self) -> dict[str, Any]:
        return feedback_loop()

    def documentation(self) -> dict[str, Any]:
        return documentation_policy()

    def tech_debt(self) -> dict[str, Any]:
        return tech_debt_status()

    def record_debt(self, **kwargs: Any) -> dict[str, Any]:
        return tech_debt_registry.record(**kwargs)

    def success_metrics(self) -> dict[str, Any]:
        return success_metrics()

    def architecture(self) -> dict[str, Any]:
        return architectural_statement()
