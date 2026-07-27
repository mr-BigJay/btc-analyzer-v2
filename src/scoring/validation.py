"""Scoring validation / backtesting records (Ch.9 §9.17)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import settings
from src.core.contracts import utc_now_iso
from src.logging_setup import get_logger

log = get_logger("scoring.validation")


def records_dir() -> Path:
    path = settings.data_dir / "scoring"
    path.mkdir(parents=True, exist_ok=True)
    return path


def record_decision(
    decision: dict[str, Any],
    *,
    analysis_input: dict[str, Any] | None = None,
) -> Path:
    stamp = utc_now_iso().replace(":", "-")
    payload = {
        "recorded_at": utc_now_iso(),
        "layer_scores": decision.get("layer_scores"),
        "composite_scores": {
            "market_bias_score": decision.get("market_bias_score"),
            "confidence_score": decision.get("confidence_score"),
            "risk_score": decision.get("risk_score"),
            "market_health_index": decision.get("market_health_index"),
            "market_stress_index": decision.get("market_stress_index"),
            "data_quality_score": decision.get("data_quality_score"),
        },
        "published_decision": decision.get("decision"),
        "publish": decision.get("publish"),
        "market_outcome": {"1h": None, "4h": None, "24h": None},
        "forecast_accuracy": None,
        "confidence_calibration_accuracy": None,
        "analysis_input_fingerprint": (analysis_input or {}).get("analyzed_at"),
        "decision_object": decision,
    }
    path = records_dir() / f"score_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    log.info("scoring decision recorded path={}", path)
    return path
