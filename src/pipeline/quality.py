"""Data quality rules before Analysis Engine (Ch.3 §3.19).

Rules: Complete · Accurate · Timely · Consistent · Normalized · Traceable
Failures → degraded + reduced confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class QualityAssessment:
    complete: bool = True
    accurate: bool = True
    timely: bool = True
    consistent: bool = True
    normalized: bool = True
    traceable: bool = True
    degraded: bool = False
    confidence: float = 1.0
    reasons: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.degraded

    def to_dict(self) -> dict[str, Any]:
        return {
            "complete": self.complete,
            "accurate": self.accurate,
            "timely": self.timely,
            "consistent": self.consistent,
            "normalized": self.normalized,
            "traceable": self.traceable,
            "degraded": self.degraded,
            "confidence": self.confidence,
            "reasons": self.reasons,
        }


class DataQualityGate:
    """Evaluate quality rules and adjust confidence."""

    MAX_AGE_SECONDS = 900  # 15 minutes for "timely"

    def assess(self, payload: dict[str, Any], *, source_live: bool = True) -> QualityAssessment:
        q = QualityAssessment()

        required = ("timestamp", "symbol", "exchange")
        missing = [k for k in required if not payload.get(k)]
        if missing:
            q.complete = False
            q.reasons.append(f"incomplete: missing {missing}")

        price = payload.get("price") or payload.get("mark_price")
        if price is not None:
            try:
                if float(price) <= 0:
                    q.accurate = False
                    q.reasons.append("inaccurate: non-positive price")
            except (TypeError, ValueError):
                q.accurate = False
                q.reasons.append("inaccurate: price not numeric")

        ts = payload.get("timestamp")
        if ts:
            parsed = _parse_ts(ts)
            if parsed is None:
                q.timely = False
                q.reasons.append("untimely: bad timestamp")
            else:
                age = (datetime.now(timezone.utc) - parsed).total_seconds()
                if age > self.MAX_AGE_SECONDS:
                    q.timely = False
                    q.reasons.append(f"untimely: age={age:.0f}s")

        symbol = str(payload.get("symbol", ""))
        if symbol and symbol != symbol.upper().replace("-", "").replace("_", ""):
            # Prefer already-normalized symbols
            if "-" in symbol or "_" in symbol:
                q.normalized = False
                q.reasons.append(f"not normalized: symbol={symbol}")

        if not payload.get("source_id") and not payload.get("exchange"):
            q.traceable = False
            q.reasons.append("not traceable: missing source_id/exchange")

        if not source_live:
            q.consistent = False
            q.reasons.append("inconsistent: cached/degraded source")

        flags = [
            q.complete,
            q.accurate,
            q.timely,
            q.consistent,
            q.normalized,
            q.traceable,
        ]
        failed = flags.count(False)
        if failed:
            q.degraded = True
            q.confidence = max(0.0, 1.0 - 0.15 * failed)
        return q


def _parse_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
