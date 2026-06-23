import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.collector.market import MarketDataCollector
from src.collector.onchain import OnChainCollector
from src.collector.sentiment import SentimentCollector
from src.db.models import CollectionLog, get_session

logger = logging.getLogger(__name__)


class CollectionOrchestrator:
    """Runs all data collectors and logs results."""

    def __init__(self) -> None:
        self.market = MarketDataCollector()
        self.sentiment = SentimentCollector()
        self.onchain = OnChainCollector()

    def _log_collection(
        self,
        session: Session,
        source: str,
        status: str,
        records: int,
        message: str | None,
        started: datetime,
    ) -> None:
        log = CollectionLog(
            source=source,
            status=status,
            records_count=records,
            message=message,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
        )
        session.add(log)
        session.commit()

    def run_all(self) -> dict[str, dict]:
        session = get_session()
        results: dict[str, dict] = {}

        collectors = [
            ("klines", self._collect_klines),
            ("ticker", self._collect_ticker),
            ("derivatives", self._collect_derivatives),
            ("sentiment", self._collect_sentiment),
            ("onchain", self._collect_onchain),
        ]

        for name, func in collectors:
            started = datetime.now(timezone.utc)
            try:
                count = func(session)
                self._log_collection(session, name, "success", count, None, started)
                results[name] = {"status": "success", "records": count}
                logger.info("Collection [%s] OK — %d records", name, count)
            except Exception as exc:
                session.rollback()
                self._log_collection(session, name, "error", 0, str(exc), started)
                results[name] = {"status": "error", "error": str(exc)}
                logger.exception("Collection [%s] failed", name)

        session.close()
        return results

    def _collect_klines(self, session: Session) -> int:
        return self.market.collect_all_timeframes(session)

    def _collect_ticker(self, session: Session) -> int:
        return self.market.collect_ticker(session)

    def _collect_derivatives(self, session: Session) -> int:
        return self.market.collect_derivatives(session)

    def _collect_sentiment(self, session: Session) -> int:
        return self.sentiment.collect_fear_greed(session)

    def _collect_onchain(self, session: Session) -> int:
        return self.onchain.collect(session)
