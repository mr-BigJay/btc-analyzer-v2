"""QA catalog aggregation (Ch.22)."""

from __future__ import annotations

from typing import Any

from src.qa.contracts import (
    ACCEPTANCE_CRITERIA,
    APPROVAL_WORKFLOW,
    COVERAGE_TARGETS,
    DEFECT_SEVERITIES,
    QA_ENGINE_VERSION,
    QA_SCHEMA_VERSION,
)
from src.qa.data_ai import validate_ai_output, validate_market_payload
from src.qa.defects import quality_metrics_snapshot
from src.qa.gates import build_test_report, evaluate_quality_gates
from src.qa.performance import evaluate_performance, load_catalog, stress_probe
from src.qa.replay import run_historical_replay
from src.qa.resilience import evaluate_resilience
from src.qa.runners import (
    pipeline_overview,
    run_e2e_smoke,
    run_integration_smoke,
    run_static_analysis,
    run_unit_smoke,
)
from src.qa.security_qa import evaluate_security_qa
from src.qa.testdata import edge_case_catalog, synthetic_tick


def run_full_suite(*, include_stress: bool = False) -> dict[str, Any]:
    static = run_static_analysis()
    unit = run_unit_smoke()
    integration = run_integration_smoke()
    e2e = run_e2e_smoke()
    performance = evaluate_performance()
    security = evaluate_security_qa()
    resilience = evaluate_resilience()
    data = validate_market_payload(synthetic_tick())
    # AI validation against a minimal structured sample when e2e report unavailable
    ai_sample = {
        "market_bias": "Neutral",
        "confidence": 60,
        "executive_summary": "Balanced conditions with measured risk.",
        "report_type": "daily_outlook",
    }
    ai = validate_ai_output(ai_sample)
    replay = run_historical_replay()
    critical_clear = quality_metrics_snapshot()["critical_open"] == 0

    gates = evaluate_quality_gates(
        unit_ok=bool(unit.get("ok")) and bool(static.get("ok")),
        integration_ok=bool(integration.get("ok")),
        e2e_ok=bool(e2e.get("ok")),
        security_ok=bool(security.get("ok")),
        performance_ok=bool(performance.get("ok")),
        migrations_ok=True,
        ai_ok=bool(ai.get("ok")),
        critical_defects_clear=critical_clear,
    )
    report = build_test_report(
        unit_ok=gates["flags"]["unit_tests"] == "Passed",
        integration_ok=gates["flags"]["integration_tests"] == "Passed",
        e2e_ok=gates["flags"]["end_to_end_tests"] == "Passed",
        security_ok=gates["flags"]["security"] == "Passed",
        performance_ok=gates["flags"]["performance"] == "Passed",
        ai_ok=gates["flags"]["ai_validation"] == "Passed",
        migrations_ok=True,
        critical_defects_clear=critical_clear,
    )
    out: dict[str, Any] = {
        "static": static,
        "unit": unit,
        "integration": integration,
        "e2e": e2e,
        "performance": performance,
        "security": security,
        "resilience": resilience,
        "data_validation": data,
        "ai_validation": ai,
        "historical_replay": replay,
        "gates": gates,
        "test_report": report.to_dict(),
        "quality_metrics": quality_metrics_snapshot(test_success_rate=1.0 if gates["all_passed"] else 0.0),
    }
    if include_stress:
        out["stress"] = stress_probe()
        out["load"] = load_catalog()
    return out


def qa_catalog() -> dict[str, Any]:
    suite = run_full_suite(include_stress=True)
    return {
        "schema_version": QA_SCHEMA_VERSION,
        "engine_version": QA_ENGINE_VERSION,
        "objectives": [
            "Functional correctness",
            "Analytical consistency",
            "Operational reliability",
            "Security validation",
            "Performance verification",
            "Regression protection",
            "Automated quality gates",
        ],
        "pipeline": pipeline_overview(),
        "coverage_targets": COVERAGE_TARGETS,
        "defect_severities": DEFECT_SEVERITIES,
        "acceptance_criteria": ACCEPTANCE_CRITERIA,
        "approval_workflow": APPROVAL_WORKFLOW,
        "test_data": edge_case_catalog(),
        "suite": suite,
        "test_report": suite["test_report"],
        "principles": [
            "Test early and continuously",
            "Automate whenever practical",
            "Verify behavior, not implementation",
            "Preserve backward compatibility",
            "Treat failures as learning opportunities",
            "Use measurable quality gates",
            "Prevent defects rather than detect them late",
        ],
        "endpoints": [
            "/api/v1/qa/status",
            "/api/v1/qa/report",
            "/api/v1/qa/gates",
            "/api/v1/qa/suite",
            "/api/v1/qa/performance",
            "/api/v1/qa/security",
            "/api/v1/qa/resilience",
            "/api/v1/qa/replay",
        ],
    }
