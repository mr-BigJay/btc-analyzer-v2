"""Security service facade (Ch.19)."""

from __future__ import annotations

from typing import Any

from src.security.engine import SecurityEngine


class SecurityService:
    def __init__(self) -> None:
        self.engine = SecurityEngine()

    def status(self) -> dict[str, Any]:
        return self.engine.status()

    def posture(self) -> dict[str, Any]:
        return self.engine.posture()

    def checklist(self, **kwargs: Any) -> dict[str, Any]:
        from src.security.hardening import production_checklist

        return production_checklist(**kwargs)

    def audit(self, *, limit: int = 50, action: str | None = None) -> list[dict[str, Any]]:
        return self.engine.audit_list(limit=limit, action=action)
