import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.analyzer.backtest import BacktestEngine
from src.analyzer.optimize import BacktestOptimizer
from src.analyzer.serialize import analysis_to_json
from src.analyzer.service import AnalysisService
from src.collector.orchestrator import CollectionOrchestrator
from src.advisor.service import AdvisorService
from src.config import settings
from src.db.models import AnalysisSnapshot, get_session, init_db
from src.notifier.formatters import overview_message, signal_alert

logger = logging.getLogger(__name__)


class AppScheduler:
    def __init__(self, telegram_service=None) -> None:
        self.collector = CollectionOrchestrator()
        self.analysis = AnalysisService()
        self.advisor = AdvisorService()
        self.telegram = telegram_service
        self._last_trends: dict[str, str] = {}
        self.scheduler = BlockingScheduler(timezone="UTC")

    def collect_and_analyze(self) -> None:
        logger.info("Running scheduled collection...")
        self.collector.run_all()
        self._run_analysis(save=True, notify=bool(self.telegram))

    def run_backtest_optimize(self) -> None:
        logger.info("Running backtest parameter optimization...")
        session = get_session()
        try:
            optimizer = BacktestOptimizer()
            row = optimizer.optimize_primary(session)
            results = [row] if row else []
            for r in results:
                logger.info(
                    "Best params %s: conf=%.0f WR=%.1f%% PF=%.2f",
                    r.timeframe, r.confidence_threshold, r.win_rate, r.profit_factor,
                )
            engine = BacktestEngine()
            engine.run_all_timeframes(session, save=True)
        except Exception:
            logger.exception("Backtest optimization failed")
        finally:
            session.close()

    def _get_alert_threshold(self, session) -> float:
        from src.analyzer.optimize import BacktestOptimizer

        params = BacktestOptimizer.get_best_params(session, "1d")
        if params:
            return params.confidence_threshold
        return float(settings.alert_threshold)

    def _run_analysis(self, save: bool = True, notify: bool = False) -> None:
        session = get_session()
        try:
            analysis = self.analysis.analyze(session)
            if save:
                snapshot = AnalysisSnapshot(
                    payload=analysis_to_json(analysis),
                    overall_score=analysis.overall_score,
                    overall_confidence=analysis.overall_confidence,
                    summary=analysis.summary,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(snapshot)
                session.commit()

            if notify and self.telegram:
                self._check_alerts(analysis, session)

            if settings.advisor_enabled:
                try:
                    self.advisor.generate(session, force=True)
                    logger.info("Advisor insight generated")
                except Exception:
                    logger.exception("Advisor generation failed")
        except Exception:
            logger.exception("Analysis failed")
        finally:
            session.close()

    def _check_alerts(self, analysis, session) -> None:
        import asyncio

        if not self.telegram:
            return

        async def _send():
            threshold = self._get_alert_threshold(session)
            for tf in settings.timeframes:
                t = analysis.timeframes[tf]
                trend = t.trend.value if hasattr(t.trend, "value") else t.trend
                prev = self._last_trends.get(tf)

                if (
                    t.confidence >= threshold
                    and trend in ("bullish", "bearish")
                    and prev != trend
                ):
                    await self.telegram.send_message(signal_alert(analysis, tf))

                self._last_trends[tf] = trend

        try:
            asyncio.run(_send())
        except Exception:
            logger.exception("Failed to send alert")

    def daily_report(self) -> None:
        import asyncio

        if not self.telegram:
            return
        try:
            asyncio.run(self.telegram.send_overview())
        except Exception:
            logger.exception("Failed to send daily report")

    def setup_jobs(self) -> None:
        self.scheduler.add_job(
            self.collect_and_analyze,
            IntervalTrigger(minutes=settings.collection_interval_minutes),
            id="collect_analyze",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.daily_report,
            CronTrigger(hour=settings.daily_report_hour, minute=0),
            id="daily_report",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.run_backtest_optimize,
            CronTrigger(hour=settings.backtest_optimize_hour, minute=0),
            id="backtest_optimize",
            replace_existing=True,
        )

    def start(self) -> None:
        init_db()
        self.setup_jobs()
        logger.info("Scheduler started")
        self.collect_and_analyze()
        try:
            self.run_backtest_optimize()
        except Exception:
            logger.warning("Initial backtest optimization skipped")
        self.scheduler.start()
