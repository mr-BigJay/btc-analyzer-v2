"""Deploy service facade (Ch.20)."""

from __future__ import annotations

from typing import Any

from src.deploy.engine import DeployEngine


class DeployService:
    def __init__(self) -> None:
        self.engine = DeployEngine()

    def status(self) -> dict[str, Any]:
        return self.engine.status()

    def deployment_object(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.deployment_object(**kwargs)

    def checklist(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.checklist(**kwargs)

    def rollback(self) -> dict[str, Any]:
        return self.engine.rollback()

    def health(self) -> dict[str, Any]:
        return self.engine.health()

    def ready(self) -> dict[str, Any]:
        return self.engine.ready()

    def live(self) -> dict[str, Any]:
        return self.engine.live()
