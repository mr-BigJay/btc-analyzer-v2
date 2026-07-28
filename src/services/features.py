"""Feature engineering service facade (Ch.13)."""

from __future__ import annotations

from typing import Any

from src.features.engine import FeatureEngineeringEngine
from src.features.store import feature_store_memory
from src.features.validation import feature_quarantine
from src.storage.repository import CentralRepository


class FeatureService:
    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.engine = FeatureEngineeringEngine(repository)

    def engineer(self, **kwargs: Any) -> dict[str, Any]:
        result = self.engine.engineer(**kwargs)
        if isinstance(result, dict):
            return result
        return result.to_dict()

    def latest(self, asset: str = "BTCUSDT", timeframe: str = "1h") -> dict[str, Any] | None:
        fs = feature_store_memory.get(asset, timeframe)
        return fs.to_dict() if fs else None

    def status(self) -> dict[str, Any]:
        recent = feature_store_memory.recent(limit=5)
        return {
            "quarantine_count": feature_quarantine.count(),
            "recent_count": len(recent),
            "latest": recent[-1] if recent else None,
        }
