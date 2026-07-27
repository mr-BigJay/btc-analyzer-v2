"""APScheduler application — isolated jobs (Ch.3 §3.14 / Ch.5 §5.8).

| Interval              | Task                          |
|-----------------------|-------------------------------|
| Real-Time (WS)        | Trades, Order Book, Liqs      |
| 1 Minute              | Funding, OI, Trades           |
| 5 Minutes             | Technical Indicators          |
| 15 Minutes            | Pattern Detection             |
| 1 Hour                | Options Metrics               |
| Daily 03:30 UTC       | Daily Outlook Generation      |
"""

from __future__ import annotations

import time

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings
from src.logging_setup import get_logger, setup_logging
from src.services import AnalysisService, CollectionService

setup_logging()
log = get_logger("scheduler")


class AppScheduler:
    def __init__(self) -> None:
        self.scheduler = BlockingScheduler(timezone=settings.timezone or "UTC")
        self._collection: CollectionService | None = None
        self._analysis: AnalysisService | None = None
        self._ws_started = False

    @property
    def collection(self) -> CollectionService:
        if self._collection is None:
            self._collection = CollectionService()
        return self._collection

    @property
    def analysis(self) -> AnalysisService:
        if self._analysis is None:
            self._analysis = AnalysisService()
        return self._analysis

    @property
    def engine(self):
        """Back-compat for code expecting DataCollectionEngine."""
        return self.collection.engine

    def _run_isolated(self, job_id: str, fn) -> None:
        started = time.monotonic()
        try:
            result = fn()
            ms = (time.monotonic() - started) * 1000
            ok = True
            msg = None
            if hasattr(result, "ok"):
                ok = bool(result.ok)
                msg = str(getattr(result, "warnings", [])[:3])
            elif isinstance(result, dict):
                ok = result.get("status") != "ERROR"
                msg = result.get("warning")
            self.collection.engine.repository.log_scheduler(
                job_id, "OK" if ok else "DEGRADED", message=msg, duration_ms=ms
            )
            log.info("{} ok={} duration_ms={:.0f}", job_id, ok, ms)
        except Exception as exc:  # noqa: BLE001
            self.collection.engine.repository.log_scheduler(job_id, "ERROR", message=str(exc))
            self.collection.engine.repository.log_error("scheduler", str(exc), error_code=job_id)
            log.warning("{} failed (continuing): {}", job_id, exc)

    def job_minute_collect(self) -> None:
        self._run_isolated("collect_1m", self.collection.run_minute)

    def job_technical_cache(self) -> None:
        def _job():
            collected = self.collection.run_technical()
            analysis = self.analysis.refresh_technical()
            return {"ok": collected.ok, "warnings": collected.warnings, "analysis": analysis}

        self._run_isolated("technical_5m", _job)

    def job_pattern_detection(self) -> None:
        """15-minute pattern detection (Ch.5 §5.8)."""
        self._run_isolated("patterns_15m", self.analysis.detect_patterns)

    def job_options_chain(self) -> None:
        self._run_isolated("options_1h", self.collection.run_options)

    def job_daily_outlook(self) -> None:
        def _job():
            try:
                from src.db.retention import apply_retention

                deleted = apply_retention()
                self.collection.engine.repository.log_scheduler("retention", "OK", message=str(deleted))
            except Exception as exc:  # noqa: BLE001
                log.warning("retention failed: {}", exc)
            narr = self.collection.run_narrative()
            log.info("Daily Outlook stub @ {:02d}:{:02d} UTC — awaiting Ch.6+", settings.daily_outlook_hour_utc, settings.daily_outlook_minute_utc)
            return narr

        self._run_isolated("daily_outlook", _job)

    def job_intraday_plan(self) -> None:
        log.info("Intraday Trading Plan job stub — awaiting Design Book Ch.6+")

    def _start_realtime_streams(self) -> None:
        if self._ws_started or not settings.binance_futures_enabled:
            return
        try:
            def _on_msg(payload: dict) -> None:
                stream = ""
                data = payload
                if isinstance(payload, dict) and "stream" in payload:
                    stream = str(payload.get("stream") or "")
                    data = payload.get("data") or {}
                if "forceOrder" in stream or (
                    isinstance(data, dict) and data.get("e") == "forceOrder"
                ):
                    order = (data.get("o") or data) if isinstance(data, dict) else {}
                    self.collection.engine.repository.append_liquidation(
                        {
                            "timestamp": order.get("T") or data.get("E"),
                            "symbol": order.get("s") or settings.binance_symbol,
                            "exchange": "binance",
                            "side": order.get("S"),
                            "price": order.get("p"),
                            "quantity": order.get("q"),
                            "source_id": str(order.get("T") or data.get("E") or ""),
                            "payload": data,
                        }
                    )
                # Mark price → hot cache (WS broadcast is async; best-effort sync set)
                if "markPrice" in stream or (isinstance(data, dict) and data.get("e") == "markPriceUpdate"):
                    from src.cache.keys import CacheKeys
                    from src.storage.redis_cache import redis_cache

                    price = data.get("p") or data.get("markPrice")
                    if price is not None:
                        redis_cache.set(CacheKeys.LATEST_MARK_PRICE, float(price))

            self.collection.engine.binance.start_websocket(on_message=_on_msg)
            self._ws_started = True
            log.info("Binance real-time WebSocket streams started")
        except Exception as exc:  # noqa: BLE001
            log.warning("Realtime WS not started: {}", exc)

    def start(self) -> None:
        self.collection.engine.repository.ensure_schema()
        self._start_realtime_streams()

        self.scheduler.add_job(self.job_minute_collect, "interval", minutes=1, id="collect_1m", replace_existing=True)
        self.scheduler.add_job(self.job_technical_cache, "interval", minutes=5, id="technical_5m", replace_existing=True)
        self.scheduler.add_job(self.job_pattern_detection, "interval", minutes=15, id="patterns_15m", replace_existing=True)
        self.scheduler.add_job(self.job_options_chain, "interval", hours=1, id="options_1h", replace_existing=True)
        self.scheduler.add_job(
            self.job_daily_outlook,
            "cron",
            hour=settings.daily_outlook_hour_utc,
            minute=settings.daily_outlook_minute_utc,
            id="daily_outlook",
            replace_existing=True,
        )
        self.scheduler.add_job(self.job_intraday_plan, "interval", minutes=5, id="intraday_plan", replace_existing=True)
        log.info(
            "Scheduler started (Ch.5): 1m · 5m technical · 15m patterns · 1h options · daily {:02d}:{:02d} {}",
            settings.daily_outlook_hour_utc,
            settings.daily_outlook_minute_utc,
            settings.timezone,
        )
        self.scheduler.start()
