"""Binance Futures collector — Layer 2 Collection (Ch.2 §2.5).

Purpose: Market Reference (Design Rule 8 — primary futures reference).
Output: ModuleResult[FlowObject]
Funding analysis stays here — never in Technical (High Cohesion).
"""

from __future__ import annotations

from src.core import FlowObject, ModuleResult, ModuleStatus
from src.storage.repository import CentralRepository


class BinanceFuturesCollector:
    """Collects Binance Futures market-reference data."""

    MODULE = "Binance"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()

    def collect(self) -> ModuleResult[FlowObject]:
        raise NotImplementedError("Awaiting Design Book Chapter 3+")

    def collect_resilient(self) -> ModuleResult[FlowObject]:
        try:
            result = self.collect()
            self.repository.save_snapshot(self.MODULE, result.to_dict())
            return result
        except Exception as exc:  # noqa: BLE001
            cached = self.repository.load_snapshot(self.MODULE)
            if cached:
                raw = cached.get("data", {}) if isinstance(cached.get("data"), dict) else {}
                return ModuleResult(
                    module=self.MODULE,
                    status=ModuleStatus.DEGRADED,
                    confidence=max(0.0, float(cached.get("confidence", 0.5)) * 0.7),
                    data=FlowObject(**{k: v for k, v in raw.items() if k in FlowObject.__dataclass_fields__}),
                    warning=f"{self.MODULE} offline — using cached snapshot ({exc})",
                    source_live=False,
                )
            return ModuleResult(
                module=self.MODULE,
                status=ModuleStatus.ERROR,
                confidence=0.0,
                data=FlowObject(),
                warning=str(exc),
                source_live=False,
            )
