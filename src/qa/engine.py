"""QA engine facade (Ch.22)."""

from __future__ import annotations

from typing import Any

from src.qa.catalog import qa_catalog, run_full_suite
from src.qa.data_ai import validate_ai_output, validate_market_payload
from src.qa.defects import defect_registry, quality_metrics_snapshot
from src.qa.gates import build_test_report, evaluate_quality_gates
from src.qa.performance import evaluate_performance, load_catalog, stress_probe
from src.qa.replay import run_historical_replay
from src.qa.resilience import evaluate_resilience
from src.qa.runners import pipeline_overview
from src.qa.security_qa import evaluate_security_qa
from src.qa.testdata import edge_case_catalog


class QAEngine:
    def status(self) -> dict[str, Any]:
        return qa_catalog()

    def report(self, **kwargs: Any) -> dict[str, Any]:
        return build_test_report(**kwargs).to_dict()

    def gates(self, **kwargs: Any) -> dict[str, Any]:
        return evaluate_quality_gates(**kwargs)

    def suite(self, *, include_stress: bool = False) -> dict[str, Any]:
        return run_full_suite(include_stress=include_stress)

    def performance(self) -> dict[str, Any]:
        return evaluate_performance()

    def load(self) -> dict[str, Any]:
        return load_catalog()

    def stress(self, **kwargs: Any) -> dict[str, Any]:
        return stress_probe(**kwargs)

    def security(self) -> dict[str, Any]:
        return evaluate_security_qa()

    def resilience(self) -> dict[str, Any]:
        return evaluate_resilience()

    def replay(self, **kwargs: Any) -> dict[str, Any]:
        return run_historical_replay(**kwargs)

    def data_validation(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return validate_market_payload(payload)

    def ai_validation(self, report: dict[str, Any] | None = None) -> dict[str, Any]:
        return validate_ai_output(report)

    def testdata(self) -> dict[str, Any]:
        return edge_case_catalog()

    def defects(self, *, limit: int = 50) -> dict[str, Any]:
        return {"defects": defect_registry.list(limit=limit), "metrics": quality_metrics_snapshot()}

    def pipeline(self) -> dict[str, Any]:
        return pipeline_overview()
