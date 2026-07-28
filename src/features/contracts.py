"""Feature engineering contracts (Ch.13)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

FEATURE_SCHEMA_VERSION = "1.0"
CALCULATION_ENGINE_VERSION = "1.0"
FEATURE_SET_VERSION = "1.0"

TIMEFRAMES = ("5m", "15m", "1h", "4h", "1D")


class FeatureCategory(str, Enum):
    PRICE = "price"
    VOLUME = "volume"
    DERIVATIVES = "derivatives"
    OPTIONS = "options"
    TECHNICAL = "technical"
    STRUCTURAL = "structural"
    LIQUIDITY = "liquidity"
    VOLATILITY = "volatility"
    COMPOSITE = "composite"


class FeatureScale(str, Enum):
    DIRECTIONAL = "directional"  # -100 .. +100
    PROBABILITY = "probability"  # 0 .. 100
    RATIO = "ratio"  # 0 .. 1
    RAW = "raw"
    CATEGORICAL = "categorical"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class FeatureLineage:
    feature: str
    parents: list[str] = field(default_factory=list)
    source: str | None = None  # e.g. Binance Spot API

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FeatureRecord:
    name: str
    value: float | str | None
    category: str
    scale: str = FeatureScale.RAW.value
    asset: str = "BTCUSDT"
    timeframe: str = "1h"
    timestamp: str = field(default_factory=utc_now_iso)
    feature_version: str = FEATURE_SET_VERSION
    calculation_engine: str = CALCULATION_ENGINE_VERSION
    lineage: FeatureLineage | None = None
    flagged_outlier: bool = False
    missing: bool = False
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.lineage is not None:
            d["lineage"] = self.lineage.to_dict()
        return d


@dataclass
class FeatureSet:
    """All engineered features for one asset/timeframe snapshot."""

    asset: str = "BTCUSDT"
    timeframe: str = "1h"
    timestamp: str = field(default_factory=utc_now_iso)
    features: dict[str, FeatureRecord] = field(default_factory=dict)
    composites: dict[str, float | None] = field(default_factory=dict)
    outputs: dict[str, float | str | None] = field(default_factory=dict)
    missing_count: int = 0
    outlier_flags: list[str] = field(default_factory=list)
    data_quality: float = 1.0
    schema_version: str = FEATURE_SCHEMA_VERSION
    feature_version: str = FEATURE_SET_VERSION
    calculation_engine: str = CALCULATION_ENGINE_VERSION
    generated_at: str = field(default_factory=utc_now_iso)
    elapsed_ms: float | None = None
    valid: bool = True
    quarantine_ids: list[str] = field(default_factory=list)

    def get(self, name: str) -> float | str | None:
        rec = self.features.get(name)
        return None if rec is None else rec.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "features": {k: v.to_dict() for k, v in self.features.items()},
            "composites": self.composites,
            "outputs": self.outputs,
            "missing_count": self.missing_count,
            "outlier_flags": self.outlier_flags,
            "data_quality": self.data_quality,
            "schema_version": self.schema_version,
            "feature_version": self.feature_version,
            "calculation_engine": self.calculation_engine,
            "generated_at": self.generated_at,
            "elapsed_ms": self.elapsed_ms,
            "valid": self.valid,
            "quarantine_ids": self.quarantine_ids,
        }
