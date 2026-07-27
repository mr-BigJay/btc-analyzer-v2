"""Data Validation stage (Ch.1 §1.7).

Rejects incomplete, stale, or inconsistent raw payloads before normalization.
Does not interpret market meaning — only data integrity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


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


class DataValidator:
    """Validates collected payloads from each evidence source.

    Spec details arrive in later chapters.
    """

    def validate(self, source: str, payload: dict) -> ValidationReport:
        raise NotImplementedError("Awaiting Design Book Chapter 2+")
