"""Dashboard service facade (Ch.17)."""

from __future__ import annotations

from typing import Any

from src.dashboard.engine import DashboardEngine


class DashboardService:
    def __init__(self) -> None:
        self.engine = DashboardEngine()

    def view(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.build_view(**kwargs)

    def preferences(self) -> dict[str, Any]:
        return self.engine.get_preferences().to_dict()

    def update_preferences(self, data: dict[str, Any]) -> dict[str, Any]:
        return self.engine.set_preferences(data).to_dict()

    def status(self) -> dict[str, Any]:
        return self.engine.status()
