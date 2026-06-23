"""Grid-search optimizer for backtest parameters."""

from __future__ import annotations

import itertools
import logging

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.analyzer.backtest import BacktestEngine
from src.config import settings
from src.db.models import OptimizedParams

logger = logging.getLogger(__name__)

CONFIDENCE_GRID = [65, 70, 75]
BULL_SCORE_GRID = [60, 62]
BEAR_SCORE_GRID = [38, 40]


class BacktestOptimizer:
    def optimize_timeframe(self, session: Session, timeframe: str) -> OptimizedParams | None:
        best = None
        best_score = -1.0

        for conf, bull, bear in itertools.product(
            CONFIDENCE_GRID, BULL_SCORE_GRID, BEAR_SCORE_GRID
        ):
            engine = BacktestEngine(
                confidence_threshold=conf,
                min_score_bull=bull,
                max_score_bear=bear,
            )
            try:
                report = engine.run(session, timeframe, step=2)
            except ValueError:
                continue

            if report.total_signals < 10:
                continue

            score = report.profit_factor * 0.6 + report.win_rate * 0.004
            if score > best_score:
                best_score = score
                best = (conf, bull, bear, report)

        if not best:
            logger.warning("No valid optimization result for %s", timeframe)
            return None

        conf, bull, bear, report = best
        row = OptimizedParams(
            timeframe=timeframe,
            confidence_threshold=conf,
            min_score_bull=bull,
            max_score_bear=bear,
            win_rate=report.win_rate,
            profit_factor=report.profit_factor,
        )
        session.add(row)
        session.commit()
        logger.info(
            "Optimized %s: conf=%.0f bull=%.0f bear=%.0f WR=%.1f%% PF=%.2f",
            timeframe, conf, bull, bear, report.win_rate, report.profit_factor,
        )
        return row

    def optimize_all(self, session: Session) -> list[OptimizedParams]:
        results = []
        for tf in settings.timeframes:
            row = self.optimize_timeframe(session, tf)
            if row:
                results.append(row)
        return results

    def optimize_primary(self, session: Session) -> OptimizedParams | None:
        """Fast nightly optimization on daily timeframe."""
        return self.optimize_timeframe(session, "1d")

    @staticmethod
    def get_best_params(session: Session, timeframe: str) -> OptimizedParams | None:
        return session.execute(
            select(OptimizedParams)
            .where(OptimizedParams.timeframe == timeframe)
            .order_by(desc(OptimizedParams.created_at))
            .limit(1)
        ).scalar_one_or_none()

    @staticmethod
    def get_all_best(session: Session) -> dict[str, OptimizedParams]:
        out = {}
        for tf in settings.timeframes:
            p = BacktestOptimizer.get_best_params(session, tf)
            if p:
                out[tf] = p
        return out
