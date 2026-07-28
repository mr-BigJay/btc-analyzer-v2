"""Immutable security audit trail (Ch.19 §19.14)."""

from __future__ import annotations

from collections import deque
from typing import Any

from src.security.contracts import AuditAction, AuditRecord, utc_now_iso
from src.security.secrets import mask_secrets
from src.storage.redis_cache import redis_cache

AUDIT_KEY = "security:audit_trail"
MAX_MEMORY = 1000


class AuditTrail:
    """Append-only audit log — records are never mutated in place."""

    def __init__(self, *, maxlen: int = MAX_MEMORY) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def append(
        self,
        action: str | AuditAction,
        *,
        actor: str = "anonymous",
        role: str = "",
        outcome: str = "success",
        resource: str = "",
        detail: str = "",
        request_id: str = "",
        ip: str = "",
        persist: bool = True,
    ) -> AuditRecord:
        action_s = action.value if isinstance(action, AuditAction) else str(action)
        record = AuditRecord(
            action=action_s,
            actor=actor,
            role=role,
            outcome=outcome,
            resource=resource,
            detail=mask_secrets(detail)[:500],
            request_id=request_id,
            ip=ip,
            timestamp=utc_now_iso(),
        )
        payload = record.to_dict()
        self._items.appendleft(payload)
        if persist:
            cached = redis_cache.get(AUDIT_KEY)
            rows = list(cached) if isinstance(cached, list) else []
            rows.insert(0, payload)
            redis_cache.set(AUDIT_KEY, rows[:MAX_MEMORY], ttl_sec=86400 * 30)
        return record

    def list(self, *, limit: int = 50, action: str | None = None) -> list[dict[str, Any]]:
        items = list(self._items)
        if not items:
            cached = redis_cache.get(AUDIT_KEY)
            items = list(cached) if isinstance(cached, list) else []
        out = []
        for row in items:
            if action and row.get("action") != action:
                continue
            out.append(row)
            if len(out) >= limit:
                break
        return out


audit_trail = AuditTrail()
