"""Report Generation & Intelligence Delivery package (Ch.10)."""

from src.reports.contracts import Audience, CanonicalReport, ReportType

__all__ = ["ReportGenerator", "CanonicalReport", "ReportType", "Audience"]


def __getattr__(name: str):
    if name == "ReportGenerator":
        from src.reports.engine import ReportGenerator

        return ReportGenerator
    raise AttributeError(name)
