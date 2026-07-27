"""Scheduler — Daily Outlook @ 03:30 UTC, collection loop, intraday plans.

Jobs are stubs until Design Docs 02–08 specify collection and generation logic.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings

logger = logging.getLogger(__name__)


class AppScheduler:
    def __init__(self) -> None:
        self.scheduler = BlockingScheduler(timezone="UTC")

    def job_collect(self) -> None:
        logger.info("collect job stub — awaiting Design Doc 02+")

    def job_daily_outlook(self) -> None:
        logger.info(
            "Daily Outlook job stub @ %02d:%02d UTC — awaiting Design Doc 02+",
            settings.daily_outlook_hour_utc,
            settings.daily_outlook_minute_utc,
        )

    def job_intraday_plan(self) -> None:
        logger.info("Intraday Trading Plan job stub — requires existing Daily Outlook")

    def start(self) -> None:
        self.scheduler.add_job(
            self.job_collect,
            "interval",
            minutes=settings.collection_interval_minutes,
            id="collect",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.job_daily_outlook,
            "cron",
            hour=settings.daily_outlook_hour_utc,
            minute=settings.daily_outlook_minute_utc,
            id="daily_outlook",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.job_intraday_plan,
            "interval",
            minutes=max(5, settings.collection_interval_minutes),
            id="intraday_plan",
            replace_existing=True,
        )
        logger.info("Scheduler started (rewrite foundation stubs)")
        self.scheduler.start()
