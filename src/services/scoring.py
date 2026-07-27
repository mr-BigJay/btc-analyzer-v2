"""Scoring service facade (Ch.9)."""

from __future__ import annotations

from typing import Any

from src.scoring.engine import ScoringEngine
from src.storage.repository import CentralRepository


class ScoringService:
    """Runs Scoring & Decision Model on Analysis + Intelligence outputs."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.engine = ScoringEngine(self.repository)

    def run(
        self,
        *,
        timeframe: str = "1h",
        multi_timeframe: bool = True,
        near_options_expiry: bool = False,
        macro_event: bool = False,
        persist: bool = True,
    ) -> dict[str, Any]:
        return self.engine.score(
            timeframe=timeframe,
            multi_timeframe=multi_timeframe,
            near_options_expiry=near_options_expiry,
            macro_event=macro_event,
            persist=persist,
        ).to_dict()
