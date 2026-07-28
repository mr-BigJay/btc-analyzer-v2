"""Outcome evaluation vs market prices (Ch.14 §14.9)."""

from __future__ import annotations

from typing import Any, Sequence

from src.validation.contracts import HORIZON_HOURS, HORIZONS, OutcomeRecord, PredictionRecord, utc_now_iso


def classify_direction(return_pct: float | None, *, threshold: float = 0.001) -> str:
    if return_pct is None:
        return "Neutral"
    if return_pct > threshold:
        return "Bullish"
    if return_pct < -threshold:
        return "Bearish"
    return "Neutral"


def bias_matches(predicted: str, actual: str) -> bool:
    p = predicted.lower()
    a = actual.lower()
    if "neutral" in p or "range" in p or "uncertain" in p:
        return a == "neutral"
    if "bull" in p:
        return a == "bullish"
    if "bear" in p:
        return a == "bearish"
    return False


def scenario_occurred(primary: str, actual_direction: str, return_pct: float | None) -> bool | None:
    if not primary:
        return None
    name = primary.lower()
    if "continuation" in name or "bullish" in name:
        return actual_direction == "bullish"
    if "reversal" in name or "bearish" in name:
        return actual_direction == "bearish"
    if "sideways" in name or "consolidat" in name or "range" in name:
        return actual_direction == "neutral" or (return_pct is not None and abs(return_pct) < 0.01)
    return None


def risk_materialized(risk_level: str, return_pct: float | None, mae: float | None = None) -> bool | None:
    if return_pct is None and mae is None:
        return None
    move = abs(mae if mae is not None else return_pct or 0.0)
    level = risk_level.lower()
    if level in {"extreme", "high"}:
        return move >= 0.02
    if level in {"elevated", "moderate"}:
        return move >= 0.01
    return move >= 0.005


def price_after_bars(closes: Sequence[float], entry_idx: int, bars: int) -> float | None:
    target = entry_idx + bars
    if entry_idx < 0 or target >= len(closes):
        return None
    return float(closes[target])


def evaluate_prediction(
    prediction: PredictionRecord | dict[str, Any],
    *,
    closes: Sequence[float],
    entry_idx: int,
    bars_per_hour: float = 1.0,
    horizons: tuple[str, ...] = HORIZONS,
) -> list[OutcomeRecord]:
    """Evaluate a prediction against a close series with no lookahead beyond horizon."""
    pred = prediction if isinstance(prediction, PredictionRecord) else PredictionRecord(**{
        k: v for k, v in prediction.items() if k in PredictionRecord.__dataclass_fields__
    })
    entry_price = pred.entry_price
    if entry_price is None and 0 <= entry_idx < len(closes):
        entry_price = float(closes[entry_idx])
    outcomes: list[OutcomeRecord] = []
    for horizon in horizons:
        hours = HORIZON_HOURS.get(horizon, 1)
        bars = max(1, int(round(hours * bars_per_hour)))
        exit_price = price_after_bars(closes, entry_idx, bars)
        ret = None
        if entry_price and exit_price is not None and entry_price != 0:
            ret = (exit_price - entry_price) / entry_price
        actual = classify_direction(ret)
        outcomes.append(
            OutcomeRecord(
                prediction_id=pred.prediction_id,
                horizon=horizon,
                evaluated_at=utc_now_iso(),
                entry_price=entry_price,
                exit_price=exit_price,
                return_pct=None if ret is None else round(ret, 8),
                direction_actual=actual,
                direction_correct=bias_matches(pred.market_bias, actual) if ret is not None else None,
                bias_correct=bias_matches(pred.market_bias, actual) if ret is not None else None,
                scenario_occurred=scenario_occurred(pred.primary_scenario, actual, ret),
                risk_materialized=risk_materialized(pred.risk_level, ret),
            )
        )
    return outcomes
