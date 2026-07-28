"""Walk-forward validation splits (Ch.14 §14.6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class WalkForwardFold:
    train_start: int
    train_end: int
    valid_start: int
    valid_end: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "train_start": self.train_start,
            "train_end": self.train_end,
            "valid_start": self.valid_start,
            "valid_end": self.valid_end,
            "train_size": self.train_end - self.train_start,
            "valid_size": self.valid_end - self.valid_start,
        }


def walk_forward_folds(
    n: int,
    *,
    train_size: int,
    valid_size: int,
    step: int | None = None,
) -> list[WalkForwardFold]:
    """Sequential expanding/sliding folds without shuffling (no leakage)."""
    if n <= 0 or train_size <= 0 or valid_size <= 0:
        return []
    step = step or valid_size
    folds: list[WalkForwardFold] = []
    start = 0
    while True:
        train_start = start
        train_end = train_start + train_size
        valid_start = train_end
        valid_end = valid_start + valid_size
        if valid_end > n:
            break
        folds.append(WalkForwardFold(train_start, train_end, valid_start, valid_end))
        start += step
    return folds


def summarize_fold_metrics(fold_metrics: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not fold_metrics:
        return {"folds": 0, "mean_accuracy": None}
    accs = [float(m.get("accuracy") or 0) for m in fold_metrics]
    return {
        "folds": len(fold_metrics),
        "mean_accuracy": round(sum(accs) / len(accs), 2),
        "min_accuracy": round(min(accs), 2),
        "max_accuracy": round(max(accs), 2),
        "fold_metrics": list(fold_metrics),
    }
