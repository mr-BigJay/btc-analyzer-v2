"""Historical replay engine — no future information (Ch.14 §14.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from src.validation.archive import prediction_archive
from src.validation.contracts import PredictionRecord, utc_now_iso
from src.validation.outcomes import evaluate_prediction


@dataclass
class ReplayPoint:
    index: int
    timestamp: str | None
    closes_available: int
    prediction_id: str | None = None
    outcomes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReplayResult:
    ok: bool
    points: list[ReplayPoint] = field(default_factory=list)
    outcomes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    engine_version: str = "1.0"
    feature_version: str | None = None
    completed_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "points": [
                {
                    "index": p.index,
                    "timestamp": p.timestamp,
                    "closes_available": p.closes_available,
                    "prediction_id": p.prediction_id,
                    "outcomes": p.outcomes,
                }
                for p in self.points
            ],
            "outcomes": self.outcomes,
            "warnings": self.warnings,
            "engine_version": self.engine_version,
            "feature_version": self.feature_version,
            "completed_at": self.completed_at,
        }


def replay_series(
    closes: Sequence[float],
    *,
    predict_fn: Callable[[Sequence[float], int], dict[str, Any]],
    step: int = 12,
    min_history: int = 30,
    bars_per_hour: float = 1.0,
    timestamps: Sequence[str] | None = None,
    highs: Sequence[float] | None = None,
    lows: Sequence[float] | None = None,
    engine_version: str = "1.0",
    feature_version: str | None = None,
    archive: bool = True,
) -> ReplayResult:
    """
    At each index i, only closes[: i+1] are visible to predict_fn.
    Outcomes use future bars strictly after i (evaluation only).
    """
    warnings: list[str] = []
    if len(closes) < min_history + 24:
        warnings.append("series too short for robust replay")
    points: list[ReplayPoint] = []
    all_outcomes: list[dict[str, Any]] = []

    i = min_history - 1
    while i < len(closes) - 2:
        visible = closes[: i + 1]
        try:
            pred_dict = predict_fn(visible, i)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"predict failed at {i}: {exc}")
            i += step
            continue

        pred_dict = dict(pred_dict)
        pred_dict.setdefault("entry_price", float(closes[i]))
        pred_dict.setdefault("engine_version", engine_version)
        pred_dict.setdefault("feature_version", feature_version)
        pred_dict.setdefault("source", "backtest")
        pred_dict.setdefault("timestamp", timestamps[i] if timestamps and i < len(timestamps) else utc_now_iso())

        fields = {f.name for f in PredictionRecord.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        rec = PredictionRecord(**{k: v for k, v in pred_dict.items() if k in fields})
        if archive:
            rec = prediction_archive.append(rec)

        outcomes = evaluate_prediction(rec, closes=closes, entry_idx=i, bars_per_hour=bars_per_hour)
        out_dicts = []
        for o in outcomes:
            d = o.to_dict()
            d["market_bias"] = rec.market_bias
            d["predicted_bias"] = rec.market_bias
            d["confidence"] = rec.confidence
            d["market_regime"] = rec.market_regime
            d["layer_scores"] = rec.layer_scores
            d["primary_scenario"] = rec.primary_scenario
            out_dicts.append(d)
        all_outcomes.extend(out_dicts)
        points.append(
            ReplayPoint(
                index=i,
                timestamp=rec.timestamp,
                closes_available=len(visible),
                prediction_id=rec.prediction_id,
                outcomes=out_dicts,
            )
        )
        i += step

    return ReplayResult(
        ok=bool(points),
        points=points,
        outcomes=all_outcomes,
        warnings=warnings,
        engine_version=engine_version,
        feature_version=feature_version,
    )


def simple_bias_predictor(closes: Sequence[float], idx: int) -> dict[str, Any]:
    """Deterministic baseline predictor for tests / smoke backtests (no AI)."""
    window = list(closes[max(0, idx - 20) : idx + 1])
    if len(window) < 2:
        return {"market_bias": "Neutral", "confidence": 50.0, "primary_scenario": "Sideways Consolidation"}
    ret = (window[-1] - window[0]) / window[0]
    if ret > 0.01:
        bias, scenario, conf = "Bullish", "Bullish Continuation", min(90.0, 55 + ret(ret) * 500)
    elif ret < -0.01:
        bias, scenario, conf = "Bearish", "Bearish Reversal", min(90.0, 55 + abs(ret) * 500)
    else:
        bias, scenario, conf = "Neutral", "Sideways Consolidation", 55.0
    return {
        "market_bias": bias,
        "confidence": round(conf, 1),
        "primary_scenario": scenario,
        "risk_level": "Moderate",
        "market_regime": "Trend" if abs(ret) > 0.02 else "Range",
        "probability_distribution": {"trend_continuation": conf, "consolidation": 100 - conf},
        "layer_scores": {"Technical": 40 if ret > 0 else (-40 if ret < 0 else 0), "Spot": 20 if ret > 0 else -20},
    }
