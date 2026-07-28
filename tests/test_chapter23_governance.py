"""Chapter 23 — Roadmap, Future Evolution & AI Governance tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_ch23_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""
os.environ["APP_ENV"] = "testing"
os.environ["API_RATE_LIMIT_PER_MINUTE"] = "2000"

from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import app  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402
from src.governance.ai_policy import evaluate_model_drift, validate_ai_conclusion
from src.governance.contracts import GovernanceObject, MaturityStage, PromptRecord
from src.governance.prompts import prompt_registry
from src.governance.roadmap import roadmap_view, tech_debt_registry
from src.services.governance import GovernanceService


def setup_module():
    reset_engine()
    init_db(seed=True)
    tech_debt_registry.clear()


def test_governance_object_shape():
    obj = GovernanceObject()
    d = obj.to_dict()
    assert d["vision"] == "AI-native Market Intelligence Platform"
    assert d["ai_advisory_only"] is True
    assert d["human_in_the_loop"] is True
    assert d["explainability_required"] is True
    assert d["schema_version"] == "1.0"
    assert d["maturity_stage"] == MaturityStage.OPERATIONAL.value


def test_prompt_registry_and_human_review():
    prompts = prompt_registry.list()
    assert len(prompts) >= 3
    ids = {p["prompt_id"] for p in prompts}
    assert "daily_outlook.narrative" in ids
    assert prompt_registry.requires_human_review("daily_outlook.narrative", "1.1.0") is True
    rec = PromptRecord(
        prompt_id="daily_outlook.narrative",
        version="1.0.0",
        author="tester",
        effective_date="2026-07-28",
        review_history=["test"],
        summary="noop same version",
    )
    assert prompt_registry.requires_human_review(rec.prompt_id, rec.version) is False


def test_explainability_and_drift():
    bad = validate_ai_conclusion({"market_bias": "Bullish"})
    assert bad["ok"] is False
    assert "Supporting evidence" in bad["missing"]
    good = validate_ai_conclusion(
        {
            "reasoning": {
                "supporting_evidence": ["Futures premium supportive"],
                "confidence_explanation": "Layer agreement elevated confidence",
                "alternative_scenarios": ["Range continuation"],
                "influential_indicators": ["Funding", "OI"],
            },
            "scenarios": [{"name": "Bullish Continuation"}],
        }
    )
    assert good["ok"] is True
    drift = evaluate_model_drift(confidence_samples=[55, 56, 54, 57, 55])
    assert "monitored" in drift
    assert drift["investigation_required"] is False


def test_roadmap_and_service():
    rm = roadmap_view()
    assert rm["versions"]["1.0"]["status"] == "current"
    assert "Multi-asset support" in rm["versions"]["1.5"]["features"]
    status = GovernanceService().status()
    assert status["book_complete"] is True
    assert status["chapters"] == 23
    assert status["governance_object"]["ai_advisory_only"] is True


def test_governance_api_and_chapter_tags():
    client = TestClient(app)
    r = client.get("/api/v1/governance/status")
    assert r.status_code == 200
    assert r.json()["data"]["schema_version"] == "1.0"

    for path in (
        "/api/v1/governance/object",
        "/api/v1/governance/roadmap",
        "/api/v1/governance/prompts",
        "/api/v1/governance/ai",
        "/api/v1/governance/drift",
        "/api/v1/governance/maturity",
        "/api/v1/governance/lifecycle",
        "/api/v1/governance/architecture",
        "/api/v1/governance/debt",
    ):
        resp = client.get(path)
        assert resp.status_code == 200, path

    ai = client.get("/api/v1/governance/ai").json()["data"]
    assert ai["governance"]["autonomous_execution"] is False
    assert ai["human_in_the_loop"]["bypass_allowed"] is False

    health = client.get("/api/v1/health").json()["data"]
    assert health["chapter"] == "23-governance-roadmap"
    assert health["phase"] == "rewrite-ch23"

    arch = client.get("/api/v1/architecture").json()["data"]
    assert arch["governance_roadmap"]["chapter"] == 23
    assert arch["governance_roadmap"]["book_complete"] is True
