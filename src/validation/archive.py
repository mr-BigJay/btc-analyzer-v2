"""Immutable prediction archive (Ch.14 §14.8). Nothing is overwritten."""

from __future__ import annotations

import json
import threading
from collections import deque
from pathlib import Path
from typing import Any

from src.config import settings
from src.validation.contracts import PredictionRecord, utc_now_iso


def archive_dir() -> Path:
    path = settings.data_dir / "validation" / "predictions"
    path.mkdir(parents=True, exist_ok=True)
    return path


class PredictionArchive:
    def __init__(self, *, memory_maxlen: int = 500) -> None:
        self._memory: deque[PredictionRecord] = deque(maxlen=memory_maxlen)
        self._lock = threading.RLock()

    def append(self, record: PredictionRecord | dict[str, Any]) -> PredictionRecord:
        if isinstance(record, dict):
            # Only known fields
            fields = {f.name for f in PredictionRecord.__dataclass_fields__.values()}  # type: ignore[attr-defined]
            record = PredictionRecord(**{k: v for k, v in record.items() if k in fields})
        with self._lock:
            self._memory.append(record)
            path = archive_dir() / f"pred_{record.timestamp.replace(':', '-')}_{record.prediction_id[:8]}.json"
            # Append-only write — never overwrite existing
            if path.exists():
                path = archive_dir() / f"pred_{record.timestamp.replace(':', '-')}_{record.prediction_id}.json"
            path.write_text(json.dumps(record.to_dict(), indent=2, default=str), encoding="utf-8")
        return record

    def list(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            mem = [r.to_dict() for r in list(self._memory)[-limit:]]
        if len(mem) >= limit:
            return mem
        files = sorted(archive_dir().glob("pred_*.json"), reverse=True)[:limit]
        disk: list[dict[str, Any]] = []
        for f in files:
            try:
                disk.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                continue
        # Prefer memory order; fill from disk
        seen = {d.get("prediction_id") for d in mem}
        for d in disk:
            if d.get("prediction_id") not in seen:
                mem.insert(0, d)
        return mem[-limit:]

    def get(self, prediction_id: str) -> dict[str, Any] | None:
        with self._lock:
            for r in self._memory:
                if r.prediction_id == prediction_id:
                    return r.to_dict()
        for f in archive_dir().glob(f"pred_*{prediction_id[:8]}*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("prediction_id") == prediction_id:
                    return data
            except Exception:  # noqa: BLE001
                continue
        return None

    def clear_memory(self) -> None:
        with self._lock:
            self._memory.clear()


prediction_archive = PredictionArchive()


def archive_from_ai_report(report: dict[str, Any], *, source: str = "continuous") -> PredictionRecord:
    """Bridge from AI Decision / scoring reports into the immutable archive."""
    scoring = report.get("scoring") if isinstance(report.get("scoring"), dict) else {}
    plan = report.get("trading_plan") if isinstance(report.get("trading_plan"), dict) else {}
    outlook = report.get("daily_outlook") if isinstance(report.get("daily_outlook"), dict) else {}
    entry = None
    zone = plan.get("entry_zone")
    if isinstance(zone, (list, tuple)) and zone:
        try:
            entry = float(zone[0])
        except (TypeError, ValueError):
            entry = None
    ts = report.get("generated_at") or outlook.get("generated_at") or utc_now_iso()
    if isinstance(outlook.get("date"), str) and not report.get("generated_at"):
        # date-only outlook → keep as timestamp prefix, still ISO-ish
        ts = f"{outlook['date']}T00:00:00.000Z"
    rec = PredictionRecord(
        timestamp=str(ts),
        symbol=str(report.get("symbol") or "BTCUSDT"),
        market_bias=str(report.get("market_bias") or scoring.get("market_bias") or "Neutral"),
        confidence=float(report.get("confidence") or scoring.get("confidence_score") or 50),
        primary_scenario=str(report.get("primary_scenario") or ""),
        risk_level=str(report.get("risk_level") or "Moderate"),
        market_regime=str(report.get("market_regime") or ""),
        probability_distribution=dict(report.get("probability_distribution") or {}),
        scenarios=list(report.get("scenarios") or []),
        layer_scores=dict(scoring.get("layer_scores") or {}),
        entry_price=entry,
        trading_plan=plan,
        engine_version=str(report.get("engine_version") or scoring.get("engine_version") or "1.0"),
        analysis_fingerprint=report.get("analysis_fingerprint"),
        feature_version=(report.get("features") or {}).get("feature_version")
        if isinstance(report.get("features"), dict)
        else None,
        source=source,
        payload={"market_bias_score": scoring.get("market_bias_score"), "publish": scoring.get("publish")},
    )
    return prediction_archive.append(rec)
