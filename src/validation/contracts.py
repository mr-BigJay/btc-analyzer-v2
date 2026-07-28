"""Validation contracts (Ch.14)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

VALIDATION_SCHEMA_VERSION = "1.0"
ENGINE_VERSION_DEFAULT = "1.0"

HORIZONS = ("1h", "4h", "24h", "7d")
HORIZON_HOURS = {"1h": 1, "4h": 4, "24h": 24, "7d": 168}


class ValidationMethod(str, Enum):
    HISTORICAL = "historical_backtest"
    WALK_FORWARD = "walk_forward"
    PAPER = "paper_trading"
    SHADOW = "shadow_mode"
    CONTINUOUS = "continuous_validation"


class DriftStatus(str, Enum):
    NONE = "none"
    WATCH = "watch"
    REVIEW = "review"


class CalibrationLabel(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    MODERATE = "Moderate"
    POOR = "Poor"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class PredictionRecord:
    """Immutable archived prediction (Ch.14 §14.8)."""

    prediction_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=utc_now_iso)
    symbol: str = "BTCUSDT"
    market_bias: str = "Neutral"
    confidence: float = 50.0
    primary_scenario: str = ""
    risk_level: str = "Moderate"
    market_regime: str = ""
    probability_distribution: dict[str, float] = field(default_factory=dict)
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    layer_scores: dict[str, float] = field(default_factory=dict)
    entry_price: float | None = None
    trading_plan: dict[str, Any] = field(default_factory=dict)
    engine_version: str = ENGINE_VERSION_DEFAULT
    analysis_fingerprint: str | None = None
    feature_version: str | None = None
    source: str = "continuous"  # continuous | backtest | paper | shadow
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutcomeRecord:
    prediction_id: str
    horizon: str
    evaluated_at: str = field(default_factory=utc_now_iso)
    entry_price: float | None = None
    exit_price: float | None = None
    return_pct: float | None = None
    direction_actual: str | None = None  # Bullish | Bearish | Neutral
    direction_correct: bool | None = None
    bias_correct: bool | None = None
    scenario_occurred: bool | None = None
    risk_materialized: bool | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTrade:
    trade_id: str = field(default_factory=lambda: str(uuid4()))
    prediction_id: str | None = None
    entry_timestamp: str = field(default_factory=utc_now_iso)
    entry_price: float | None = None
    stop_loss: float | None = None
    targets: list[float] = field(default_factory=list)
    exit_timestamp: str | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    mfe: float | None = None  # max favorable excursion (pct)
    mae: float | None = None  # max adverse excursion (pct)
    pnl_pct: float | None = None
    direction: str = "no_trade"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationObject:
    """Canonical validation cycle record (Ch.14 §14.22)."""

    engine_version: str = ENGINE_VERSION_DEFAULT
    validation_period: str = ""
    method: str = ValidationMethod.HISTORICAL.value
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    win_rate: float | None = None
    profit_factor: float | None = None
    expectancy: float | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    confidence_calibration: str = CalibrationLabel.MODERATE.value
    market_regime_results: dict[str, Any] = field(default_factory=dict)
    layer_contribution: dict[str, Any] = field(default_factory=dict)
    calibration_bins: dict[str, Any] = field(default_factory=dict)
    drift_detected: bool = False
    drift_status: str = DriftStatus.NONE.value
    known_limitations: list[str] = field(default_factory=list)
    dataset_version: str | None = None
    sample_size: int = 0
    approved: bool = False
    approval_record: dict[str, Any] | None = None
    schema_version: str = VALIDATION_SCHEMA_VERSION
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
