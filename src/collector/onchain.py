import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.collector.base import BaseCollector
from src.db.models import OnChainMetric

logger = logging.getLogger(__name__)

COINMETRICS_URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
METRICS = ["AdrActCnt", "CapMVRVCur"]


class OnChainCollector(BaseCollector):
    source_name = "coinmetrics"

    def collect(self, session: Session, page_size: int = 90) -> int:
        data = self._get(
            COINMETRICS_URL,
            {
                "assets": "btc",
                "metrics": ",".join(METRICS),
                "page_size": page_size,
            },
        )
        rows_data = data.get("data", [])
        if not rows_data:
            return 0

        now = self.now()
        rows = []

        for item in rows_data:
            ts = self._parse_time(item["time"])
            if "AdrActCnt" in item and item["AdrActCnt"] is not None:
                rows.append(
                    {
                        "metric_name": "active_addresses",
                        "value": float(item["AdrActCnt"]),
                        "timestamp": ts,
                        "collected_at": now,
                    }
                )
            if "CapMVRVCur" in item and item["CapMVRVCur"] is not None:
                rows.append(
                    {
                        "metric_name": "mvrv",
                        "value": float(item["CapMVRVCur"]),
                        "timestamp": ts,
                        "collected_at": now,
                    }
                )

        if not rows:
            return 0

        stmt = sqlite_insert(OnChainMetric).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["metric_name", "timestamp"],
            set_={
                "value": stmt.excluded.value,
                "collected_at": stmt.excluded.collected_at,
            },
        )
        session.execute(stmt)
        session.commit()
        logger.info("Collected %d on-chain metric records", len(rows))
        return len(rows)

    @staticmethod
    def _parse_time(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
