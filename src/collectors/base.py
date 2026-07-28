"""Base collector — independent, resilient, never stops the system (Ch.3 / Ch.12)."""

from __future__ import annotations

import logging
from typing import Any, Generic, TypeVar

from src.collectors.interface import ExchangeCollector
from src.core import ModuleResult, ModuleStatus
from src.storage.repository import CentralRepository

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseCollector(ExchangeCollector[T], Generic[T]):
    """Every exchange collector inherits this pattern.

    Lifecycle: connect → collect → validate → normalize → publish (Ch.12 §12.5).
    Collectors must not communicate with each other (Ch.3 §3.5).
    """

    MODULE: str = "Base"
    MARKET: str = "Futures"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self._connected = False

    def connect(self) -> bool:
        """Default: mark connected. Adapters may probe REST/WS."""
        self._connected = True
        return True

    def collect(self) -> ModuleResult[T]:
        raise NotImplementedError

    def _rebuild_data(self, raw: dict) -> T | None:
        """Override when typed domain objects are required from cache."""
        return None

    def fallback_from_cache(self, error: Exception | str | None = None) -> ModuleResult[T]:
        """Ch.3 §3.15: after retries fail → cached snapshot → log warning → continue."""
        from src.collectors.health import health_monitor

        exc_txt = str(error) if error else "unknown error"
        logger.warning("%s falling back to cache: %s", self.MODULE, exc_txt)
        health_monitor.record_error(self.MODULE.lower().replace(" ", "_"), exc_txt)
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
        from src.collectors.health import health_monitor

        if not self._connected:
            try:
                self.connect()
            except Exception as exc:  # noqa: BLE001
                return self.fallback_from_cache(exc)
        try:
            result = self.collect()
            if result.status == ModuleStatus.OK and result.data is not None:
                self.repository.save_snapshot(self.MODULE, result.to_dict())
                self.repository.cache_hot(self.MODULE, result.to_dict())
                health_monitor.record_success(
                    self.MODULE.lower().replace(" ", "_"),
                    latency_ms=result.response_time_ms,
                )
            elif result.status == ModuleStatus.ERROR:
                health_monitor.record_error(
                    self.MODULE.lower().replace(" ", "_"),
                    result.warning,
                )
            return result
        except Exception as exc:  # noqa: BLE001
            return self.fallback_from_cache(exc)

    def run_pipeline(self, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Full connect→collect→validate→normalize→publish cycle for a payload."""
        import time

        from src.collectors.metrics import metrics_registry
        from src.collectors.quarantine import quarantine_store

        if payload is None:
            result = self.collect_resilient()
            if result.data is None:
                return None
            payload = result.to_dict().get("data") or {}
            if hasattr(result.data, "__dataclass_fields__"):
                from dataclasses import asdict

                payload = asdict(result.data)

        t0 = time.perf_counter()
        report = self.validate(payload if isinstance(payload, dict) else {})
        validation_ms = (time.perf_counter() - t0) * 1000
        hard = [i for i in getattr(report, "issues", []) if getattr(i, "severity", "error") == "error"]
        if hard:
            quarantine_store.add(
                source=self.MODULE.lower(),
                payload=payload if isinstance(payload, dict) else {},
                codes=[i.code for i in hard],
            )
            metrics_registry.record(self.MODULE.lower(), success=False, validation_ms=validation_ms)
            return None

        t1 = time.perf_counter()
        normalized = self.normalize(payload if isinstance(payload, dict) else {})
        normalization_ms = (time.perf_counter() - t1) * 1000
        self.publish(normalized)
        metrics_registry.record(
            self.MODULE.lower(),
            success=True,
            validation_ms=validation_ms,
            normalization_ms=normalization_ms,
        )
        return normalized
