"""Analysis Engine contracts (Ch.6 §6.5 / §6.11)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from src.core.contracts import utc_now_iso


class SignalBias(str, Enum):
    BULLISH = "Bullish"
    SLIGHTLY_BULLISH = "Slightly Bullish"
    NEUTRAL = "Neutral"
    SLIGHTLY_BEARISH = "Slightly Bearish"
    BEARISH = "Bearish"
    HIGH_UNCERTAINTY = "High Uncertainty"


class Strength(str, Enum):
    VERY_WEAK = "Very Weak"
    WEAK = "Weak"
    NEUTRAL = "Neutral"
    STRONG = "Strong"
    VERY_STRONG = "Very Strong"


def strength_from_confidence(confidence: float) -> Strength:
    c = max(0.0, min(100.0, float(confidence)))
    if c <= 20:
        return Strength.VERY_WEAK
    if c <= 40:
        return Strength.WEAK
    if c <= 60:
        return Strength.NEUTRAL
    if c <= 80:
        return Strength.STRONG
    return Strength.VERY_STRONG


@dataclass
class LayerResult:
    """Standard analysis object returned by every layer (Ch.6 §6.5)."""

    layer: str
    signal: str = SignalBias.NEUTRAL.value
    confidence: float = 50.0
    strength: str = Strength.NEUTRAL.value
    summary: str = ""
    timeframe: str = "1h"
    details: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    data_quality: float = 1.0  # 0–1

    def __post_init__(self) -> None:
        self.confidence = float(max(0.0, min(100.0, self.confidence)))
        if not self.strength or self.strength == Strength.NEUTRAL.value:
            self.strength = strength_from_confidence(self.confidence).value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def signed_score(self) -> float:
        """Map signal+confidence to [-1, 1] for aggregation."""
        s = self.signal
        c = self.confidence / 100.0
        if s in (SignalBias.BULLISH.value, "bullish"):
            return c
        if s in (SignalBias.SLIGHTLY_BULLISH.value, "slightly_bullish"):
            return 0.5 * c
        if s in (SignalBias.BEARISH.value, "bearish"):
            return -c
        if s in (SignalBias.SLIGHTLY_BEARISH.value, "slightly_bearish"):
            return -0.5 * c
        if s in (SignalBias.HIGH_UNCERTAINTY.value, "high_uncertainty"):
            return 0.0
        return 0.0


@dataclass
class Scenario:
    name: str
    probability: float
    trigger: str = ""
    target_zones: list[float] = field(default_factory=list)
    invalidation: float | None = None
    confidence: float = 50.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MarketAnalysisOutput:
    """Unified Analysis Engine output for the AI layer (Ch.6 §6.11)."""

    market_bias: str = SignalBias.NEUTRAL.value
    confidence: float = 50.0
    market_regime: str = "Range"
    volatility: str = "Medium"
    primary_scenario: str = "Sideways Consolidation"
    risk_level: str = "Moderate"
    layer_results: list[dict[str, Any]] = field(default_factory=list)
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)
    timeframe_alignment: dict[str, Any] = field(default_factory=dict)
    symbol: str = "BTCUSDT"
    analyzed_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
