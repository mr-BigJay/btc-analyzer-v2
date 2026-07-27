"""Daily Outlook — strategic map (Ch.1 §1.8 / Ch.7 §7.13).

Scheduled 03:30 UTC. Not a direct trade signal.
Intraday plans may only be generated after an outlook exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.ai.engine import AIDecisionEngine
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
    """Strategic daily report — Ch.7 §7.13."""

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
    rationale: str = ""
    decision: DecisionResult | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OutlookGenerator:
    """Builds Daily Outlook from AI Decision Engine (Ch.7)."""

    def __init__(self) -> None:
        self.ai = AIDecisionEngine()

    def generate(self, decision: DecisionResult | None = None) -> DailyOutlook:
        if decision and decision.report:
            report = decision.report
        else:
            report = self.ai.decide(persist=True).to_dict()

        outlook = report.get("daily_outlook") or {}
        scenarios = report.get("scenarios") or []
        primary = scenarios[0] if scenarios else {}
        alt = scenarios[1] if len(scenarios) > 1 else {}
        dist = report.get("probability_distribution") or {}
        plan = report.get("trading_plan") or {}
        inv = outlook.get("invalidation_levels") or []

        main = Scenario(
            name=str(primary.get("name") or "main"),
            probability=float(primary.get("probability") or 0) / 100.0,
            description=str(primary.get("trigger") or ""),
        )
        alternative = Scenario(
            name=str(alt.get("name") or "alternative"),
            probability=float(alt.get("probability") or 0) / 100.0,
            description=str(alt.get("trigger") or ""),
        )
        bull = float(dist.get("trend_continuation") or primary.get("probability") or 50) / 100.0
        bear = float(dist.get("trend_reversal") or 50) / 100.0
        total = bull + bear or 1.0

        bias = str(report.get("market_bias") or "Neutral").lower().replace(" ", "_")
        candle = "green" if "bullish" in bias else "red" if "bearish" in bias else "doji"

        return DailyOutlook(
            date=str(outlook.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            market_bias=str(report.get("market_bias") or "Neutral"),
            expected_candle=candle,
            bullish_probability=bull / total,
            bearish_probability=bear / total,
            main_scenario=main,
            alternative_scenario=alternative,
            risk_factors=list(report.get("major_risks") or []),
            preferred_direction=str(plan.get("preferred_direction") or "no_trade"),
            invalidation=float(inv[0]) if inv else plan.get("invalidation"),
            summary=str(outlook.get("executive_summary") or ""),
            rationale=str((report.get("reasoning") or {}).get("primary_conclusion") or ""),
            decision=decision,
            payload=report,
        )
