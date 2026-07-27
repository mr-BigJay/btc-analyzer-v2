"""AI Decision Engine.

Responsibility (Doc 01 §4–§6):
  Combine independent evidence layers and calculate probabilities.
  A conclusion requires CoinEx + Binance + Deribit + Technical + risk rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.collectors.binance import FuturesEvidence
from src.collectors.coinex import NarrativeEvidence
from src.collectors.deribit import OptionsEvidence
from src.technical import TechnicalEvidence


@dataclass
class EvidenceBundle:
    """All independent evidence layers for one decision cycle."""

    narrative: NarrativeEvidence | None = None
    futures: FuturesEvidence | None = None
    options: OptionsEvidence | None = None
    technical: TechnicalEvidence | None = None


@dataclass
class DecisionResult:
    """Probabilistic decision output — not a trade order."""

    bias: str = "neutral"  # bullish | bearish | neutral
    bullish_probability: float = 0.5
    bearish_probability: float = 0.5
    confidence: float = 0.0
    preferred_direction: str = "no_trade"  # long | short | no_trade
    confirming_layers: list[str] = field(default_factory=list)
    conflicting_layers: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    rationale: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def is_trade_eligible(self) -> bool:
        """Requires multi-layer confirmation (Doc 01 §6)."""
        return (
            self.preferred_direction in ("long", "short")
            and len(self.confirming_layers) >= 3
            and self.confidence >= 0.55
        )


class DecisionEngine:
    """Combines evidence layers into calibrated probabilities.

    Implementation of scoring/weights arrives in later design documents.
    """

    def evaluate(self, evidence: EvidenceBundle) -> DecisionResult:
        raise NotImplementedError("Awaiting Design Doc 02+ for decision engine spec")
