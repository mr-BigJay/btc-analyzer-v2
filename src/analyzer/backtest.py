"""Walk-forward backtest for technical signals."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass

import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.analyzer.models import Trend
from src.analyzer.service import TechnicalAnalyzer
from src.config import settings
from src.db.models import BacktestResult, OHLCVCandle

logger = logging.getLogger(__name__)

FORWARD_BARS = {"4h": 6, "1d": 5, "1w": 4}
MIN_HISTORY = 120


@dataclass
class TradeSignal:
    index: int
    time: str
    trend: str
    score: float
    confidence: float
    entry_price: float
    exit_price: float
    return_pct: float
    win: bool


@dataclass
class BacktestReport:
    timeframe: str
    total_signals: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    avg_return_pct: float
    max_drawdown_pct: float
    trades: list[TradeSignal]


class BacktestEngine:
    def __init__(
        self,
        confidence_threshold: float | None = None,
        min_score_bull: float = 60.0,
        max_score_bear: float = 40.0,
    ) -> None:
        self.analyzer = TechnicalAnalyzer()
        self.confidence_threshold = confidence_threshold or settings.alert_threshold
        self.min_score_bull = min_score_bull
        self.max_score_bear = max_score_bear

    def _load_candles(self, session: Session, timeframe: str) -> pd.DataFrame:
        rows = session.execute(
            select(OHLCVCandle)
            .where(OHLCVCandle.symbol == settings.symbol, OHLCVCandle.timeframe == timeframe)
            .order_by(OHLCVCandle.open_time)
        ).scalars().all()
        return pd.DataFrame(
            [
                {
                    "open_time": r.open_time,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                }
                for r in rows
            ]
        )

    def run(
        self,
        session: Session,
        timeframe: str,
        step: int = 1,
    ) -> BacktestReport:
        df = self._load_candles(session, timeframe)
        if len(df) < MIN_HISTORY + FORWARD_BARS.get(timeframe, 5):
            raise ValueError(f"Not enough data for backtest on {timeframe}")

        forward = FORWARD_BARS.get(timeframe, 5)
        trades: list[TradeSignal] = []

        for i in range(MIN_HISTORY, len(df) - forward, step):
            window = df.iloc[: i + 1].copy()
            try:
                result = self.analyzer.analyze_dataframe(window, timeframe)
            except Exception:
                continue

            if result.confidence < self.confidence_threshold:
                continue
            if result.trend == Trend.BULLISH and result.score < self.min_score_bull:
                continue
            if result.trend == Trend.BEARISH and result.score > self.max_score_bear:
                continue
            if result.trend == Trend.NEUTRAL:
                continue

            entry = float(window["close"].iloc[-1])
            exit_price = float(df["close"].iloc[i + forward])

            if result.trend == Trend.BULLISH:
                ret = (exit_price - entry) / entry * 100
            else:
                ret = (entry - exit_price) / entry * 100

            trades.append(
                TradeSignal(
                    index=i,
                    time=str(window["open_time"].iloc[-1]),
                    trend=result.trend.value,
                    score=result.score,
                    confidence=result.confidence,
                    entry_price=round(entry, 2),
                    exit_price=round(exit_price, 2),
                    return_pct=round(ret, 2),
                    win=ret > 0,
                )
            )

        return self._build_report(timeframe, trades)

    def _build_report(self, timeframe: str, trades: list[TradeSignal]) -> BacktestReport:
        if not trades:
            return BacktestReport(
                timeframe=timeframe,
                total_signals=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                profit_factor=0.0,
                avg_return_pct=0.0,
                max_drawdown_pct=0.0,
                trades=[],
            )

        wins = [t for t in trades if t.win]
        losses = [t for t in trades if not t.win]
        gross_profit = sum(t.return_pct for t in wins)
        gross_loss = abs(sum(t.return_pct for t in losses))
        pf = gross_profit / gross_loss if gross_loss else float("inf")

        equity = 100.0
        peak = 100.0
        max_dd = 0.0
        for t in trades:
            equity *= 1 + t.return_pct / 100
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)

        return BacktestReport(
            timeframe=timeframe,
            total_signals=len(trades),
            wins=len(wins),
            losses=len(losses),
            win_rate=round(len(wins) / len(trades) * 100, 1),
            profit_factor=round(pf, 2) if pf != float("inf") else 999.0,
            avg_return_pct=round(sum(t.return_pct for t in trades) / len(trades), 2),
            max_drawdown_pct=round(max_dd, 2),
            trades=trades,
        )

    def save_report(self, session: Session, report: BacktestReport) -> None:
        payload = json.dumps(
            {
                "summary": asdict(report),
                "trades": [asdict(t) for t in report.trades[-50:]],
            },
            ensure_ascii=False,
        )
        row = BacktestResult(
            timeframe=report.timeframe,
            total_signals=report.total_signals,
            win_rate=report.win_rate,
            profit_factor=report.profit_factor,
            avg_return_pct=report.avg_return_pct,
            max_drawdown_pct=report.max_drawdown_pct,
            payload=payload,
        )
        session.add(row)
        session.commit()

    def run_all_timeframes(self, session: Session, save: bool = True) -> list[BacktestReport]:
        reports = []
        for tf in settings.timeframes:
            try:
                report = self.run(session, tf)
                reports.append(report)
                if save:
                    self.save_report(session, report)
                logger.info(
                    "Backtest %s: signals=%d win_rate=%.1f%% pf=%.2f",
                    tf,
                    report.total_signals,
                    report.win_rate,
                    report.profit_factor,
                )
            except Exception:
                logger.exception("Backtest failed for %s", tf)
        return reports
