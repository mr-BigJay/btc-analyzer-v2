"""AI Decision Engine contracts (Ch.7 §7.16)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from src.core.contracts import utc_now_iso


class RiskCategory(str, Enum):
    LOW = "Low Risk"
    MODERATE = "Moderate Risk"
    ELEVATED = "Elevated Risk"
    HIGH = "High Risk"
    EXTREME = "Extreme Risk"


class ConfidenceBand(str, Enum):
    EXCEPTIONAL = "Exceptional agreement"
    VERY_HIGH = "Very High"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low confidence"


def confidence_band(score: float) -> ConfidenceBand:
    c = float(score)
    if c >= 90:
        return ConfidenceBand.EXCEPTIONAL
    if c >= 80:
        return ConfidenceBand.VERY_HIGH
    if c >= 70:
        return ConfidenceBand.HIGH
    if c >= 60:
        return ConfidenceBand.MODERATE
    return ConfidenceBand.LOW


@dataclass
class EvidenceItem:
    layer: str
    evidence: str
    signal: str
    confidence: float
    priority: float = 0.5  # 0–1 after prioritization
    tags: list[str] = field(default_factory=list)
    data_quality: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioAssessment:
    name: str
    probability: float
    trigger: str = ""
    supporting_evidence: list[str] = field(default_factory=list)
    invalidating_evidence: list[str] = field(default_factory=list)
    risk_level: str = RiskCategory.MODERATE.value
    time_horizon: str = "1–3 sessions"
    target_zones: list[float] = field(default_factory=list)
    invalidation: float | None = None
    confidence: float = 50.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReasoningBlock:
    """Explainability payload (Ch.7 §7.12) — required with every conclusion."""

    primary_conclusion: str = ""
    supporting_evidence: list[str] = field(default_factory=list)
    conflicting_evidence: list[str] = field(default_factory=list)
    confidence_explanation: str = ""
    risk_explanation: str = ""
    conflict_narrative: str = ""
    uncertainty_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TradingPlanSpec:
    """Intraday Trading Plan (Ch.7 §7.14) — advisory only."""

    preferred_direction: str = "no_trade"  # long | short | no_trade
    entry_zone: list[float] = field(default_factory=list)
    confirmation_conditions: list[str] = field(default_factory=list)
    target_levels: list[float] = field(default_factory=list)
    stop_loss_zone: float | None = None
    risk_reward: float | None = None
    position_sizing_guidance: str = "Risk ≤1% of equity; never increase leverage on uncertainty."
    session_notes: str = ""
    invalidation: float | None = None
    confidence: float = 0.0
    advisory: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DailyOutlookReport:
    """Flagship Daily Outlook structure (Ch.7 §7.13)."""

    executive_summary: str = ""
    market_bias: str = "Neutral"
    confidence_score: float = 50.0
    market_regime: str = "Range"
    key_drivers: list[str] = field(default_factory=list)
    options_analysis: str = ""
    futures_analysis: str = ""
    technical_summary: str = ""
    liquidity_zones: list[str] = field(default_factory=list)
    major_risks: list[str] = field(default_factory=list)
    primary_scenario: dict[str, Any] = field(default_factory=dict)
    alternative_scenarios: list[dict[str, Any]] = field(default_factory=list)
    trading_plan: dict[str, Any] = field(default_factory=dict)
    invalidation_levels: list[float] = field(default_factory=list)
    final_assessment: str = ""
    date: str = ""
    symbol: str = "BTCUSDT"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AIDecisionReport:
    """Standardized AI report object (Ch.7 §7.16)."""

    market_bias: str = "Neutral"
    confidence: float = 50.0
    confidence_band: str = ConfidenceBand.LOW.value
    market_regime: str = "Range"
    risk_level: str = RiskCategory.MODERATE.value
    primary_narrative: str = "Range / Indecision"
    primary_scenario: str = "Sideways Consolidation"
    alternative_scenarios: list[dict[str, Any]] = field(default_factory=list)
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    key_drivers: list[str] = field(default_factory=list)
    major_risks: list[str] = field(default_factory=list)
    trading_plan: dict[str, Any] = field(default_factory=dict)
    reasoning: dict[str, Any] = field(default_factory=dict)
    daily_outlook: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    probability_distribution: dict[str, float] = field(default_factory=dict)
    market_intelligence: dict[str, Any] = field(default_factory=dict)
    scoring: dict[str, Any] = field(default_factory=dict)
    symbol: str = "BTCUSDT"
    analyzed_at: str = field(default_factory=utc_now_iso)
    analysis_fingerprint: str = ""
    disclaimer: str = (
        "Decision Support System output — advisory only. "
        "Probabilities are evidence-derived, not guarantees. "
        "Never treat high confidence as certainty."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
