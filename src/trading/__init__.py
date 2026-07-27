"""Intraday Trading Plan — tactical report (Ch.1 §1.8 / Ch.7 §7.14).

Generated only after a Daily Outlook exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.outlook import DailyOutlook, OutlookGenerator


@dataclass
class TradingPlan:
    """Tactical plan — Ch.7 §7.14. Advisory only."""

    direction: str = "no_trade"  # long | short | no_trade
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    stop_loss: float | None = None
    take_profits: list[float] = field(default_factory=list)
    risk_reward: float | None = None
    confidence: float = 0.0
    invalidation: float | None = None
    outlook_date: str = ""
    rationale: str = ""
    notes: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TradingPlanGenerator:
    """Builds Intraday Trading Plan from an existing Daily Outlook."""

    def generate(self, outlook: DailyOutlook) -> TradingPlan:
        if outlook is None:
            raise ValueError("Intraday plan requires an existing Daily Outlook (Ch.1 §1.8 / Ch.7 §7.14)")

        report = outlook.payload or {}
        if not report:
            # Ensure outlook exists via generator path
            report = OutlookGenerator().generate().payload

        plan = report.get("trading_plan") or (outlook.payload.get("trading_plan") if outlook.payload else {}) or {}
        entry = plan.get("entry_zone") or []
        return TradingPlan(
            direction=str(plan.get("preferred_direction") or outlook.preferred_direction or "no_trade"),
            entry_zone_low=entry[0] if len(entry) > 0 else None,
            entry_zone_high=entry[1] if len(entry) > 1 else None,
            stop_loss=plan.get("stop_loss_zone"),
            take_profits=list(plan.get("target_levels") or []),
            risk_reward=plan.get("risk_reward"),
            confidence=float(plan.get("confidence") or outlook.payload.get("confidence") or 0),
            invalidation=plan.get("invalidation") or outlook.invalidation,
            outlook_date=outlook.date,
            rationale=str((report.get("reasoning") or {}).get("primary_conclusion") or outlook.rationale),
            notes=str(plan.get("session_notes") or ""),
            payload=plan,
        )
