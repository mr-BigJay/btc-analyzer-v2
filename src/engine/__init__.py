"""AI Decision Engine — Analysis + Probability (Ch.1 §1.5–§1.7).

Principles:
  - Evidence-Based Analysis
  - Probability Over Prediction
  - Transparency (every result carries rationale)
  - Risk First
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.pipeline.normalization import NormalizedSnapshot


@dataclass
class LayerVerdict:
    """Transparent per-layer contribution (Ch.1 Transparency principle)."""

    layer: str
    bias: str  # bullish | bearish | neutral
    weight: float
    score: float
    rationale: str


@dataclass
class DecisionResult:
    """Probabilistic decision output — not a trade order (DSS)."""

    bias: str = "neutral"
    bullish_probability: float = 0.5
    bearish_probability: float = 0.5
    confidence: float = 0.0
    preferred_direction: str = "no_trade"  # long | short | no_trade
    layer_verdicts: list[LayerVerdict] = field(default_factory=list)
    confirming_layers: list[str] = field(default_factory=list)
    conflicting_layers: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    rationale: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def is_trade_eligible(self) -> bool:
        """Risk-first multi-evidence gate (Ch.1 §1.5)."""
        return (
            self.preferred_direction in ("long", "short")
            and len(self.confirming_layers) >= 3
            and self.confidence >= 0.55
            and not any(f.startswith("BLOCK:") for f in self.risk_flags)
        )


class AnalysisEngine:
    """Interprets normalized evidence into per-layer verdicts.

    Spec details arrive in later chapters.
    """

    def analyze(self, snapshot: NormalizedSnapshot) -> list[LayerVerdict]:
        raise NotImplementedError("Awaiting Design Book Chapter 2+")


class ProbabilityEngine:
    """Converts layer verdicts into calibrated probabilities.

    Probability Over Prediction (Ch.1 §1.5) — never absolute claims.
    """

    def estimate(self, verdicts: list[LayerVerdict]) -> DecisionResult:
        raise NotImplementedError("Awaiting Design Book Chapter 2+")


class DecisionEngine:
    """Orchestrates AnalysisEngine → ProbabilityEngine."""

    def __init__(self) -> None:
        self.analysis = AnalysisEngine()
        self.probability = ProbabilityEngine()

    def evaluate(self, snapshot: NormalizedSnapshot) -> DecisionResult:
        verdicts = self.analysis.analyze(snapshot)
        return self.probability.estimate(verdicts)
