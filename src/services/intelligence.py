"""Market Intelligence service facade (Ch.8)."""

from __future__ import annotations

from typing import Any

from src.intelligence.engine import MarketIntelligenceEngine
from src.storage.repository import CentralRepository


class IntelligenceService:
    """Runs Market Intelligence Framework on Analysis Engine output."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.engine = MarketIntelligenceEngine(self.repository)

    def run(
        self,
        *,
        timeframe: str = "1h",
        multi_timeframe: bool = True,
        near_options_expiry: bool = False,
        macro_event: bool = False,
        persist: bool = True,
    ) -> dict[str, Any]:
        out = self.engine.evaluate(
            timeframe=timeframe,
            multi_timeframe=multi_timeframe,
            near_options_expiry=near_options_expiry,
            macro_event=macro_event,
            persist=persist,
        )
        return out.to_dict()
