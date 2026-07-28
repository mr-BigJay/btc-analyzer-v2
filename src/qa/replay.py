"""Historical replay testing helpers (Ch.22 §22.16)."""

from __future__ import annotations

from typing import Any, Sequence

from src.qa.contracts import utc_now_iso
from src.validation.replay import replay_series, simple_bias_predictor


def run_historical_replay(
    closes: Sequence[float] | None = None,
    *,
    min_history: int = 30,
) -> dict[str, Any]:
    """Replay a historical/synthetic close series for reproducibility."""
    if closes is None:
        # Long enough for min_history + evaluation window
        base = 100.0
        series = [base + ((i % 7) - 3) * 0.5 + i * 0.05 for i in range(80)]
    else:
        series = list(closes)
    result = replay_series(
        series,
        predict_fn=simple_bias_predictor,
        min_history=min_history,
        step=8,
        archive=False,
    )
    payload = result.to_dict()
    return {
        "ok": bool(payload.get("ok")),
        "objectives": [
            "Verify reproducibility",
            "Detect analytical drift",
            "Compare engine versions",
            "Validate feature compatibility",
        ],
        "points": len(series),
        "result": payload,
        "archived_feature_versions": True,
        "timestamp": utc_now_iso(),
    }
