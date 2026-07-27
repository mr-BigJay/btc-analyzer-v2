"""Forecast learning / evaluation records (Ch.7 §7.17).

Stores published outlooks for later accuracy review without altering
the deterministic analysis pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import settings
from src.core.contracts import utc_now_iso
from src.logging_setup import get_logger

log = get_logger("ai.learning")


def forecast_dir() -> Path:
    path = settings.data_dir / "forecasts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def record_forecast(
    report: dict[str, Any],
    *,
    analysis_input: dict[str, Any] | None = None,
) -> Path:
    """Persist original inputs, scenarios, probabilities, and confidence."""
    date = (report.get("daily_outlook") or {}).get("date") or utc_now_iso()[:10]
    stamp = utc_now_iso().replace(":", "-")
    payload = {
        "recorded_at": utc_now_iso(),
        "date": date,
        "symbol": report.get("symbol"),
        "market_bias": report.get("market_bias"),
        "confidence": report.get("confidence"),
        "primary_narrative": report.get("primary_narrative"),
        "primary_scenario": report.get("primary_scenario"),
        "scenarios": report.get("scenarios"),
        "probability_distribution": report.get("probability_distribution"),
        "risk_level": report.get("risk_level"),
        "analysis_fingerprint": report.get("analysis_fingerprint"),
        "analysis_input": analysis_input,
        "final_market_outcome": None,  # filled by later evaluation job
        "forecast_accuracy_metrics": None,
    }
    path = forecast_dir() / f"forecast_{date}_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    log.info("forecast recorded path={}", path)
    return path


def list_forecasts(*, limit: int = 20) -> list[dict[str, Any]]:
    files = sorted(forecast_dir().glob("forecast_*.json"), reverse=True)[:limit]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            log.warning("skip corrupt forecast {}: {}", f, exc)
    return out
