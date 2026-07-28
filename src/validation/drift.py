"""Drift detection — raise review flags, never silent adapt (Ch.14 §14.16)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from src.validation.contracts import DriftStatus, utc_now_iso


@dataclass
class DriftReport:
    status: str = DriftStatus.NONE.value
    drift_detected: bool = False
    signals: list[dict[str, Any]] = field(default_factory=list)
    reviewed: bool = False
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "drift_detected": self.drift_detected,
            "signals": self.signals,
            "reviewed": self.reviewed,
            "generated_at": self.generated_at,
        }


def detect_performance_drift(
    recent_accuracy: float,
    baseline_accuracy: float,
    *,
    watch_drop: float = 5.0,
    review_drop: float = 10.0,
) -> DriftReport:
    drop = baseline_accuracy - recent_accuracy
    report = DriftReport()
    if drop >= review_drop:
        report.drift_detected = True
        report.status = DriftStatus.REVIEW.value
        report.signals.append(
            {"type": "performance_drift", "drop": round(drop, 2), "recent": recent_accuracy, "baseline": baseline_accuracy}
        )
    elif drop >= watch_drop:
        report.drift_detected = True
        report.status = DriftStatus.WATCH.value
        report.signals.append(
            {"type": "performance_drift", "drop": round(drop, 2), "recent": recent_accuracy, "baseline": baseline_accuracy}
        )
    return report


def detect_feature_drift(
    recent_means: dict[str, float],
    baseline_means: dict[str, float],
    *,
    threshold: float = 0.35,
) -> DriftReport:
    report = DriftReport()
    for key, base in baseline_means.items():
        if key not in recent_means:
            continue
        if base == 0:
            continue
        rel = abs(recent_means[key] - base) / abs(base)
        if rel >= threshold:
            report.drift_detected = True
            report.status = DriftStatus.REVIEW.value if rel >= threshold * 1.5 else DriftStatus.WATCH.value
            report.signals.append(
                {"type": "feature_drift", "feature": key, "relative_change": round(rel, 3), "recent": recent_means[key], "baseline": base}
            )
    return report


def merge_drift_reports(reports: Sequence[DriftReport]) -> DriftReport:
    merged = DriftReport()
    for r in reports:
        if r.drift_detected:
            merged.drift_detected = True
            merged.signals.extend(r.signals)
            if r.status == DriftStatus.REVIEW.value or merged.status == DriftStatus.REVIEW.value:
                merged.status = DriftStatus.REVIEW.value
            elif r.status == DriftStatus.WATCH.value:
                merged.status = DriftStatus.WATCH.value
    return merged
