"""Quantitative performance metrics (Ch.14 §14.10–§14.11)."""

from __future__ import annotations

import math
from typing import Any, Sequence


def _safe_div(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return a / b


def confusion_from_directions(
    predicted: Sequence[str],
    actual: Sequence[str],
    *,
    positive: str = "Bullish",
) -> dict[str, int]:
    tp = fp = tn = fn = 0
    for p, a in zip(predicted, actual):
        p_pos = positive.lower() in p.lower()
        a_pos = positive.lower() in a.lower()
        if p_pos and a_pos:
            tp += 1
        elif p_pos and not a_pos:
            fp += 1
        elif (not p_pos) and (not a_pos):
            tn += 1
        else:
            fn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def classification_scores(cm: dict[str, int]) -> dict[str, float]:
    tp, fp, tn, fn = cm["tp"], cm["fp"], cm["tn"], cm["fn"]
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total * 100 if total else 0.0
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    prec = (precision or 0.0) * 100
    rec = (recall or 0.0) * 100
    f1 = 0.0
    if prec + rec > 0:
        f1 = 2 * prec * rec / (prec + rec)
    return {
        "accuracy": round(accuracy, 2),
        "precision": round(prec, 2),
        "recall": round(rec, 2),
        "f1_score": round(f1, 2),
        "sample_size": total,
    }


def directional_accuracy(correct_flags: Sequence[bool | None]) -> float:
    valid = [c for c in correct_flags if c is not None]
    if not valid:
        return 0.0
    return round(100.0 * sum(1 for c in valid if c) / len(valid), 2)


def trading_metrics(returns: Sequence[float]) -> dict[str, float | None]:
    """Analytical quality companion metrics from paper/backtest returns (not live PnL)."""
    if not returns:
        return {
            "win_rate": None,
            "profit_factor": None,
            "expectancy": None,
            "max_drawdown": None,
            "sharpe_ratio": None,
            "sortino_ratio": None,
        }
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    win_rate = 100.0 * len(wins) / len(returns)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = _safe_div(gross_profit, gross_loss) if gross_loss else (None if not wins else float("inf"))
    expectancy = sum(returns) / len(returns)

    # Drawdown on equity curve
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in returns:
        equity += r
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

    mean = expectancy
    var = sum((r - mean) ** 2 for r in returns) / max(1, len(returns) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    sharpe = (mean / std) if std > 0 else None
    downside = [r for r in returns if r < 0]
    if downside:
        dvar = sum(r ** 2 for r in downside) / len(downside)
        dstd = math.sqrt(dvar)
        sortino = (mean / dstd) if dstd > 0 else None
    else:
        sortino = None

    return {
        "win_rate": round(win_rate, 2),
        "profit_factor": None if profit_factor is None or profit_factor == float("inf") else round(profit_factor, 4),
        "expectancy": round(expectancy, 6),
        "max_drawdown": round(max_dd, 6),
        "sharpe_ratio": None if sharpe is None else round(sharpe, 4),
        "sortino_ratio": None if sortino is None else round(sortino, 4),
    }


def aggregate_outcome_metrics(outcomes: Sequence[dict[str, Any]], *, horizon: str | None = None) -> dict[str, Any]:
    rows = [o for o in outcomes if horizon is None or o.get("horizon") == horizon]
    correct = [o.get("direction_correct") for o in rows]
    bias = [o.get("bias_correct") for o in rows]
    scenarios = [o.get("scenario_occurred") for o in rows if o.get("scenario_occurred") is not None]
    returns = [float(o["return_pct"]) for o in rows if o.get("return_pct") is not None]

    # Build predicted/actual from nested prediction fields if present
    predicted = [str(o.get("predicted_bias") or o.get("market_bias") or "") for o in rows]
    actual = [str(o.get("direction_actual") or "Neutral") for o in rows]
    cm = confusion_from_directions(predicted, actual) if predicted and any(predicted) else {
        "tp": sum(1 for c in correct if c),
        "fp": sum(1 for c in correct if c is False),
        "tn": 0,
        "fn": 0,
    }
    scores = classification_scores(cm)
    scores["directional_accuracy"] = directional_accuracy(correct)
    scores["bias_accuracy"] = directional_accuracy(bias)
    if scenarios:
        scores["scenario_accuracy"] = round(100.0 * sum(1 for s in scenarios if s) / len(scenarios), 2)
    else:
        scores["scenario_accuracy"] = None
    scores.update(trading_metrics(returns))
    scores["horizon"] = horizon
    return scores
