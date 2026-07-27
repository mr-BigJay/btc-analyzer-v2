"""Report service facade (Ch.10)."""

from __future__ import annotations

from typing import Any

from src.reports.contracts import Audience, ReportType
from src.reports.engine import ReportGenerator
from src.storage.repository import CentralRepository


class ReportService:
    """Formats validated intelligence for delivery channels — no analysis."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.generator = ReportGenerator(self.repository)

    def daily_outlook(
        self,
        *,
        audience: str = Audience.PROFESSIONAL.value,
        language: str = "en",
        persist: bool = True,
        export: bool = False,
    ) -> dict[str, Any]:
        return self.generator.generate(
            report_type=ReportType.DAILY_OUTLOOK.value,
            audience=audience,
            language=language,
            persist=persist,
            export_formats=["json", "markdown"] if export else None,
        )

    def trading_plan(self, **kwargs: Any) -> dict[str, Any]:
        return self.generator.trading_plan_report(**kwargs)

    def snapshot(self, **kwargs: Any) -> dict[str, Any]:
        return self.generator.snapshot_report(**kwargs)

    def generate(self, report_type: str, **kwargs: Any) -> dict[str, Any]:
        return self.generator.generate(report_type=report_type, **kwargs)
