"""Execution layer — Bitunix validation (Doc 01 §3–§4).

Validates a Trading Plan before any position is opened.
Does not invent signals; only gates execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.trading import TradingPlan


@dataclass
class ExecutionValidation:
    """Result of pre-trade validation on Bitunix."""

    approved: bool = False
    reasons: list[str] = field(default_factory=list)
    plan: TradingPlan | None = None
    validated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = "bitunix"


class BitunixValidator:
    """Validates trading plans against Bitunix execution constraints.

    Implementation details arrive in later design documents.
    """

    def validate(self, plan: TradingPlan) -> ExecutionValidation:
        raise NotImplementedError("Awaiting Design Doc 02+ for Bitunix execution spec")
