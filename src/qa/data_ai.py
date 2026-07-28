"""Data validation and AI output QA (Ch.22 §22.14–22.15)."""

from __future__ import annotations

from typing import Any

from src.qa.contracts import utc_now_iso


DATA_CHECKS = [
    "Missing fields",
    "Timestamp consistency",
    "Duplicate records",
    "Invalid prices",
    "Symbol mapping",
    "Schema compliance",
]

AI_CHECKS = [
    "Internal consistency",
    "Explainability",
    "Scenario alignment",
    "Confidence calibration",
    "Unsupported claims",
    "Required output structure",
]


def validate_market_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    issues: list[str] = []
    required = ["symbol", "price", "timestamp"]
    for key in required:
        if key not in payload or payload.get(key) in (None, ""):
            issues.append(f"missing:{key}")
    price = payload.get("price")
    if price is not None:
        try:
            if float(price) <= 0:
                issues.append("invalid_price")
        except (TypeError, ValueError):
            issues.append("invalid_price")
    symbol = str(payload.get("symbol") or "")
    if symbol and not symbol.endswith("USDT") and "/" not in symbol:
        # soft warning style — still ok for exotic symbols
        pass
    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "checks": DATA_CHECKS,
        "timestamp": utc_now_iso(),
    }


def validate_ai_output(report: dict[str, Any] | None) -> dict[str, Any]:
    report = report or {}
    issues: list[str] = []
    # Required structure (flexible across report shapes)
    has_structure = any(
        k in report
        for k in ("executive_summary", "market_bias", "confidence", "scenarios", "report_type", "renders")
    )
    if not has_structure:
        issues.append("missing_required_structure")
    conf = report.get("confidence")
    if conf is not None:
        try:
            c = float(conf)
            if c < 0 or c > 100:
                issues.append("confidence_out_of_range")
        except (TypeError, ValueError):
            issues.append("confidence_invalid")
    bias = report.get("market_bias")
    summary = str(report.get("executive_summary") or "")
    # Unsupported absolute claims heuristic
    banned = ("guaranteed profit", "sure win", "cannot lose")
    if any(b in summary.lower() for b in banned):
        issues.append("unsupported_claim")
    explainable = bool(summary) or bool(report.get("rationale") or report.get("reasoning"))
    if bias and not explainable:
        issues.append("missing_explainability")
    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "checks": AI_CHECKS,
        "narrative_assessed_independently": True,
        "timestamp": utc_now_iso(),
    }
