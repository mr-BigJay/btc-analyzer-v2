from dataclasses import dataclass, field
from enum import Enum


class Trend(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"


@dataclass
class LayerScore:
    name: str
    score: float
    weight: float
    details: dict = field(default_factory=dict)


@dataclass
class TimeframeAnalysis:
    timeframe: str
    trend: Trend
    score: float
    confidence: float
    regime: MarketRegime
    price: float
    layers: list[LayerScore]
    indicators: dict
    structure: str
    levels: dict = field(default_factory=dict)


@dataclass
class OnChainContext:
    active_addresses: int | None
    active_addresses_change_pct: float | None
    mvrv: float | None
    mvrv_signal: str
    active_addresses_signal: str


@dataclass
class DerivativesContext:
    funding_rate: float | None
    funding_signal: str
    open_interest_change_pct: float | None
    oi_signal: str
    long_short_ratio: float | None
    ls_signal: str
    taker_buy_sell_ratio: float | None
    taker_signal: str


@dataclass
class SentimentContext:
    fear_greed_value: int | None
    fear_greed_label: str | None
    signal: str


@dataclass
class OverviewAnalysis:
    price: float
    change_24h_pct: float
    overall_score: float
    overall_confidence: float
    summary: str
    mtf_aligned: bool
    timeframes: dict[str, TimeframeAnalysis]
    derivatives: DerivativesContext
    sentiment: SentimentContext
    updated_at: str
    onchain: OnChainContext | None = None
