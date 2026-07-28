"""Operator validation dashboard snapshot (Ch.14 §14.18)."""

from __future__ import annotations

from typing import Any

from src.validation.archive import prediction_archive
from src.validation.contracts import utc_now_iso
from src.validation.paper import paper_ledger


def build_dashboard(
    *,
    metrics: dict[str, Any] | None = None,
    calibration: dict[str, Any] | None = None,
    regime_results: dict[str, Any] | None = None,
    layer_contribution: dict[str, Any] | None = None,
    drift: dict[str, Any] | None = None,
    failures: list[dict[str, Any]] | None = None,
    data_quality_trend: list[float] | None = None,
) -> dict[str, Any]:
    preds = prediction_archive.list(limit=20)
    papers = paper_ledger.list(limit=20)
    return {
        "generated_at": utc_now_iso(),
        "audience": "operators",
        "current_accuracy": (metrics or {}).get("accuracy"),
        "confidence_calibration": (calibration or {}).get("label"),
        "calibration_bins": (calibration or {}).get("bins"),
        "market_regime_performance": regime_results or {},
        "layer_contribution": layer_contribution or {},
        "prediction_history": preds,
        "recent_failures": failures or [],
        "data_quality_trend": data_quality_trend or [],
        "model_drift_status": (drift or {}).get("status", "none"),
        "drift": drift or {},
        "metrics": metrics or {},
        "paper_trades": papers,
    }
