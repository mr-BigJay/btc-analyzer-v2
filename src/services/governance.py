"""Governance service facade (Ch.23)."""

from __future__ import annotations

from typing import Any

from src.governance.engine import GovernanceEngine


class GovernanceService:
    def __init__(self) -> None:
        self.engine = GovernanceEngine()

    def status(self) -> dict[str, Any]:
        return self.engine.status()

    def governance_object(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.governance_object(**kwargs)

    def roadmap(self) -> dict[str, Any]:
        return self.engine.roadmap()

    def prompts(self) -> dict[str, Any]:
        return self.engine.prompts()

    def ai(self) -> dict[str, Any]:
        return self.engine.ai()

    def drift(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.drift(**kwargs)

    def maturity(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.maturity(**kwargs)

    def lifecycle(self) -> dict[str, Any]:
        return self.engine.lifecycle()

    def architecture(self) -> dict[str, Any]:
        return self.engine.architecture()

    def tech_debt(self) -> dict[str, Any]:
        return self.engine.tech_debt()

    def explainability_check(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.engine.explainability_check(payload)
