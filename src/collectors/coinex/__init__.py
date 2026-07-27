"""CoinEx collector — Layer 2 Collection (Ch.2 §2.5).

Purpose: daily market narrative.
Output: ModuleResult[NarrativeObject]
No analysis occurs here — raw narrative extraction only.
"""

from __future__ import annotations

from src.core import ModuleResult, ModuleStatus, NarrativeObject
from src.storage.repository import CentralRepository


class CoinExCollector:
    """Collects daily narrative from CoinEx."""

    MODULE = "CoinEx"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()

    def collect(self) -> ModuleResult[NarrativeObject]:
        """Return Narrative Object envelope. Spec in later chapters."""
        raise NotImplementedError("Awaiting Design Book Chapter 3+")

    def collect_resilient(self) -> ModuleResult[NarrativeObject]:
        """Fault-tolerant collect (Ch.2 §2.9): live → cache → DEGRADED."""
        try:
            result = self.collect()
            self.repository.save_snapshot(self.MODULE, result.to_dict())
            return result
        except Exception as exc:  # noqa: BLE001 — provider failure must not stop system
            cached = self.repository.load_snapshot(self.MODULE)
            if cached:
                data = NarrativeObject(**cached.get("data", {})) if isinstance(cached.get("data"), dict) else NarrativeObject()
                return ModuleResult(
                    module=self.MODULE,
                    status=ModuleStatus.DEGRADED,
                    confidence=max(0.0, float(cached.get("confidence", 0.5)) * 0.7),
                    data=data,
                    warning=f"{self.MODULE} offline — using cached snapshot ({exc})",
                    source_live=False,
                )
            return ModuleResult(
                module=self.MODULE,
                status=ModuleStatus.ERROR,
                confidence=0.0,
                data=NarrativeObject(),
                warning=str(exc),
                source_live=False,
            )
