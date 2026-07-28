"""Decision service facade (Ch.5 / Ch.7) — AI Decision Engine."""

from __future__ import annotations

from typing import Any

from src.ai.engine import AIDecisionEngine
from src.storage.repository import CentralRepository


class DecisionService:
    """Runs AI Decision Engine on Analysis Engine output — never collectors."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.engine = AIDecisionEngine(self.repository)

    def run(
        self,
        *,
        timeframe: str = "1h",
        multi_timeframe: bool = True,
        near_options_expiry: bool = False,
        macro_event: bool = False,
        persist: bool = True,
    ) -> dict[str, Any]:
        report = self.engine.decide(
            timeframe=timeframe,
            multi_timeframe=multi_timeframe,
            near_options_expiry=near_options_expiry,
            macro_event=macro_event,
            persist=persist,
        )
        return report.to_dict()

    def outlook(self, **kwargs: Any) -> dict[str, Any]:
        return self.run(**kwargs).get("daily_outlook") or {}

    def trading_plan(self, **kwargs: Any) -> dict[str, Any]:
        return self.run(**kwargs).get("trading_plan") or {}
