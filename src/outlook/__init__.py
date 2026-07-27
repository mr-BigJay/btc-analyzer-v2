"""Daily Outlook — strategic map for the day (Doc 01 §5, §7).

Scheduled ~03:30 UTC. Not a direct trade signal.
Intraday plans may only be generated after an outlook exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.engine import DecisionResult


@dataclass
class Scenario:
    name: str  # base | bull | bear
    probability: float
    description: str
    target_high: float | None = None
    target_low: float | None = None
    expected_close: float | None = None


@dataclass
class DailyOutlook:
    """Strategic daily map — Doc 01 §5 / §7."""

    date: str = ""
    market_bias: str = "neutral"
    bullish_probability: float = 0.5
    bearish_probability: float = 0.5
    expected_candle: str = "doji"  # green | red | doji
    expected_high: float | None = None
    expected_low: float | None = None
    expected_close: float | None = None
    support: float | None = None
    resistance: float | None = None
    preferred_direction: str = "no_trade"
    scenarios: list[Scenario] = field(default_factory=list)
    invalidation: float | None = None
    risk_factors: list[str] = field(default_factory=list)
    summary: str = ""
    decision: DecisionResult | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OutlookGenerator:
    """Builds Daily Outlook from DecisionEngine output.

    Implementation details arrive in later design documents.
    """

    def generate(self, decision: DecisionResult) -> DailyOutlook:
        raise NotImplementedError("Awaiting Design Doc 02+ for Daily Outlook spec")
