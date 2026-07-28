"""QA service facade (Ch.22)."""

from __future__ import annotations

from typing import Any

from src.qa.engine import QAEngine


class QAService:
    def __init__(self) -> None:
        self.engine = QAEngine()

    def status(self) -> dict[str, Any]:
        return self.engine.status()

    def report(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.report(**kwargs)

    def gates(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.gates(**kwargs)

    def suite(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.suite(**kwargs)

    def performance(self) -> dict[str, Any]:
        return self.engine.performance()

    def security(self) -> dict[str, Any]:
        return self.engine.security()

    def resilience(self) -> dict[str, Any]:
        return self.engine.resilience()

    def replay(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.replay(**kwargs)

    def defects(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.defects(**kwargs)
