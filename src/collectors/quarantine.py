"""Validation quarantine — invalid records never reach analysis (Ch.12 §12.10)."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class QuarantineRecord:
    id: str
    source: str
    reason: str
    codes: list[str]
    payload: dict[str, Any]
    quarantined_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "reason": self.reason,
            "codes": self.codes,
            "payload": self.payload,
            "quarantined_at": self.quarantined_at,
        }


class QuarantineStore:
    """In-memory quarantine ring buffer (DB persistence optional later)."""

    def __init__(self, *, maxlen: int = 500) -> None:
        self._items: deque[QuarantineRecord] = deque(maxlen=maxlen)
        self._lock = threading.RLock()

    def add(
        self,
        *,
        source: str,
        payload: dict[str, Any],
        codes: list[str],
        reason: str | None = None,
    ) -> QuarantineRecord:
        rec = QuarantineRecord(
            id=str(uuid4()),
            source=source,
            reason=reason or (", ".join(codes) if codes else "validation_failed"),
            codes=list(codes),
            payload=payload,
        )
        with self._lock:
            self._items.append(rec)
        return rec

    def list(self, *, limit: int = 50, source: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._items)
        if source:
            items = [i for i in items if i.source == source]
        return [i.to_dict() for i in items[-limit:]]

    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


quarantine_store = QuarantineStore()
