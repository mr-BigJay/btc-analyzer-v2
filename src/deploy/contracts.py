"""Deployment & Infrastructure contracts (Ch.20)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

DEPLOY_SCHEMA_VERSION = "1.0"
DEPLOY_ENGINE_VERSION = "1.0"


class Environment(str, Enum):
    DEVELOPMENT = "Development"
    TESTING = "Testing"
    STAGING = "Staging"
    PRODUCTION = "Production"


class DeploymentStrategy(str, Enum):
    ROLLING = "Rolling Update"
    BLUE_GREEN = "Blue-Green"
    CANARY = "Canary"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class DeploymentObject:
    """Standard Deployment Object (Ch.20 §20.25)."""

    environment: str = Environment.DEVELOPMENT.value
    application_version: str = "1.0.0"
    deployment_strategy: str = DeploymentStrategy.BLUE_GREEN.value
    container_runtime: str = "Docker"
    database: str = "PostgreSQL"
    cache: str = "Redis"
    monitoring: bool = True
    rollback_enabled: bool = True
    schema_version: str = DEPLOY_SCHEMA_VERSION
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CORE_CONTAINERS = [
    "nginx",
    "api",
    "scheduler",
    "collectors",
    "ai",
    "postgres",
    "redis",
]

FUTURE_CONTAINERS = [
    "monitoring",
    "grafana",
    "prometheus",
    "alertmanager",
    "celery-workers",
]

SCALABILITY = {
    "API": "Yes",
    "Collectors": "Yes",
    "AI Engine": "Yes",
    "WebSocket Gateway": "Yes",
    "Scheduler": "Limited (leader election required)",
    "PostgreSQL": "Read replicas supported",
}

RTO_MINUTES = 30
RPO_MINUTES = 5

PRODUCTION_READINESS = [
    ("Automated tests passed", "tests_passed"),
    ("Security scan completed", "security_scan"),
    ("Database migrations validated", "migrations_validated"),
    ("Health checks operational", "health_checks"),
    ("Backup verified", "backup_verified"),
    ("Rollback plan available", "rollback_plan"),
    ("Monitoring active", "monitoring"),
    ("Logging enabled", "logging"),
    ("Environment variables validated", "env_validated"),
]

REQUIRED_ENV_KEYS = [
    "DATABASE_URL",
    "REDIS_URL",
    "API_JWT_SECRET",  # design-book alias: JWT_SECRET
    "LOG_LEVEL",
    "TIMEZONE",
    "APP_ENV",
]
