import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.analyzer.serialize import analysis_to_json
from src.analyzer.service import AnalysisService
from src.collector.orchestrator import CollectionOrchestrator
from src.config import settings
from src.db.models import AnalysisSnapshot, get_session, init_db
from src.notifier.formatters import overview_message, signal_alert

logger = logging.getLogger(__name__)


class AppScheduler:
    def __init__(self, telegram_service=None) -> None:
        self.collector = CollectionOrchestrator()
        self.analysis = AnalysisService()
        self.telegram = telegram_service
        self._last_trends: dict[str, str] = {}
        self.scheduler = BlockingScheduler(timezone="UTC")

    def collect_and_analyze(self) -> None:
        logger.info("Running scheduled collection...")
        self.collector.run_all()
        self._run_analysis(save=True, notify=bool(self.telegram))

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
                self._check_alerts(analysis)
        except Exception:
            logger.exception("Analysis failed")
        finally:
            session.close()

    def _check_alerts(self, analysis) -> None:
        import asyncio

        if not self.telegram:
            return

        async def _send():
            for tf in settings.timeframes:
                t = analysis.timeframes[tf]
                trend = t.trend.value if hasattr(t.trend, "value") else t.trend
                prev = self._last_trends.get(tf)

                if (
                    t.confidence >= settings.alert_threshold
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

    def start(self) -> None:
        init_db()
        self.setup_jobs()
        logger.info("Scheduler started")
        self.collect_and_analyze()
        self.scheduler.start()
