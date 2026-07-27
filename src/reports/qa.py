"""Report QA validation before publication (Ch.10 §10.19)."""

from __future__ import annotations

from typing import Any

from src.reports.contracts import CanonicalReport


REQUIRED_FIELDS = (
    "report_type",
    "generated_at",
    "market_bias",
    "confidence",
    "market_regime",
    "executive_summary",
    "metadata",
)


def validate_report(report: CanonicalReport | dict[str, Any]) -> dict[str, Any]:
    data = report.to_dict() if isinstance(report, CanonicalReport) else dict(report)
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_FIELDS:
        if data.get(field) in (None, "", {}):
            errors.append(f"Missing required field: {field}")

    conf = data.get("confidence")
    try:
        conf_f = float(conf)
        if not 0 <= conf_f <= 100:
            errors.append(f"Confidence out of range: {conf}")
    except (TypeError, ValueError):
        errors.append("Confidence must be numeric")

    scenarios = []
    primary = data.get("primary_scenario") or {}
    if primary:
        scenarios.append(primary)
    scenarios.extend(data.get("alternative_scenarios") or [])
    if scenarios:
        try:
            total = sum(float(s.get("probability") or 0) for s in scenarios if isinstance(s, dict))
            if abs(total - 100.0) > 1.5 and len(scenarios) >= 2:
                errors.append(f"Scenario probabilities sum to {total}, expected ~100")
        except (TypeError, ValueError):
            errors.append("Scenario probabilities invalid")

    # Explanations available for non-neutral / actionable plans
    explain = data.get("explainability") or {}
    plan = data.get("trading_plan") or {}
    if plan.get("direction") in ("long", "short") and not (
        explain.get("primary_conclusion") or data.get("final_conclusion") or data.get("executive_summary")
    ):
        errors.append("Actionable trading plan without explanation")

    meta = data.get("metadata") or {}
    for key in ("report_id", "generation_time", "engine_version", "schema_version"):
        if not meta.get(key):
            errors.append(f"Incomplete metadata: {key}")

    # Contradictory conclusions: Strong Bullish bias with exclusively bearish primary scenario
    bias = str(data.get("market_bias") or "")
    pname = str((primary or {}).get("name") or "")
    if "Bullish" in bias and "Bearish" in pname and float((primary or {}).get("probability") or 0) >= 50:
        warnings.append("Primary scenario leans against market bias label")
    if "Bearish" in bias and "Bullish" in pname and float((primary or {}).get("probability") or 0) >= 50:
        warnings.append("Primary scenario leans against market bias label")

    mbs = data.get("market_bias_score")
    if mbs is not None:
        try:
            if "Bullish" in bias and float(mbs) < -15:
                errors.append("Bias label inconsistent with market_bias_score")
            if "Bearish" in bias and float(mbs) > 15:
                errors.append("Bias label inconsistent with market_bias_score")
        except (TypeError, ValueError):
            warnings.append("market_bias_score not numeric")

    ok = not errors
    return {
        "ok": ok,
        "publish": ok,
        "errors": errors,
        "warnings": warnings,
    }
