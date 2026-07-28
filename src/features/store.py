"""Feature store — in-memory + DB persistence (Ch.13 §13.18)."""

from __future__ import annotations

import json
import threading
from collections import deque
from typing import Any

from src.features.contracts import FeatureSet


class FeatureStoreMemory:
    """Hot feature store for reuse by Analysis Engine."""

    def __init__(self, *, maxlen: int = 200) -> None:
        self._latest: dict[tuple[str, str], FeatureSet] = {}
        self._history: deque[FeatureSet] = deque(maxlen=maxlen)
        self._lock = threading.RLock()

    def put(self, fs: FeatureSet) -> None:
        with self._lock:
            self._latest[(fs.asset.upper(), fs.timeframe)] = fs
            self._history.append(fs)

    def get(self, asset: str = "BTCUSDT", timeframe: str = "1h") -> FeatureSet | None:
        with self._lock:
            return self._latest.get((asset.upper(), timeframe))

    def recent(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._history)[-limit:]
        return [fs.to_dict() for fs in items]

    def clear(self) -> None:
        with self._lock:
            self._latest.clear()
            self._history.clear()


feature_store_memory = FeatureStoreMemory()


def persist_feature_set(fs: FeatureSet, *, module: str = "analysis") -> int | None:
    """Append feature set JSON into DB feature_store table when available."""
    try:
        from src.db.access import assert_can_write
        from src.db.models.intelligence_store import FeatureStoreRecord
        from src.db.seed import resolve_symbol_id
        from src.db.session import get_session
        from datetime import datetime, timezone

        assert_can_write(module, "feature_store")
        session = get_session()
        try:
            asset_id = resolve_symbol_id(session, fs.asset)
            ts = datetime.fromisoformat(fs.timestamp.replace("Z", "+00:00"))
            row = FeatureStoreRecord(
                asset_id=asset_id,
                timeframe=fs.timeframe,
                timestamp=ts,
                feature_set_version=fs.feature_version,
                calculation_engine=fs.calculation_engine,
                schema_version=fs.schema_version,
                data_quality=fs.data_quality,
                missing_count=fs.missing_count,
                payload=json.dumps(fs.to_dict(), ensure_ascii=False, default=str),
            )
            session.add(row)
            session.commit()
            return int(row.id)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    except Exception:
        return None
