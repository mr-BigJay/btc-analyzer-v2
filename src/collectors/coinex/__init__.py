"""CoinEx collector — market narrative analysis.

Responsibility (Doc 01 §4):
  Extract and validate the market narrative.
  Never produces a trade decision alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class NarrativeEvidence:
    """Structured narrative output from CoinEx layer."""

    bias: str = "neutral"  # bullish | bearish | neutral
    themes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = "coinex"


class CoinExCollector:
    """Collects narrative signals from CoinEx.

    Implementation details arrive in later design documents.
    """

    def collect(self) -> NarrativeEvidence:
        raise NotImplementedError("Awaiting Design Doc 02+ for CoinEx narrative spec")
