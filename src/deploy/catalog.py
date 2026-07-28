"""Deployment catalog and DeploymentObject builder (Ch.20)."""

from __future__ import annotations

from typing import Any

from src import __version__
from src.config import settings
from src.deploy.contracts import (
    CORE_CONTAINERS,
    DEPLOY_ENGINE_VERSION,
    DEPLOY_SCHEMA_VERSION,
    FUTURE_CONTAINERS,
    SCALABILITY,
    DeploymentObject,
    DeploymentStrategy,
)
from src.deploy.environments import resolve_environment, validate_environment_variables
from src.deploy.readiness import production_readiness, rollback_policy


def build_deployment_object(
    *,
    environment: str | None = None,
    strategy: str | None = None,
) -> DeploymentObject:
    env = environment or resolve_environment()
    db = "PostgreSQL" if settings.is_postgres else "SQLite"
    return DeploymentObject(
        environment=env,
        application_version=__version__,
        deployment_strategy=strategy or DeploymentStrategy.BLUE_GREEN.value,
        container_runtime="Docker",
        database=db,
        cache="Redis",
        monitoring=True,
        rollback_enabled=True,
    )


def deploy_catalog() -> dict[str, Any]:
    return {
        "schema_version": DEPLOY_SCHEMA_VERSION,
        "engine_version": DEPLOY_ENGINE_VERSION,
        "objectives": [
            "Reproducible deployments",
            "Environment consistency",
            "Zero or minimal downtime updates",
            "Automated rollback capability",
            "Horizontal scalability",
            "Infrastructure portability",
            "Operational resilience",
        ],
        "environments": ["Development", "Testing", "Staging", "Production"],
        "core_containers": CORE_CONTAINERS,
        "future_containers": FUTURE_CONTAINERS,
        "scalability": SCALABILITY,
        "pipeline": [
            "Source Code",
            "Static Analysis",
            "Unit Tests",
            "Container Build",
            "Security Scan",
            "Integration Tests",
            "Artifact Registry",
            "Deployment",
        ],
        "ci": [
            "Code formatting",
            "Static analysis",
            "Unit tests",
            "Dependency scanning",
            "Container build verification",
        ],
        "cd": [
            "Automated deployment to staging",
            "Manual approval for production",
            "Health verification",
            "Rollback support",
        ],
        "service_discovery": ["postgres", "redis", "api", "scheduler", "collectors", "ai"],
        "persistent_storage": [
            "PostgreSQL database",
            "Reports",
            "Audit logs",
            "Configuration backups",
            "Feature Store",
        ],
        "deployment_object": build_deployment_object().to_dict(),
        "rollback": rollback_policy(),
        "environment_validation": validate_environment_variables(),
        "readiness": production_readiness(),
        "principles": [
            "Immutable deployments",
            "Infrastructure as Code",
            "Automation over manual intervention",
            "Stateless application services",
            "Safe and reversible releases",
            "Continuous health verification",
            "Scalable and portable infrastructure",
        ],
        "endpoints": [
            "/health",
            "/ready",
            "/live",
            "/api/v1/health",
            "/api/v1/deploy/status",
            "/api/v1/deploy/object",
            "/api/v1/deploy/checklist",
        ],
    }
