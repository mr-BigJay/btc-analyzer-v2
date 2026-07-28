"""Validation governance — evidence before promotion (Ch.14 §14.21–§14.22)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import settings
from src.validation.contracts import ValidationObject, utc_now_iso


def governance_dir() -> Path:
    path = settings.data_dir / "validation" / "governance"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_validation_object(
    metrics: dict[str, Any],
    *,
    engine_version: str,
    validation_period: str,
    method: str,
    calibration_label: str,
    regime_results: dict[str, Any] | None = None,
    layer_contribution: dict[str, Any] | None = None,
    calibration_bins: dict[str, Any] | None = None,
    drift_detected: bool = False,
    drift_status: str = "none",
    dataset_version: str | None = None,
    known_limitations: list[str] | None = None,
) -> ValidationObject:
    return ValidationObject(
        engine_version=engine_version,
        validation_period=validation_period,
        method=method,
        accuracy=float(metrics.get("accuracy") or 0),
        precision=float(metrics.get("precision") or 0),
        recall=float(metrics.get("recall") or 0),
        f1_score=float(metrics.get("f1_score") or 0),
        win_rate=metrics.get("win_rate"),
        profit_factor=metrics.get("profit_factor"),
        expectancy=metrics.get("expectancy"),
        max_drawdown=metrics.get("max_drawdown"),
        sharpe_ratio=metrics.get("sharpe_ratio"),
        sortino_ratio=metrics.get("sortino_ratio"),
        confidence_calibration=calibration_label,
        market_regime_results=regime_results or {},
        layer_contribution=layer_contribution or {},
        calibration_bins=calibration_bins or {},
        drift_detected=drift_detected,
        drift_status=drift_status,
        known_limitations=known_limitations or [],
        dataset_version=dataset_version,
        sample_size=int(metrics.get("sample_size") or 0),
        approved=False,
    )


def approve_validation(
    obj: ValidationObject,
    *,
    approver: str,
    notes: str = "",
    min_accuracy: float = 70.0,
    min_samples: int = 20,
) -> ValidationObject:
    """Promote only with documented evidence — does not mutate historical predictions."""
    limitations = list(obj.known_limitations)
    if obj.sample_size < min_samples:
        limitations.append(f"sample_size<{min_samples}")
    if obj.accuracy < min_accuracy:
        limitations.append(f"accuracy<{min_accuracy}")
    if obj.drift_detected and obj.drift_status == "review":
        limitations.append("unresolved_drift_review")

    approved = obj.accuracy >= min_accuracy and obj.sample_size >= min_samples and not (
        obj.drift_detected and obj.drift_status == "review"
    )
    obj.known_limitations = limitations
    obj.approved = approved
    obj.approval_record = {
        "approver": approver,
        "notes": notes,
        "approved_at": utc_now_iso(),
        "approved": approved,
    }
    path = governance_dir() / f"validation_{obj.engine_version}_{obj.validation_period}_{obj.generated_at.replace(':', '-')}.json"
    path.write_text(json.dumps(obj.to_dict(), indent=2, default=str), encoding="utf-8")
    return obj
