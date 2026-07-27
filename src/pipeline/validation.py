"""Data Validation Layer (Ch.3 §3.10).

Checks every incoming dataset before it may enter the database.
Does not interpret market meaning — integrity only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ValidationIssue:
    source: str
    code: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ValidationReport:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = ""
    record_count: int = 0
    rejected_count: int = 0

    def add(self, source: str, code: str, message: str, severity: str = "error") -> None:
        self.issues.append(
            ValidationIssue(source=source, code=code, message=message, severity=severity)
        )
        if severity == "error":
            self.ok = False


class DataValidator:
    """Validates collected payloads (Ch.3 §3.10).

    Checks:
      - API response status
      - Missing fields
      - Invalid values
      - Duplicate records
      - Timestamp validation
      - Symbol verification
      - Numerical precision
    """

    ALLOWED_SYMBOLS = frozenset({"BTCUSDT", "BTC-PERPETUAL", "BTC"})
    MAX_AGE_SECONDS = 3600  # 1h soft freshness for REST snapshots

    def validate(self, source: str, payload: dict[str, Any]) -> ValidationReport:
        report = ValidationReport(ok=True, source=source)
        if not isinstance(payload, dict):
            report.add(source, "TYPE", "Payload must be a dict")
            return report

        status = payload.get("api_status")
        if status is None and "http_status" in payload:
            status = payload.get("http_status")
        if status is not None and str(status).upper() not in {"OK", "200", "SUCCESS", "TRUE"}:
            report.add(source, "API_STATUS", f"Bad API status: {status}")

        required = payload.get("_required_fields") or []
        for field_name in required:
            if payload.get(field_name) is None:
                report.add(source, "MISSING_FIELD", f"Missing required field: {field_name}")

        symbol = payload.get("symbol")
        if symbol is not None:
            normalized = str(symbol).upper().replace("_", "").replace("-", "")
            if "BTC" not in normalized and symbol not in self.ALLOWED_SYMBOLS:
                report.add(source, "SYMBOL", f"Unexpected symbol: {symbol}", severity="warning")

        ts = payload.get("timestamp")
        if ts is not None:
            parsed = self._parse_ts(ts)
            if parsed is None:
                report.add(source, "TIMESTAMP", f"Invalid timestamp: {ts}")
            else:
                age = (datetime.now(timezone.utc) - parsed).total_seconds()
                if age < -60:
                    report.add(source, "TIMESTAMP", f"Future timestamp: {ts}")
                elif age > self.MAX_AGE_SECONDS:
                    report.add(
                        source,
                        "TIMESTAMP",
                        f"Stale timestamp age={age:.0f}s",
                        severity="warning",
                    )

        for key, value in payload.items():
            if key.startswith("_"):
                continue
            if isinstance(value, float):
                if math.isnan(value) or math.isinf(value):
                    report.add(source, "INVALID_VALUE", f"{key} is NaN/Inf")
                elif abs(value) > 0 and abs(value) < 1e-18:
                    report.add(
                        source,
                        "PRECISION",
                        f"{key} below numerical precision floor",
                        severity="warning",
                    )
            if isinstance(value, (int, float)) and key in {
                "price",
                "mark_price",
                "index_price",
                "volume",
                "open_interest",
            }:
                if value < 0:
                    report.add(source, "INVALID_VALUE", f"{key} must be non-negative")

        records = payload.get("records")
        if isinstance(records, list):
            report.record_count = len(records)
            seen: set[str] = set()
            for i, rec in enumerate(records):
                if not isinstance(rec, dict):
                    report.add(source, "INVALID_VALUE", f"records[{i}] not an object")
                    report.rejected_count += 1
                    continue
                dedupe_key = str(rec.get("source_id") or rec.get("id") or rec.get("timestamp") or i)
                if dedupe_key in seen:
                    report.add(source, "DUPLICATE", f"Duplicate record: {dedupe_key}")
                    report.rejected_count += 1
                else:
                    seen.add(dedupe_key)

        return report

    def filter_valid_records(self, source: str, records: list[dict]) -> tuple[list[dict], ValidationReport]:
        """Return only records that pass per-row checks. Invalid never enter DB."""
        report = ValidationReport(ok=True, source=source, record_count=len(records))
        valid: list[dict] = []
        for i, rec in enumerate(records):
            row_report = self.validate(source, rec)
            if row_report.ok or all(iss.severity == "warning" for iss in row_report.issues):
                # Allow warnings through; hard errors reject
                hard = [iss for iss in row_report.issues if iss.severity == "error"]
                if hard:
                    report.issues.extend(hard)
                    report.ok = False
                    report.rejected_count += 1
                else:
                    report.issues.extend(row_report.issues)
                    valid.append(rec)
            else:
                report.issues.extend(row_report.issues)
                report.ok = False
                report.rejected_count += 1
        return valid, report

    @staticmethod
    def _parse_ts(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            # ms or s
            ts = float(value)
            if ts > 1e12:
                ts /= 1000.0
            try:
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
