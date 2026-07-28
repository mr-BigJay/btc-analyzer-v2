"""Observability service facade (Ch.21)."""

from __future__ import annotations

from typing import Any

from src.observability.engine import ObservabilityEngine


class ObservabilityService:
    def __init__(self) -> None:
        self.engine = ObservabilityEngine()

    def status(self) -> dict[str, Any]:
        return self.engine.status()

    def observability_object(self, service: str = "api") -> dict[str, Any]:
        return self.engine.observability_object(service)

    def metrics(self) -> dict[str, Any]:
        return self.engine.metrics()

    def slos(self) -> dict[str, Any]:
        return self.engine.slos()

    def alerts(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.alerts(**kwargs)

    def traces(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.traces(**kwargs)

    def dashboard(self) -> dict[str, Any]:
        return self.engine.dashboard()

    def anomalies(self) -> dict[str, Any]:
        return self.engine.anomalies()

    def capacity(self) -> dict[str, Any]:
        return self.engine.capacity()
