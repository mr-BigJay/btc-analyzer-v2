"""Scoring & Decision Model contracts (Ch.9 §9.16)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from src.core.contracts import utc_now_iso


class BiasClass(str, Enum):
    STRONG_BULLISH = "Strong Bullish"
    BULLISH = "Bullish"
    SLIGHTLY_BULLISH = "Slightly Bullish"
    NEUTRAL = "Neutral"
    SLIGHTLY_BEARISH = "Slightly Bearish"
    BEARISH = "Bearish"
    STRONG_BEARISH = "Strong Bearish"


class AlignmentClass(str, Enum):
    FULL = "Full Alignment"
    PARTIAL = "Partial Alignment"
    MIXED = "Mixed Alignment"
    DIVERGENCE = "Complete Divergence"


class DataQualityBand(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    ACCEPTABLE = "Acceptable"
    DEGRADED = "Degraded"


LAYER_NAMES = (
    "Spot",
    "Futures",
    "Options",
    "Technical",
    "Market Structure",
    "Liquidity",
    "Pattern Detection",
    "Volatility",
)


def classify_bias(score: float) -> str:
    """Market bias classification from MBS (Ch.9 §9.9)."""
    s = float(score)
    if s >= 75:
        return BiasClass.STRONG_BULLISH.value
    if s >= 40:
        return BiasClass.BULLISH.value
    if s >= 15:
        return BiasClass.SLIGHTLY_BULLISH.value
    if s > -15:
        return BiasClass.NEUTRAL.value
    if s > -40:
        return BiasClass.SLIGHTLY_BEARISH.value
    if s > -75:
        return BiasClass.BEARISH.value
    return BiasClass.STRONG_BEARISH.value


def interpret_layer_score(score: float) -> str:
    s = float(score)
    if s >= 80:
        return "Strong Bullish"
    if s >= 40:
        return "Bullish"
    if s > -40:
        return "Neutral"
    if s > -80:
        return "Bearish"
    return "Strong Bearish"


def dqs_band(score: float) -> str:
    s = float(score)
    if s >= 90:
        return DataQualityBand.EXCELLENT.value
    if s >= 75:
        return DataQualityBand.GOOD.value
    if s >= 60:
        return DataQualityBand.ACCEPTABLE.value
    return DataQualityBand.DEGRADED.value


@dataclass
class DecisionObject:
    """Canonical scoring decision object (Ch.9 §9.16)."""

    market_bias: str = BiasClass.NEUTRAL.value
    market_bias_score: float = 0.0
    confidence_score: float = 50.0
    risk_score: float = 40.0
    market_health_index: float = 50.0
    market_stress_index: float = 40.0
    data_quality_score: float = 80.0
    timeframe_alignment: str = AlignmentClass.PARTIAL.value
    decision: str = BiasClass.NEUTRAL.value
    publish: bool = True
    layer_scores: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    weight_regime: str = "default"
    composite_matrix: dict[str, float] = field(default_factory=dict)
    conflict_penalties: list[dict[str, Any]] = field(default_factory=list)
    publication_notes: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    symbol: str = "BTCUSDT"
    scored_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
