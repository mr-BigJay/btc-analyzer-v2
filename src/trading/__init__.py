"""Intraday Trading Plan (Doc 01 §5, §8).

Generated only after a Daily Outlook exists.
Refines entry timing with lower timeframes, order flow, confirmations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.outlook import DailyOutlook


@dataclass
class TradingPlan:
    """Actionable intraday plan — still requires Bitunix validation."""

    direction: str = "no_trade"  # long | short | no_trade
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    stop_loss: float | None = None
    take_profits: list[float] = field(default_factory=list)
    confidence: float = 0.0
    risk_reward: float | None = None
    outlook_date: str = ""
    invalidation: float | None = None
    notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TradingPlanGenerator:
    """Builds Intraday Trading Plan from an existing Daily Outlook.

    Implementation details arrive in later design documents.
    """

    def generate(self, outlook: DailyOutlook) -> TradingPlan:
        if outlook is None:
            raise ValueError("Intraday plan requires an existing Daily Outlook (Doc 01 §8)")
        raise NotImplementedError("Awaiting Design Doc 02+ for Intraday Trading Plan spec")
