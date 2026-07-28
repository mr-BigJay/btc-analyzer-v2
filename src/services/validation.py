"""Validation service facade (Ch.14)."""

from __future__ import annotations

from typing import Any, Sequence

from src.validation.archive import prediction_archive
from src.validation.engine import ValidationEngine
from src.validation.paper import paper_ledger


class ValidationService:
    def __init__(self) -> None:
        self.engine = ValidationEngine()

    def backtest(self, closes: Sequence[float], **kwargs: Any) -> dict[str, Any]:
        return self.engine.backtest(closes, **kwargs)

    def walk_forward(self, closes: Sequence[float], **kwargs: Any) -> dict[str, Any]:
        return self.engine.walk_forward(closes, **kwargs)

    def evaluate(self, outcomes: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        return self.engine.evaluate_outcomes(outcomes, **kwargs)

    def continuous(self, report: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self.engine.continuous_from_report(report, **kwargs)

    def approve(self, validation_object: dict[str, Any], *, approver: str, notes: str = "") -> dict[str, Any]:
        return self.engine.approve(validation_object, approver=approver, notes=notes)

    def compare(self, production: list[dict[str, Any]], candidate: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        return self.engine.version_compare(production, candidate, **kwargs)

    def dashboard(self) -> dict[str, Any]:
        return self.engine.dashboard()

    def predictions(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return prediction_archive.list(limit=limit)

    def paper_trades(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return paper_ledger.list(limit=limit)

    def status(self) -> dict[str, Any]:
        return {
            "predictions_cached": len(prediction_archive.list(limit=500)),
            "paper_trades_cached": len(paper_ledger.list(limit=500)),
            "horizons": ["1h", "4h", "24h", "7d"],
            "methods": [
                "historical_backtest",
                "walk_forward",
                "paper_trading",
                "shadow_mode",
                "continuous_validation",
            ],
        }
