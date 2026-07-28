"""Deployment engine facade helpers (Ch.20)."""

from __future__ import annotations

from typing import Any

from src.deploy.catalog import build_deployment_object, deploy_catalog
from src.deploy.probes import health_detailed, liveness, readiness
from src.deploy.readiness import production_readiness, rollback_policy


class DeployEngine:
    def status(self) -> dict[str, Any]:
        return deploy_catalog()

    def deployment_object(self, **kwargs: Any) -> dict[str, Any]:
        return build_deployment_object(**kwargs).to_dict()

    def checklist(self, **kwargs: Any) -> dict[str, Any]:
        return production_readiness(**kwargs)

    def rollback(self) -> dict[str, Any]:
        return rollback_policy()

    def health(self) -> dict[str, Any]:
        return health_detailed()

    def ready(self) -> dict[str, Any]:
        return readiness()

    def live(self) -> dict[str, Any]:
        return liveness()
