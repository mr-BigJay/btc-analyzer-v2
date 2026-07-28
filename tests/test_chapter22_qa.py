"""Chapter 22 — Testing Strategy & Quality Assurance tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

TEST_DB = Path("/tmp/btc_analyzer_ch22_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""
os.environ["APP_ENV"] = "testing"
os.environ["API_RATE_LIMIT_PER_MINUTE"] = "2000"

from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import app  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402
from src.qa.contracts import DefectSeverity, TestReport
from src.qa.data_ai import validate_ai_output, validate_market_payload
from src.qa.defects import defect_registry
from src.qa.gates import build_test_report, evaluate_quality_gates
from src.qa.performance import evaluate_performance, stress_probe
from src.qa.replay import run_historical_replay
from src.qa.resilience import evaluate_resilience
from src.qa.runners import run_static_analysis, run_unit_smoke
from src.qa.security_qa import evaluate_security_qa
from src.qa.testdata import corrupted_tick, synthetic_tick
from src.services.qa import QAService


def setup_module():
    reset_engine()
    init_db(seed=True)
    defect_registry.clear()


@pytest.mark.unit
def test_test_report_shape():
    report = TestReport(
        release="1.0.0",
        unit_tests="Passed",
        integration_tests="Passed",
        end_to_end_tests="Passed",
        performance="Passed",
        security="Passed",
        ai_validation="Passed",
        overall_status="Approved",
    )
    d = report.to_dict()
    assert d["schema_version"] == "1.0"
    assert d["overall_status"] == "Approved"
    assert d["unit_tests"] == "Passed"


@pytest.mark.unit
def test_quality_gates_block_on_failure():
    ok = evaluate_quality_gates()
    assert ok["can_release"] is True
    blocked = evaluate_quality_gates(security_ok=False)
    assert blocked["can_release"] is False
    report = build_test_report(security_ok=False)
    assert report.overall_status == "Blocked"


@pytest.mark.unit
def test_data_and_ai_validation():
    good = validate_market_payload(synthetic_tick())
    assert good["ok"] is True
    bad = validate_market_payload(corrupted_tick())
    assert bad["ok"] is False
    assert any("missing" in i or "invalid" in i for i in bad["issues"])

    ai_ok = validate_ai_output(
        {
            "market_bias": "Bullish",
            "confidence": 70,
            "executive_summary": "Trend supported by structure.",
            "report_type": "daily_outlook",
        }
    )
    assert ai_ok["ok"] is True
    ai_bad = validate_ai_output({"confidence": 150})
    assert ai_bad["ok"] is False


@pytest.mark.unit
def test_defects_and_static_unit_smoke():
    defect_registry.clear()
    d = defect_registry.report(title="example", severity=DefectSeverity.LOW.value)
    assert d["severity"] == "Low"
    assert run_static_analysis()["ok"] is True
    assert run_unit_smoke()["ok"] is True


@pytest.mark.performance
def test_performance_and_stress():
    perf = evaluate_performance()
    assert perf["ok"] is True
    stress = stress_probe(burst=20)
    assert stress["ok"] is True


@pytest.mark.security
def test_security_and_resilience():
    sec = evaluate_security_qa()
    assert sec["ok"] is True
    assert "Authentication" in sec["checks"]
    res = evaluate_resilience()
    assert res["ok"] is True
    assert len(res["scenarios"]) >= 6


@pytest.mark.regression
def test_historical_replay():
    out = run_historical_replay()
    assert out["ok"] is True
    assert out["result"]["ok"] is True


@pytest.mark.integration
def test_qa_api_and_chapter_tags():
    client = TestClient(app)
    status = QAService().status()
    assert status["schema_version"] == "1.0"
    assert status["test_report"]["schema_version"] == "1.0"

    r = client.get("/api/v1/qa/status")
    assert r.status_code == 200
    assert r.json()["data"]["engine_version"] == "1.0"

    r2 = client.get("/api/v1/qa/report")
    assert r2.status_code == 200
    assert r2.json()["data"]["overall_status"] in {"Approved", "Blocked", "Conditional"}

    r3 = client.get("/api/v1/qa/gates")
    assert r3.status_code == 200
    assert r3.json()["data"]["items"]

    r4 = client.get("/api/v1/qa/suite")
    assert r4.status_code == 200
    assert r4.json()["data"]["unit"]["ok"] is True

    for path in (
        "/api/v1/qa/performance",
        "/api/v1/qa/security",
        "/api/v1/qa/resilience",
        "/api/v1/qa/replay",
        "/api/v1/qa/defects",
    ):
        resp = client.get(path)
        assert resp.status_code == 200, path

    health = client.get("/api/v1/health").json()["data"]
    assert health["chapter"] == "22-testing-qa"
    assert health["phase"] == "rewrite-ch22"

    arch = client.get("/api/v1/architecture").json()["data"]
    assert arch["testing_qa"]["chapter"] == 22
    assert arch["testing_qa"]["quality_gates"] is True
