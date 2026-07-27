"""Technical analysis layer.

Responsibility (Doc 01 §4):
  Market structure, support/resistance, patterns, indicators.
  Pattern detection alone must never trigger a trade (Doc 01 §6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TechnicalEvidence:
    """Structured technical-structure evidence."""

    timeframe: str = "1d"
    structure_bias: str = "neutral"  # bullish | bearish | neutral
    support: float | None = None
    resistance: float | None = None
    patterns: list[str] = field(default_factory=list)
    indicators: dict = field(default_factory=dict)
    invalidation: float | None = None
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = "technical"


class TechnicalAnalyzer:
    """Analyzes market structure across timeframes.

    Implementation details arrive in later design documents.
    """

    def analyze(self, timeframe: str = "1d") -> TechnicalEvidence:
        raise NotImplementedError("Awaiting Design Doc 02+ for technical layer spec")
