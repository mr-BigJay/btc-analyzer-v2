"""Release quality gates and Test Report builder (Ch.22 §22.19 / §22.24)."""

from __future__ import annotations

from typing import Any

from src import __version__
from src.qa.contracts import (
    RELEASE_GATES,
    GateStatus,
    OverallStatus,
    TestReport,
    utc_now_iso,
)


def _status(ok: bool) -> str:
    return GateStatus.PASSED.value if ok else GateStatus.FAILED.value


def evaluate_quality_gates(
    *,
    unit_ok: bool = True,
    integration_ok: bool = True,
    e2e_ok: bool = True,
    security_ok: bool = True,
    performance_ok: bool = True,
    migrations_ok: bool = True,
    ai_ok: bool = True,
    critical_defects_clear: bool = True,
) -> dict[str, Any]:
    flags = {
        "unit_tests": unit_ok,
        "integration_tests": integration_ok,
        "end_to_end_tests": e2e_ok,
        "security": security_ok,
        "performance": performance_ok,
        "migrations": migrations_ok,
        "ai_validation": ai_ok,
        "critical_defects": critical_defects_clear,
    }
    items = []
    for key, label in RELEASE_GATES:
        ok = bool(flags[key])
        items.append({"gate": key, "label": label, "status": "✓" if ok else "✗", "ok": ok})
    all_ok = all(flags.values())
    return {
        "items": items,
        "all_passed": all_ok,
        "can_release": all_ok,
        "evaluated_at": utc_now_iso(),
        "flags": {k: _status(v) for k, v in flags.items()},
    }


def build_test_report(
    *,
    release: str | None = None,
    unit_ok: bool = True,
    integration_ok: bool = True,
    e2e_ok: bool = True,
    security_ok: bool = True,
    performance_ok: bool = True,
    ai_ok: bool = True,
    migrations_ok: bool = True,
    critical_defects_clear: bool = True,
) -> TestReport:
    gates = evaluate_quality_gates(
        unit_ok=unit_ok,
        integration_ok=integration_ok,
        e2e_ok=e2e_ok,
        security_ok=security_ok,
        performance_ok=performance_ok,
        migrations_ok=migrations_ok,
        ai_ok=ai_ok,
        critical_defects_clear=critical_defects_clear,
    )
    overall = OverallStatus.APPROVED.value if gates["can_release"] else OverallStatus.BLOCKED.value
    return TestReport(
        release=release or __version__,
        unit_tests=_status(unit_ok),
        integration_tests=_status(integration_ok),
        end_to_end_tests=_status(e2e_ok),
        performance=_status(performance_ok),
        security=_status(security_ok),
        ai_validation=_status(ai_ok),
        overall_status=overall,
    )
