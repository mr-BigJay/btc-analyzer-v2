"""Feature validation + quarantine (Ch.13 §13.17)."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from src.features.contracts import FeatureRecord, FeatureScale, FeatureSet, utc_now_iso
from src.features.normalize import apply_scale


@dataclass
class FeatureIssue:
    feature: str
    code: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class FeatureValidationReport:
    ok: bool = True
    issues: list[FeatureIssue] = field(default_factory=list)

    def add(self, feature: str, code: str, message: str, severity: str = "error") -> None:
        self.issues.append(FeatureIssue(feature, code, message, severity))
        if severity == "error":
            self.ok = False


@dataclass
class QuarantineItem:
    id: str
    feature: str
    reason: str
    record: dict[str, Any]
    quarantined_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "feature": self.feature,
            "reason": self.reason,
            "record": self.record,
            "quarantined_at": self.quarantined_at,
        }


class FeatureQuarantine:
    def __init__(self, *, maxlen: int = 500) -> None:
        self._items: deque[QuarantineItem] = deque(maxlen=maxlen)
        self._lock = threading.RLock()

    def add(self, feature: str, record: dict[str, Any], reason: str) -> QuarantineItem:
        item = QuarantineItem(id=str(uuid4()), feature=feature, reason=reason, record=record)
        with self._lock:
            self._items.append(item)
        return item

    def list(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._items)[-limit:]
        return [i.to_dict() for i in items]

    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


feature_quarantine = FeatureQuarantine()


def validate_feature(rec: FeatureRecord) -> FeatureValidationReport:
    report = FeatureValidationReport()
    if not rec.name:
        report.add("", "NAME", "Feature name required")
    if rec.value is None:
        report.add(rec.name, "MISSING", "Null value", severity="warning")
        return report
    if isinstance(rec.value, str):
        if rec.scale != FeatureScale.CATEGORICAL.value:
            report.add(rec.name, "TYPE", "String value requires categorical scale", severity="warning")
        return report
    try:
        fv = float(rec.value)
    except (TypeError, ValueError):
        report.add(rec.name, "TYPE", "Value not numeric")
        return report
    if fv != fv or fv in (float("inf"), float("-inf")):
        report.add(rec.name, "RANGE", "Non-finite value")
        return report
    scaled = apply_scale(fv, rec.scale)
    if scaled is None:
        report.add(rec.name, "SCALE", "Scale normalization failed")
    elif rec.scale == FeatureScale.DIRECTIONAL.value and not (-100 <= scaled <= 100):
        report.add(rec.name, "RANGE", f"Directional out of range: {scaled}")
    elif rec.scale == FeatureScale.PROBABILITY.value and not (0 <= scaled <= 100):
        report.add(rec.name, "RANGE", f"Probability out of range: {scaled}")
    elif rec.scale == FeatureScale.RATIO.value and not (0 <= scaled <= 1):
        report.add(rec.name, "RANGE", f"Ratio out of range: {scaled}")
    return report


def validate_feature_set(fs: FeatureSet) -> tuple[FeatureSet, FeatureValidationReport]:
    report = FeatureValidationReport()
    kept: dict[str, FeatureRecord] = {}
    qids: list[str] = []
    for name, rec in fs.features.items():
        r = validate_feature(rec)
        report.issues.extend(r.issues)
        hard = [i for i in r.issues if i.severity == "error"]
        if hard:
            report.ok = False
            item = feature_quarantine.add(name, rec.to_dict(), hard[0].message)
            qids.append(item.id)
            continue
        # Apply normalized scale in-place for numeric values
        if isinstance(rec.value, (int, float)) and rec.value is not None:
            normed = apply_scale(float(rec.value), rec.scale)
            if normed is not None:
                rec.value = round(normed, 6)
        kept[name] = rec
    fs.features = kept
    fs.quarantine_ids = qids
    fs.valid = report.ok or not any(i.severity == "error" for i in report.issues)
    return fs, report
