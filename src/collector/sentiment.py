import logging

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.collector.base import BaseCollector
from src.db.models import FearGreedIndex

logger = logging.getLogger(__name__)

FEAR_GREED_URL = "https://api.alternative.me/fng/"


class SentimentCollector(BaseCollector):
    source_name = "fear_greed"

    def collect_fear_greed(self, session: Session, limit: int = 30) -> int:
        data = self._get(FEAR_GREED_URL, {"limit": limit, "format": "json"})
        now = self.now()
        rows = []

        for item in data.get("data", []):
            rows.append(
                {
                    "value": int(item["value"]),
                    "classification": item["value_classification"],
                    "timestamp": self.ms_to_datetime(int(item["timestamp"]) * 1000),
                    "collected_at": now,
                }
            )

        if not rows:
            return 0

        stmt = sqlite_insert(FearGreedIndex).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["timestamp"],
            set_={
                "value": stmt.excluded.value,
                "classification": stmt.excluded.classification,
                "collected_at": stmt.excluded.collected_at,
            },
        )
        session.execute(stmt)
        session.commit()
        logger.info("Collected %d fear & greed records", len(rows))
        return len(rows)
