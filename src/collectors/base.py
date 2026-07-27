"""Base collector — independent, resilient, never stops the system (Ch.3)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.core import ModuleResult, ModuleStatus
from src.storage.repository import CentralRepository

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseCollector(ABC, Generic[T]):
    """Every exchange collector inherits this pattern.

    Collectors must not communicate with each other (Ch.3 §3.5).
    """

    MODULE: str = "Base"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()

    @abstractmethod
    def collect(self) -> ModuleResult[T]:
        """Live collection — raise on hard failure so resilient path can fall back."""

    def _rebuild_data(self, raw: dict) -> T | None:
        """Override when typed domain objects are required from cache."""
        return None

    def fallback_from_cache(self, error: Exception | str | None = None) -> ModuleResult[T]:
        """Ch.3 §3.15: after retries fail → cached snapshot → log warning → continue."""
        exc_txt = str(error) if error else "unknown error"
        logger.warning("%s falling back to cache: %s", self.MODULE, exc_txt)
        cached = self.repository.load_snapshot(self.MODULE)
        if cached:
            raw = cached.get("data") if isinstance(cached.get("data"), dict) else {}
            data = self._rebuild_data(raw or {})
            return ModuleResult(
                module=self.MODULE,
                status=ModuleStatus.DEGRADED,
                confidence=max(0.0, float(cached.get("confidence", 0.5)) * 0.7),
                data=data,
                warning=f"{self.MODULE} offline — using cached snapshot ({exc_txt})",
                source_live=False,
                error_code=type(error).__name__ if isinstance(error, Exception) else "CACHE_FALLBACK",
            )
        return ModuleResult(
            module=self.MODULE,
            status=ModuleStatus.ERROR,
            confidence=0.0,
            data=None,
            warning=exc_txt,
            source_live=False,
            error_code=type(error).__name__ if isinstance(error, Exception) else "NO_CACHE",
        )

    def collect_resilient(self) -> ModuleResult[T]:
        """Live → cache snapshot → DEGRADED / ERROR. Never halt the platform."""
        try:
            result = self.collect()
            if result.status == ModuleStatus.OK and result.data is not None:
                self.repository.save_snapshot(self.MODULE, result.to_dict())
                self.repository.cache_hot(self.MODULE, result.to_dict())
            return result
        except Exception as exc:  # noqa: BLE001
            return self.fallback_from_cache(exc)
