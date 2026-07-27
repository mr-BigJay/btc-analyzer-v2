"""Deribit collector — options intelligence.

Responsibility (Doc 01 §4):
  PCR, Max Pain, IV, Gamma, Dealer Position.
  Never produces a trade decision alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class OptionsEvidence:
    """Structured options intelligence from Deribit."""

    currency: str = "BTC"
    put_call_ratio: float | None = None
    max_pain: float | None = None
    iv_rank: float | None = None
    gamma_regime: str = "neutral"  # long_gamma | short_gamma | neutral
    dealer_position_bias: str = "neutral"
    details: dict = field(default_factory=dict)
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = "deribit"


class DeribitOptionsCollector:
    """Collects Deribit options intelligence.

    Implementation details arrive in later design documents.
    """

    def collect(self) -> OptionsEvidence:
        raise NotImplementedError("Awaiting Design Doc 02+ for Deribit options spec")
