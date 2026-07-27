"""Bitunix — execution validation only (Ch.2 Design Rule 7).

NOT the primary market reference (Binance is — Rule 8).
Validates a Trading Plan before any position is opened.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core import ModuleResult, ModuleStatus, utc_now_iso
from src.trading import TradingPlan


@dataclass
class ExecutionValidation:
    approved: bool = False
    reasons: list[str] = field(default_factory=list)
    plan: TradingPlan | None = None
    validated_at: str = field(default_factory=utc_now_iso)


class BitunixValidator:
    MODULE = "Bitunix"

    def validate(self, plan: TradingPlan) -> ModuleResult[ExecutionValidation]:
        raise NotImplementedError("Awaiting Design Book Chapter 3+")

    def reject(self, plan: TradingPlan, reason: str) -> ModuleResult[ExecutionValidation]:
        return ModuleResult(
            module=self.MODULE,
            status=ModuleStatus.OK,
            confidence=1.0,
            data=ExecutionValidation(approved=False, reasons=[reason], plan=plan),
        )
