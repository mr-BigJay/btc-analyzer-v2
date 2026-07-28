"""ExchangeCollector interface (Ch.12 §12.5).

Every exchange adapter implements the same lifecycle:
connect → collect → validate → normalize → publish
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from src.core import ModuleResult

T = TypeVar("T")


class ExchangeCollector(ABC, Generic[T]):
    """Provider-agnostic collector contract (Ch.12 §12.5).

    Collectors operate independently and can restart without affecting others.
    No collector may call another collector or exchange API outside its adapter.
    """

    MODULE: str = "Exchange"
    MARKET: str = "Unknown"  # Spot | Futures | Options | Volatility | Macro | Narrative

    @abstractmethod
    def connect(self) -> bool:
        """Establish / verify connectivity (REST probe or WS handshake)."""

    @abstractmethod
    def collect(self) -> ModuleResult[T]:
        """Acquire raw market payload from the provider."""

    def validate(self, payload: dict[str, Any]) -> Any:
        """Run integrity checks. Override or delegate to DataValidator."""
        from src.pipeline.validation import DataValidator

        return DataValidator().validate(self.MODULE.lower(), payload)

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Map provider fields into the internal contract."""
        from src.collectors.contract import stamp_contract
        from src.pipeline.normalization import DataNormalizer

        record = DataNormalizer().normalize_record(self.MODULE.lower(), payload)
        out = record.to_dict() | {k: v for k, v in payload.items() if not str(k).startswith("_")}
        return stamp_contract(
            out,
            source=self.MODULE,
            market=self.MARKET,
            asset=out.get("symbol") or payload.get("symbol"),
        )

    def publish(self, normalized: dict[str, Any]) -> None:
        """Emit internal event after successful normalize (Ch.12 §12.15)."""
        from src.collectors.events import event_bus

        domain = self.MARKET.lower().replace(" ", "_")
        event_bus.publish(
            f"market.{domain}.updated",
            asset=str(normalized.get("asset") or normalized.get("symbol") or "BTCUSDT"),
            payload=normalized,
            source=self.MODULE,
        )
