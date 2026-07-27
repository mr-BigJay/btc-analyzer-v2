"""Intraday Trading Plan — tactical report (Ch.1 §1.8).

Generated only after a Daily Outlook exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.outlook import DailyOutlook


@dataclass
class TradingPlan:
    """Tactical plan — Ch.1 §1.8. Still requires Bitunix validation."""

    direction: str = "no_trade"  # long | short | no_trade
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    stop_loss: float | None = None
    take_profits: list[float] = field(default_factory=list)
    risk_reward: float | None = None
    confidence: float = 0.0
    invalidation: float | None = None
    outlook_date: str = ""
    rationale: str = ""  # Transparency principle
    notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TradingPlanGenerator:
    """Builds Intraday Trading Plan from an existing Daily Outlook."""

    def generate(self, outlook: DailyOutlook) -> TradingPlan:
        if outlook is None:
            raise ValueError(
                "Intraday plan requires an existing Daily Outlook (Ch.1 §1.8)"
            )
        raise NotImplementedError("Awaiting Design Book Chapter 2+")
