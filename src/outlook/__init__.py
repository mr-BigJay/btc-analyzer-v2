"""Daily Outlook — strategic map (Ch.1 §1.8).

Scheduled 03:30. Not a direct trade signal.
Intraday plans may only be generated after an outlook exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.engine import DecisionResult


@dataclass
class Scenario:
    """Main or Alternative scenario (Ch.1 §1.8)."""

    name: str  # main | alternative | bull | bear
    probability: float
    description: str
    expected_high: float | None = None
    expected_low: float | None = None
    expected_close: float | None = None


@dataclass
class DailyOutlook:
    """Strategic daily report — Ch.1 §1.8 Expected Output."""

    date: str = ""
    market_bias: str = "neutral"
    expected_candle: str = "doji"  # green | red | doji
    expected_high: float | None = None
    expected_low: float | None = None
    expected_close: float | None = None
    bullish_probability: float = 0.5
    bearish_probability: float = 0.5
    support: float | None = None
    resistance: float | None = None
    main_scenario: Scenario | None = None
    alternative_scenario: Scenario | None = None
    risk_factors: list[str] = field(default_factory=list)
    preferred_direction: str = "no_trade"
    invalidation: float | None = None
    summary: str = ""
    rationale: str = ""  # Transparency principle
    decision: DecisionResult | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OutlookGenerator:
    """Builds Daily Outlook from DecisionEngine output.

    Spec details arrive in later chapters.
    """

    def generate(self, decision: DecisionResult) -> DailyOutlook:
        raise NotImplementedError("Awaiting Design Book Chapter 2+")
