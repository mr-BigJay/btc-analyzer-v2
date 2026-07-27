"""Market Intelligence Framework contracts (Ch.8 §8.15)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from src.core.contracts import utc_now_iso


class MarketRegime(str, Enum):
    STRONG_UPTREND = "Strong Uptrend"
    WEAK_UPTREND = "Weak Uptrend"
    STRONG_DOWNTREND = "Strong Downtrend"
    WEAK_DOWNTREND = "Weak Downtrend"
    RANGE = "Range"
    COMPRESSION = "Compression"
    EXPANSION = "Expansion"
    TRANSITION = "Transition"


class MarketCycle(str, Enum):
    ACCUMULATION = "Accumulation"
    MARKUP = "Markup"
    DISTRIBUTION = "Distribution"
    MARKDOWN = "Markdown"


class Participant(str, Enum):
    RETAIL = "Retail Traders"
    PROFESSIONAL = "Professional Traders"
    WHALES = "Whales"
    INSTITUTIONS = "Institutions"
    OPTIONS_DEALERS = "Options Dealers"


class InstitutionalActivity(str, Enum):
    BUYING = "Buying"
    SELLING = "Selling"
    NEUTRAL = "Neutral Activity"


class VolatilityRegime(str, Enum):
    VERY_LOW = "Very Low"
    LOW = "Low"
    NORMAL = "Normal"
    ELEVATED = "Elevated"
    EXTREME = "Extreme"


class StressLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    ELEVATED = "Elevated"
    HIGH = "High"
    EXTREME = "Extreme"


class HealthBand(str, Enum):
    CRITICAL = "Critical"
    WEAK = "Weak"
    NEUTRAL = "Neutral"
    HEALTHY = "Healthy"
    EXCEPTIONAL = "Exceptional"


def health_band(score: float) -> HealthBand:
    s = float(score)
    if s <= 20:
        return HealthBand.CRITICAL
    if s <= 40:
        return HealthBand.WEAK
    if s <= 60:
        return HealthBand.NEUTRAL
    if s <= 80:
        return HealthBand.HEALTHY
    return HealthBand.EXCEPTIONAL


@dataclass
class MarketIntelligenceOutput:
    """Standardized Market Intelligence object (Ch.8 §8.15)."""

    market_regime: str = MarketRegime.RANGE.value
    market_cycle: str = MarketCycle.ACCUMULATION.value
    dominant_participant: str = Participant.PROFESSIONAL.value
    institutional_activity: str = InstitutionalActivity.NEUTRAL.value
    market_health_index: float = 50.0
    market_health_band: str = HealthBand.NEUTRAL.value
    market_stress_index: str = StressLevel.MODERATE.value
    market_stress_score: float = 40.0
    volatility_regime: str = VolatilityRegime.NORMAL.value
    macro_bias: str = "Neutral"
    cross_asset_bias: str = "Neutral"
    liquidity_state: str = "Balanced"
    transition_probability: float = 20.0
    detected_transitions: list[str] = field(default_factory=list)
    derivatives_thesis: str = ""
    participant_scores: dict[str, float] = field(default_factory=dict)
    macro_events: list[dict[str, Any]] = field(default_factory=list)
    cross_asset: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    data_completeness: float = 1.0
    symbol: str = "BTCUSDT"
    analyzed_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
