"""Chapter 20 — Deployment, DevOps & Infrastructure tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_ch20_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""
os.environ["APP_ENV"] = "testing"
os.environ["API_RATE_LIMIT_PER_MINUTE"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import app  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402
from src.deploy.catalog import build_deployment_object, deploy_catalog
from src.deploy.contracts import DeploymentObject, DeploymentStrategy, Environment
from src.deploy.environments import resolve_environment, validate_environment_variables
from src.deploy.probes import health_detailed, liveness, readiness
from src.deploy.readiness import production_readiness, rollback_policy
from src.services.deploy import DeployService


def setup_module():
    reset_engine()
    init_db(seed=True)


def test_deployment_object_shape():
    obj = DeploymentObject(
        environment=Environment.PRODUCTION.value,
        deployment_strategy=DeploymentStrategy.BLUE_GREEN.value,
    )
    d = obj.to_dict()
    assert d["environment"] == "Production"
    assert d["deployment_strategy"] == "Blue-Green"
    assert d["container_runtime"] == "Docker"
    assert d["database"] == "PostgreSQL"
    assert d["cache"] == "Redis"
    assert d["monitoring"] is True
    assert d["rollback_enabled"] is True
    assert d["schema_version"] == "1.0"


def test_resolve_environment():
    assert resolve_environment("prod") == "Production"
    assert resolve_environment("staging") == "Staging"
    assert resolve_environment("test") == "Testing"


def test_env_validation_and_probes():
    env = validate_environment_variables()
    assert env["ok"] is True
    assert env["hardcoded_forbidden"] is True
    live = liveness()
    assert live["ok"] is True
    assert live["status"] == "live"
    ready = readiness()
    assert ready["ok"] is True
    assert "database" in ready["checks"]
    health = health_detailed()
    assert health["ok"] is True


def test_production_checklist_and_rollback():
    cl = production_readiness(security_scan=True, backup_verified=True)
    assert cl["core_ok"] is True
    assert cl["can_deploy_production"] is True
    labels = {i["item"] for i in cl["items"]}
    assert "Health checks operational" in labels
    assert "Rollback plan available" in labels
    rb = rollback_policy()
    assert rb["enabled"] is True
    assert rb["rto_minutes"] == 30
    assert rb["rpo_minutes"] == 5
    assert "Health check failure" in rb["triggers"]


def test_deploy_catalog_and_service():
    cat = deploy_catalog()
    assert "nginx" in cat["core_containers"]
    assert "Artifact Registry" in cat["pipeline"]
    assert cat["deployment_object"]["rollback_enabled"] is True
    obj = build_deployment_object(environment="Staging")
    assert obj.environment == "Staging"
    status = DeployService().status()
    assert status["engine_version"] == "1.0"
    assert "/health" in status["endpoints"]


def test_deploy_and_probe_api():
    client = TestClient(app)

    r = client.get("/api/v1/deploy/status")
    assert r.status_code == 200
    assert r.json()["data"]["schema_version"] == "1.0"

    r2 = client.get("/api/v1/deploy/object")
    assert r2.status_code == 200
    assert r2.json()["data"]["container_runtime"] == "Docker"

    r3 = client.get("/api/v1/deploy/checklist")
    assert r3.status_code == 200
    assert r3.json()["data"]["items"]

    r4 = client.get("/api/v1/deploy/rollback")
    assert r4.status_code == 200
    assert r4.json()["data"]["rto_minutes"] == 30

    for path in ("/live", "/api/v1/live", "/ready", "/api/v1/ready", "/health", "/api/v1/health"):
        resp = client.get(path)
        assert resp.status_code == 200, path

    health = client.get("/api/v1/health").json()["data"]
    assert health["chapter"] == "23-governance-roadmap"
    assert health["phase"] == "rewrite-ch23"

    arch = client.get("/api/v1/architecture").json()["data"]
    assert arch["deployment_devops"]["chapter"] == 20
    assert arch["deployment_devops"]["rollback_enabled"] is True

    sys_h = client.get("/api/v1/system/health").json()["data"]
    assert sys_h["chapter"] == "23-governance-roadmap"
    assert sys_h["phase"] == "rewrite-ch23"
