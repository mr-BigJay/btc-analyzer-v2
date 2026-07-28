"""Risk Management contracts (Ch.15)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

RISK_SCHEMA_VERSION = "1.0"
RISK_ENGINE_VERSION = "1.0"


class RiskLevel(str, Enum):
    VERY_LOW = "Very Low"
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    EXTREME = "Extreme"


class LiquidityState(str, Enum):
    HEALTHY = "Healthy"
    ACCEPTABLE = "Acceptable"
    THIN = "Thin"
    CRITICAL = "Critical"


class VolatilityAdjustment(str, Enum):
    NEUTRAL = "Neutral"
    SLIGHT_REDUCTION = "Slight reduction"
    NONE = "No adjustment"
    REDUCED = "Reduced"
    SIGNIFICANT_REDUCTION = "Significant reduction"


class EventRisk(str, Enum):
    LOW = "Low"
    ELEVATED = "Elevated"
    HIGH = "High"


class LeverageEnvironment(str, Enum):
    CONSERVATIVE = "Conservative conditions"
    NORMAL = "Normal conditions"
    ELEVATED = "Elevated leverage risk"
    EXTREME = "Extreme leverage risk"


class StopNoise(str, Enum):
    STABLE = "Stable"
    INCREASED_NOISE = "Increased Noise"
    HIGH_STOP_OUT = "High Stop-Out Probability"


class RiskReward(str, Enum):
    FAVORABLE = "Favorable"
    BALANCED = "Balanced"
    UNFAVORABLE = "Unfavorable"


class CapitalMode(str, Enum):
    NORMAL = "Normal"
    REDUCED = "Reduced"
    PRESERVATION = "Preservation"
    LOCKDOWN = "Lockdown"


class ExposureBand(str, Enum):
    FULL = "Full allocation"
    MODERATE = "Moderate allocation"
    REDUCED = "Reduced allocation"
    MINIMAL = "Minimal allocation"
    NONE = "No new position"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def crs_to_level(crs: float) -> str:
    s = float(crs)
    if s <= 20:
        return RiskLevel.VERY_LOW.value
    if s <= 40:
        return RiskLevel.LOW.value
    if s <= 60:
        return RiskLevel.MODERATE.value
    if s <= 80:
        return RiskLevel.HIGH.value
    return RiskLevel.EXTREME.value


@dataclass
class CategoryScore:
    name: str
    score: float  # 0–100
    label: str = ""
    drivers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskObject:
    """Standard Risk Object (Ch.15 §15.18) — part of the final decision package."""

    composite_risk_score: float = 40.0
    risk_level: str = RiskLevel.MODERATE.value
    liquidity_state: str = LiquidityState.ACCEPTABLE.value
    volatility_adjustment: str = VolatilityAdjustment.NONE.value
    event_risk: str = EventRisk.LOW.value
    leverage_environment: str = LeverageEnvironment.NORMAL.value
    no_trade_zone: bool = False
    no_trade_reasons: list[str] = field(default_factory=list)
    capital_preservation_mode: str = CapitalMode.NORMAL.value
    suggested_exposure: str = ExposureBand.MODERATE.value
    exposure_fraction: float = 0.5  # 0–1 guidance only
    stop_noise: str = StopNoise.STABLE.value
    risk_reward: str = RiskReward.BALANCED.value
    confidence_risk_guidance: str = ""
    category_scores: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    suppressed: bool = False
    suppression_log: list[str] = field(default_factory=list)
    schema_version: str = RISK_SCHEMA_VERSION
    engine_version: str = RISK_ENGINE_VERSION
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RiskObject":
        raw = dict(data or {})
        allowed = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in raw.items() if k in allowed})

