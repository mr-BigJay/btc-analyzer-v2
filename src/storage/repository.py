"""Central Data Repository — Layer 5 Storage (Ch.2 §2.4 / Ch.3 §3.12–3.13).

Responsibilities:
  - Historical append-only storage
  - File + memory caching / snapshots (fault tolerance)
  - Time-series management

Design Rule 1: modules must not reach into each other's tables.
All persistence goes through this repository facade.
Historical data is never overwritten — always append.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.config import settings
from src.db.models import (
    CoinExAnalysisRecord,
    FuturesMarketRecord,
    LiquidationEventRecord,
    OptionsMarketRecord,
    OrderBookSnapshotRecord,
    SpotMarketRecord,
    TechnicalCacheRecord,
    get_session,
    init_db,
)
from src.storage.cache import global_cache

logger = logging.getLogger(__name__)


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


class CentralRepository:
    """Single storage gateway for snapshots and historical records."""

    def __init__(self) -> None:
        self.cache_dir = settings.data_dir / "snapshots"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory = global_cache

    def _snapshot_path(self, module: str) -> Path:
        safe = module.lower().replace(" ", "_")
        return self.cache_dir / f"{safe}.json"

    def save_snapshot(self, module: str, payload: dict[str, Any]) -> None:
        path = self._snapshot_path(module)
        envelope = {
            **payload,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug("Snapshot saved for %s → %s", module, path)

    def load_snapshot(self, module: str) -> dict[str, Any] | None:
        path = self._snapshot_path(module)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Corrupt snapshot for %s: %s", module, exc)
            return None

    def cache_hot(self, module: str, payload: dict[str, Any]) -> None:
        """Update in-memory hot keys from a module result (Ch.3 §3.12)."""
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        module_l = module.lower()
        if module_l == "binance":
            if data.get("funding_rate") is not None:
                self.memory.set("latest_funding_rate", data.get("funding_rate"))
            if data.get("open_interest") is not None:
                self.memory.set("current_open_interest", data.get("open_interest"))
            if data.get("mark_price") is not None:
                self.memory.set("latest_mark_price", data.get("mark_price"))
            if data.get("order_book"):
                self.memory.set("current_order_book", data.get("order_book"))
        elif module_l == "deribit":
            if data.get("option_chain") is not None:
                self.memory.set("latest_option_chain", data.get("option_chain"))
        elif module_l == "bitunix":
            self.memory.set("bitunix_validation_snapshot", data)

    def ensure_schema(self) -> None:
        init_db()

    def session(self):
        """ORM session for historical tables — do not bypass this facade."""
        return get_session()

    # --- Append-only writers (invalid records must never reach here) ---

    def append_futures(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            row = FuturesMarketRecord(
                timestamp=_parse_ts(record.get("timestamp")),
                symbol=str(record.get("symbol", "BTCUSDT")),
                exchange=str(record.get("exchange", "binance")),
                price=_f(record.get("price")),
                mark_price=_f(record.get("mark_price")),
                index_price=_f(record.get("index_price")),
                funding_rate=_f(record.get("funding_rate")),
                open_interest=_f(record.get("open_interest")),
                open_interest_value=_f(record.get("open_interest_value")),
                long_short_ratio=_f(record.get("long_short_ratio")),
                volume=_f(record.get("volume")),
                basis=_f(record.get("basis")),
                source_id=str(record.get("source_id") or uuid4()),
                payload=json.dumps(record, ensure_ascii=False, default=str),
            )
            session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_options(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            row = OptionsMarketRecord(
                timestamp=_parse_ts(record.get("timestamp")),
                symbol=str(record.get("symbol", "BTCUSDT")),
                exchange=str(record.get("exchange", "deribit")),
                put_call_ratio=_f(record.get("put_call_ratio")),
                max_pain=_f(record.get("max_pain")),
                iv_rank=_f(record.get("iv_rank")),
                gamma_exposure=_f(record.get("gamma_exposure")),
                volume=_f(record.get("volume")),
                open_interest=_f(record.get("open_interest")),
                source_id=str(record.get("source_id") or uuid4()),
                payload=json.dumps(record, ensure_ascii=False, default=str),
            )
            session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_spot(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            row = SpotMarketRecord(
                timestamp=_parse_ts(record.get("timestamp")),
                symbol=str(record.get("symbol", "BTCUSDT")),
                exchange=str(record.get("exchange", "binance")),
                price=_f(record.get("price")),
                volume=_f(record.get("volume")),
                source_id=str(record.get("source_id") or uuid4()),
                payload=json.dumps(record, ensure_ascii=False, default=str),
            )
            session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_coinex_analysis(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            parsed = record.get("parsed") or record
            row = CoinExAnalysisRecord(
                timestamp=_parse_ts(record.get("timestamp")),
                symbol=str(record.get("symbol", "BTCUSDT")),
                publication_time=record.get("publication_time"),
                summary=record.get("summary"),
                confidence_score=_f(record.get("confidence_score")),
                raw_article=record.get("raw_article"),
                parsed_payload=json.dumps(parsed, ensure_ascii=False, default=str),
                source_id=str(record.get("source_id") or uuid4()),
            )
            session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_orderbook(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            row = OrderBookSnapshotRecord(
                timestamp=_parse_ts(record.get("timestamp")),
                symbol=str(record.get("symbol", "BTCUSDT")),
                exchange=str(record.get("exchange", "binance")),
                spread=_f(record.get("spread")),
                source_id=str(record.get("source_id") or uuid4()),
                payload=json.dumps(record, ensure_ascii=False, default=str),
            )
            session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_liquidation(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            row = LiquidationEventRecord(
                timestamp=_parse_ts(record.get("timestamp")),
                symbol=str(record.get("symbol", "BTCUSDT")),
                exchange=str(record.get("exchange", "binance")),
                side=record.get("side"),
                price=_f(record.get("price")),
                quantity=_f(record.get("quantity")),
                source_id=str(record.get("source_id") or uuid4()),
                payload=json.dumps(record, ensure_ascii=False, default=str),
            )
            session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_technical_cache(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            row = TechnicalCacheRecord(
                timestamp=_parse_ts(record.get("timestamp")),
                symbol=str(record.get("symbol", "BTCUSDT")),
                timeframe=str(record.get("timeframe", "1h")),
                source_id=str(record.get("source_id") or uuid4()),
                payload=json.dumps(record, ensure_ascii=False, default=str),
            )
            session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
