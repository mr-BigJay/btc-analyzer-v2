"""Scheduler — independent collector intervals (Ch.3 §3.14).

| Interval              | Task                          |
|-----------------------|-------------------------------|
| Real-Time (WS)        | Trades, Order Book, Liqs      |
| 1 Minute              | Price, Funding, Open Interest |
| 5 Minutes             | Technical Cache Refresh       |
| 1 Hour                | Option Chain Update           |
| Daily 03:30 UTC       | Daily Outlook Generation      |
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings

logger = logging.getLogger(__name__)


class AppScheduler:
    def __init__(self) -> None:
        self.scheduler = BlockingScheduler(timezone="UTC")
        self._engine = None
        self._ws_started = False

    @property
    def engine(self):
        if self._engine is None:
            from src.collectors.engine import DataCollectionEngine

            self._engine = DataCollectionEngine()
        return self._engine

    def job_minute_collect(self) -> None:
        """1-minute: price, funding, open interest."""
        try:
            result = self.engine.run_minute_cycle_sync()
            logger.info(
                "minute_collect ok=%s warnings=%s",
                result.ok,
                len(result.warnings),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("minute_collect failed (continuing): %s", exc)

    def job_technical_cache(self) -> None:
        """5-minute: technical cache refresh."""
        try:
            result = self.engine.run_technical_cache_sync()
            logger.info("technical_cache ok=%s", result.ok)
        except Exception as exc:  # noqa: BLE001
            logger.warning("technical_cache failed (continuing): %s", exc)

    def job_options_chain(self) -> None:
        """1-hour: option chain update."""
        try:
            result = self.engine.run_options_cycle_sync()
            logger.info("options_chain ok=%s", result.ok)
        except Exception as exc:  # noqa: BLE001
            logger.warning("options_chain failed (continuing): %s", exc)

    def job_daily_outlook(self) -> None:
        """Daily 03:30 UTC — also refreshes CoinEx narrative first."""
        try:
            narr = self.engine.run_narrative_cycle_sync()
            logger.info("daily narrative ok=%s", narr.ok)
        except Exception as exc:  # noqa: BLE001
            logger.warning("daily narrative failed (continuing): %s", exc)
        logger.info(
            "Daily Outlook job stub @ %02d:%02d UTC — awaiting Design Book Ch.5+",
            settings.daily_outlook_hour_utc,
            settings.daily_outlook_minute_utc,
        )

    def job_intraday_plan(self) -> None:
        logger.info("Intraday Trading Plan job stub — awaiting Design Book Ch.6+")

    def _start_realtime_streams(self) -> None:
        """Real-time WS: trades, depth, liquidations (best-effort)."""
        if self._ws_started or not settings.binance_futures_enabled:
            return
        try:
            def _on_msg(payload: dict) -> None:
                stream = ""
                data = payload
                if isinstance(payload, dict) and "stream" in payload:
                    stream = str(payload.get("stream") or "")
                    data = payload.get("data") or {}
                # Persist liquidations only (append-only); avoid flooding DB with every trade
                if "forceOrder" in stream or (
                    isinstance(data, dict) and data.get("e") == "forceOrder"
                ):
                    order = (data.get("o") or data) if isinstance(data, dict) else {}
                    self.engine.repository.append_liquidation(
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

            self.engine.binance.start_websocket(on_message=_on_msg)
            self._ws_started = True
            logger.info("Binance real-time WebSocket streams started")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Realtime WS not started: %s", exc)

    def start(self) -> None:
        self.engine.repository.ensure_schema()
        self._start_realtime_streams()

        self.scheduler.add_job(
            self.job_minute_collect,
            "interval",
            minutes=1,
            id="collect_1m",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.job_technical_cache,
            "interval",
            minutes=5,
            id="technical_cache_5m",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.job_options_chain,
            "interval",
            hours=1,
            id="options_1h",
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
            minutes=5,
            id="intraday_plan",
            replace_existing=True,
        )
        logger.info(
            "Scheduler started (Ch.3): 1m market · 5m technical · 1h options · daily %02d:%02d UTC",
            settings.daily_outlook_hour_utc,
            settings.daily_outlook_minute_utc,
        )
        self.scheduler.start()
