"""Paper trading simulation — no real orders (Ch.14 §14.7)."""

from __future__ import annotations

import json
import threading
from collections import deque
from pathlib import Path
from typing import Any, Sequence

from src.config import settings
from src.validation.contracts import PaperTrade, PredictionRecord, utc_now_iso


def paper_dir() -> Path:
    path = settings.data_dir / "validation" / "paper_trades"
    path.mkdir(parents=True, exist_ok=True)
    return path


class PaperTradingLedger:
    def __init__(self, *, maxlen: int = 500) -> None:
        self._trades: deque[PaperTrade] = deque(maxlen=maxlen)
        self._lock = threading.RLock()

    def open_from_prediction(self, pred: PredictionRecord | dict[str, Any]) -> PaperTrade | None:
        p = pred if isinstance(pred, PredictionRecord) else PredictionRecord(**{
            k: v for k, v in pred.items() if k in PredictionRecord.__dataclass_fields__
        })
        plan = p.trading_plan or {}
        direction = str(plan.get("preferred_direction") or "no_trade")
        if direction == "no_trade" or p.entry_price is None:
            return None
        zone = plan.get("entry_zone") or []
        targets = []
        for t in plan.get("target_levels") or plan.get("targets") or []:
            try:
                targets.append(float(t))
            except (TypeError, ValueError):
                pass
        stop = plan.get("stop_loss_zone") or plan.get("stop_loss")
        try:
            stop_f = float(stop) if stop is not None else None
        except (TypeError, ValueError):
            stop_f = None
        trade = PaperTrade(
            prediction_id=p.prediction_id,
            entry_timestamp=p.timestamp,
            entry_price=float(zone[0]) if isinstance(zone, (list, tuple)) and zone else p.entry_price,
            stop_loss=stop_f,
            targets=targets,
            direction=direction,
        )
        with self._lock:
            self._trades.append(trade)
            path = paper_dir() / f"paper_{trade.trade_id}.json"
            path.write_text(json.dumps(trade.to_dict(), indent=2, default=str), encoding="utf-8")
        return trade

    def simulate_exit(
        self,
        trade: PaperTrade,
        *,
        highs: Sequence[float],
        lows: Sequence[float],
        closes: Sequence[float],
        start_idx: int,
        max_bars: int = 24,
    ) -> PaperTrade:
        if trade.entry_price is None or start_idx < 0:
            return trade
        entry = trade.entry_price
        direction = trade.direction.lower()
        long = "long" in direction or "bull" in direction
        mfe = 0.0
        mae = 0.0
        exit_price = None
        exit_reason = "time_exit"
        exit_i = min(len(closes) - 1, start_idx + max_bars)
        for i in range(start_idx + 1, min(len(closes), start_idx + max_bars + 1)):
            h = float(highs[i]) if i < len(highs) else float(closes[i])
            low = float(lows[i]) if i < len(lows) else float(closes[i])
            if long:
                mfe = max(mfe, (h - entry) / entry)
                mae = max(mae, (entry - low) / entry)
                if trade.stop_loss is not None and low <= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = "stop_loss"
                    exit_i = i
                    break
                for t in trade.targets:
                    if h >= t:
                        exit_price = t
                        exit_reason = "target"
                        exit_i = i
                        break
                if exit_price is not None:
                    break
            else:
                mfe = max(mfe, (entry - low) / entry)
                mae = max(mae, (h - entry) / entry)
                if trade.stop_loss is not None and h >= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = "stop_loss"
                    exit_i = i
                    break
                for t in trade.targets:
                    if low <= t:
                        exit_price = t
                        exit_reason = "target"
                        exit_i = i
                        break
                if exit_price is not None:
                    break
        if exit_price is None:
            exit_price = float(closes[exit_i])
        pnl = (exit_price - entry) / entry if long else (entry - exit_price) / entry
        trade.exit_timestamp = utc_now_iso()
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason
        trade.mfe = round(mfe, 6)
        trade.mae = round(mae, 6)
        trade.pnl_pct = round(pnl, 6)
        with self._lock:
            path = paper_dir() / f"paper_{trade.trade_id}.json"
            path.write_text(json.dumps(trade.to_dict(), indent=2, default=str), encoding="utf-8")
        return trade

    def list(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return [t.to_dict() for t in list(self._trades)[-limit:]]


paper_ledger = PaperTradingLedger()
