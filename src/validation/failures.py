"""Failure categorization for incorrect predictions (Ch.14 §14.17)."""

from __future__ import annotations

from typing import Any


FAILURE_CATEGORIES = (
    "insufficient_data",
    "unexpected_macro_event",
    "liquidity_shock",
    "model_conflict",
    "excessive_leverage",
    "exchange_outage",
    "unknown",
)


def categorize_failure(
    *,
    data_quality: float | None = None,
    conflicts: list[Any] | None = None,
    return_pct: float | None = None,
    funding_rate: float | None = None,
    source_flags: dict[str, bool] | None = None,
    macro_event: bool = False,
) -> dict[str, Any]:
    reasons: list[str] = []
    if data_quality is not None and data_quality < 0.55:
        reasons.append("insufficient_data")
    if macro_event:
        reasons.append("unexpected_macro_event")
    if return_pct is not None and abs(return_pct) >= 0.04:
        reasons.append("liquidity_shock")
    if conflicts:
        reasons.append("model_conflict")
    if funding_rate is not None and abs(funding_rate) >= 0.001:
        reasons.append("excessive_leverage")
    if source_flags and any(v is False for v in source_flags.values()):
        reasons.append("exchange_outage")
    if not reasons:
        reasons.append("unknown")
    return {
        "primary": reasons[0],
        "all": reasons,
        "categories": list(FAILURE_CATEGORIES),
    }
