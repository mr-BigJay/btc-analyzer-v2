"""Admin service facade."""

from __future__ import annotations

from typing import Any

from src.admin import engine


class AdminService:
    def status(self) -> dict[str, Any]:
        return engine.admin_status()

    def config(self) -> dict[str, Any]:
        return engine.config_view()

    def update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        return engine.update_config(payload)

    def progress(self) -> dict[str, Any]:
        return engine.setup_progress()

    def bootstrap(self, password: str, initial_config: dict[str, Any] | None = None) -> dict[str, Any]:
        return engine.bootstrap(password, initial_config=initial_config)

    def login(self, password: str) -> dict[str, Any]:
        return engine.login(password)

    def skip(self, step_id: str) -> dict[str, Any]:
        return engine.skip_step(step_id)

    def run_op(self, op: str) -> dict[str, Any]:
        return engine.run_op(op)
