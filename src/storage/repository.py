"""Central Data Repository — SSOT facade (Ch.2 / Ch.3 / Ch.4).

All modules read and write through this layer. No orphan records:
every market row references exchange_id + symbol_id.
Historical rows are append-only. Hot data also mirrored to Redis/memory.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings
from src.db.models import (
    ApiCallLog,
    CoinExAnalysis,
    ErrorLog,
    FundingRate,
    Liquidation,
    MarketCandle,
    OpenInterest,
    OptionsAnalyticsSnapshot,
    OptionsChain,
    OrderBookSnapshot,
    SchedulerLog,
    TechnicalIndicator,
    Trade,
)
from src.db.seed import resolve_exchange_id, resolve_symbol_id
from src.db.session import get_session, init_db
from src.storage.cache import global_cache
from src.storage.redis_cache import redis_cache

logger = logging.getLogger(__name__)


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return datetime.now(timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class CentralRepository:
    """Single storage gateway for snapshots and historical records."""

    def __init__(self) -> None:
        self.cache_dir = settings.data_dir / "snapshots"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory = global_cache
        self.redis = redis_cache

    def _snapshot_path(self, module: str) -> Path:
        safe = module.lower().replace(" ", "_")
        return self.cache_dir / f"{safe}.json"

    def save_snapshot(self, module: str, payload: dict[str, Any]) -> None:
        path = self._snapshot_path(module)
        envelope = {**payload, "cached_at": datetime.now(timezone.utc).isoformat()}
        path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        self.redis.set(f"snapshot:{module.lower()}", envelope, ttl_sec=3600)

    def load_snapshot(self, module: str) -> dict[str, Any] | None:
        cached = self.redis.get(f"snapshot:{module.lower()}")
        if isinstance(cached, dict):
            return cached
        path = self._snapshot_path(module)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Corrupt snapshot for %s: %s", module, exc)
            return None

    def cache_hot(self, module: str, payload: dict[str, Any]) -> None:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        module_l = module.lower()
        ttl = settings.redis_hot_ttl_sec
        if module_l == "binance":
            if data.get("funding_rate") is not None:
                self.memory.set("latest_funding_rate", data.get("funding_rate"))
                self.redis.set("latest_funding_rate", data.get("funding_rate"), ttl_sec=ttl)
            if data.get("open_interest") is not None:
                self.memory.set("current_open_interest", data.get("open_interest"))
                self.redis.set("current_open_interest", data.get("open_interest"), ttl_sec=ttl)
            if data.get("mark_price") is not None:
                self.memory.set("latest_mark_price", data.get("mark_price"))
                self.redis.set("latest_mark_price", data.get("mark_price"), ttl_sec=ttl)
            if data.get("order_book"):
                self.memory.set("current_order_book", data.get("order_book"))
                self.redis.set("current_order_book", data.get("order_book"), ttl_sec=ttl)
        elif module_l == "deribit":
            if data.get("option_chain") is not None:
                # Store compact summary in redis; full chain can be large
                summary = {
                    "count": len(data.get("option_chain") or []),
                    "put_call_ratio": data.get("put_call_ratio"),
                    "max_pain": data.get("max_pain"),
                    "gamma_exposure": data.get("gamma_exposure"),
                }
                self.memory.set("latest_option_chain", data.get("option_chain"))
                self.redis.set("latest_option_chain_summary", summary, ttl_sec=ttl)
        elif module_l == "bitunix":
            self.memory.set("bitunix_validation_snapshot", data)
            self.redis.set("bitunix_validation_snapshot", data, ttl_sec=ttl)
        elif module_l == "coinex":
            self.redis.set("active_daily_outlook_narrative", data, ttl_sec=ttl)

    def ensure_schema(self) -> None:
        init_db(seed=True)

    def session(self):
        return get_session()

    # --- Append-only writers mapped to Ch.4 tables ---

    def append_futures(self, record: dict[str, Any]) -> None:
        """Split futures snapshot into funding_rates + open_interest (+ optional extras)."""
        session = get_session()
        try:
            exchange_id = resolve_exchange_id(session, str(record.get("exchange", "binance")))
            symbol_id = resolve_symbol_id(session, str(record.get("symbol", "BTCUSDT")))
            ts = _parse_ts(record.get("timestamp"))

            if record.get("funding_rate") is not None:
                session.add(
                    FundingRate(
                        exchange_id=exchange_id,
                        symbol_id=symbol_id,
                        timestamp=ts,
                        funding_rate=float(record["funding_rate"]),
                        predicted_rate=_f(record.get("predicted_rate")),
                    )
                )
            if record.get("open_interest") is not None:
                session.add(
                    OpenInterest(
                        exchange_id=exchange_id,
                        symbol_id=symbol_id,
                        timestamp=ts,
                        oi=float(record["open_interest"]),
                        oi_value=_f(record.get("open_interest_value")),
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_options(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            exchange_id = resolve_exchange_id(session, str(record.get("exchange", "deribit")))
            symbol_id = resolve_symbol_id(session, str(record.get("symbol", "BTCUSDT")))
            ts = _parse_ts(record.get("timestamp"))

            session.add(
                OptionsAnalyticsSnapshot(
                    exchange_id=exchange_id,
                    symbol_id=symbol_id,
                    timestamp=ts,
                    put_call_ratio=_f(record.get("put_call_ratio")),
                    max_pain=_f(record.get("max_pain")),
                    iv_rank=_f(record.get("iv_rank")),
                    iv_percentile=_f(record.get("iv_percentile")),
                    gamma_exposure=_f(record.get("gamma_exposure")),
                    dealer_gamma=_f(record.get("dealer_gamma")),
                    dealer_delta=_f(record.get("dealer_delta")),
                    volatility_skew=_f(record.get("volatility_skew")),
                    payload=json.dumps(
                        {k: record.get(k) for k in ("volume", "open_interest") if k in record},
                        default=str,
                    ),
                )
            )

            chain = record.get("option_chain") or []
            # Batch insert — limit per cycle to protect write amplification
            batch = chain[:500]
            rows = []
            for item in batch:
                if not isinstance(item, dict):
                    continue
                greeks = item.get("greeks") if isinstance(item.get("greeks"), dict) else {}
                exp = item.get("expiration")
                exp_dt = _parse_ts(exp) if exp is not None else None
                rows.append(
                    OptionsChain(
                        exchange_id=exchange_id,
                        symbol_id=symbol_id,
                        expiration=exp_dt,
                        strike=_f(item.get("strike")),
                        type=(item.get("option_type") or item.get("type") or None),
                        iv=_f(item.get("mark_iv") or item.get("iv")),
                        delta=_f(greeks.get("delta")),
                        gamma=_f(greeks.get("gamma")),
                        theta=_f(greeks.get("theta")),
                        vega=_f(greeks.get("vega")),
                        open_interest=_f(item.get("open_interest")),
                        volume=_f(item.get("volume")),
                        instrument=item.get("instrument"),
                        timestamp=ts,
                    )
                )
            if rows:
                session.add_all(rows)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_spot(self, record: dict[str, Any]) -> None:
        """Spot tick stored as a 1-tick candle proxy when OHLCV unavailable."""
        price = _f(record.get("price"))
        if price is None:
            return
        session = get_session()
        try:
            exchange_id = resolve_exchange_id(session, str(record.get("exchange", "binance")))
            symbol_id = resolve_symbol_id(session, str(record.get("symbol", "BTCUSDT")))
            ts = _parse_ts(record.get("timestamp"))
            session.add(
                MarketCandle(
                    exchange_id=exchange_id,
                    symbol_id=symbol_id,
                    timeframe="tick",
                    timestamp=ts,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=_f(record.get("volume")) or 0.0,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_coinex_analysis(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            symbol_id = resolve_symbol_id(session, str(record.get("symbol", "BTCUSDT")))
            pub = record.get("publication_time") or record.get("timestamp")
            session.add(
                CoinExAnalysis(
                    published_at=_parse_ts(pub) if pub else None,
                    title=record.get("summary"),
                    summary=record.get("summary"),
                    full_text=record.get("raw_article") or record.get("full_text"),
                    bullish_points=json.dumps(record.get("bullish_arguments") or [], ensure_ascii=False),
                    bearish_points=json.dumps(record.get("bearish_arguments") or [], ensure_ascii=False),
                    support_levels=json.dumps(record.get("support_levels") or [], ensure_ascii=False),
                    resistance_levels=json.dumps(record.get("resistance_levels") or [], ensure_ascii=False),
                    confidence_score=_f(record.get("confidence_score")),
                    bias=record.get("bias"),
                    symbol_id=symbol_id,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_orderbook(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            exchange_id = resolve_exchange_id(session, str(record.get("exchange", "binance")))
            symbol_id = resolve_symbol_id(session, str(record.get("symbol", "BTCUSDT")))
            book = record.get("order_book") or {}
            bids = book.get("bids") or []
            asks = book.get("asks") or []
            best_bid = _f(bids[0][0]) if bids and isinstance(bids[0], (list, tuple)) else _f(record.get("best_bid"))
            best_ask = _f(asks[0][0]) if asks and isinstance(asks[0], (list, tuple)) else _f(record.get("best_ask"))
            spread = _f(record.get("spread"))
            if spread is None and best_bid is not None and best_ask is not None:
                spread = best_ask - best_bid
            imbalance = _f(record.get("imbalance"))
            if imbalance is None and best_bid is not None and best_ask is not None and (best_bid + best_ask):
                imbalance = (best_bid - best_ask) / (best_bid + best_ask)

            session.add(
                OrderBookSnapshot(
                    exchange_id=exchange_id,
                    symbol_id=symbol_id,
                    timestamp=_parse_ts(record.get("timestamp")),
                    best_bid=best_bid,
                    best_ask=best_ask,
                    spread=spread,
                    imbalance=imbalance,
                    payload=json.dumps(book or record, ensure_ascii=False, default=str),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_liquidation(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            exchange_id = resolve_exchange_id(session, str(record.get("exchange", "binance")))
            symbol_id = resolve_symbol_id(session, str(record.get("symbol", "BTCUSDT")))
            session.add(
                Liquidation(
                    exchange_id=exchange_id,
                    symbol_id=symbol_id,
                    timestamp=_parse_ts(record.get("timestamp")),
                    side=record.get("side"),
                    price=_f(record.get("price")),
                    quantity=_f(record.get("quantity")),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_technical_cache(self, record: dict[str, Any]) -> None:
        """Persist OHLCV candles from technical refresh; indicator calc awaits Ch.5+."""
        session = get_session()
        try:
            exchange_id = resolve_exchange_id(session, str(record.get("exchange", "binance")))
            symbol_id = resolve_symbol_id(session, str(record.get("symbol", "BTCUSDT")))
            timeframe = str(record.get("timeframe", "1h"))
            ohlcv = record.get("ohlcv") or []
            rows = []
            for candle in ohlcv[-200:]:
                if not isinstance(candle, dict):
                    continue
                o = _f(candle.get("open"))
                h = _f(candle.get("high"))
                low = _f(candle.get("low"))
                c = _f(candle.get("close"))
                if None in (o, h, low, c):
                    continue
                rows.append(
                    MarketCandle(
                        exchange_id=exchange_id,
                        symbol_id=symbol_id,
                        timeframe=timeframe,
                        timestamp=_parse_ts(candle.get("open_time") or record.get("timestamp")),
                        open=o,
                        high=h,
                        low=low,
                        close=c,
                        volume=_f(candle.get("volume")) or 0.0,
                    )
                )
            if rows:
                session.add_all(rows)

            # Placeholder technical_indicators row for cache refresh marker
            session.add(
                TechnicalIndicator(
                    symbol_id=symbol_id,
                    timeframe=timeframe,
                    timestamp=_parse_ts(record.get("timestamp")),
                    payload=json.dumps({"source": "technical_cache_refresh", "candles": len(rows)}, default=str),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_trade(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            exchange_id = resolve_exchange_id(session, str(record.get("exchange", "binance")))
            symbol_id = resolve_symbol_id(session, str(record.get("symbol", "BTCUSDT")))
            session.add(
                Trade(
                    exchange_id=exchange_id,
                    symbol_id=symbol_id,
                    timestamp=_parse_ts(record.get("timestamp")),
                    price=float(record["price"]),
                    quantity=float(record["quantity"]),
                    side=record.get("side"),
                    aggressor=record.get("aggressor"),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def log_api_call(
        self,
        exchange: str,
        endpoint: str,
        *,
        response_time_ms: float | None,
        status: str,
        error_code: str | None = None,
        retry_count: int = 0,
    ) -> None:
        session = get_session()
        try:
            session.add(
                ApiCallLog(
                    exchange=exchange,
                    endpoint=endpoint,
                    response_time_ms=response_time_ms,
                    status=status,
                    error_code=error_code,
                    retry_count=retry_count,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            logger.debug("api_call_log persist failed", exc_info=True)
        finally:
            session.close()

    def log_scheduler(self, job_id: str, status: str, message: str | None = None, duration_ms: float | None = None) -> None:
        session = get_session()
        try:
            session.add(SchedulerLog(job_id=job_id, status=status, message=message, duration_ms=duration_ms))
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def log_error(self, module: str, message: str, error_code: str | None = None, details: str | None = None) -> None:
        session = get_session()
        try:
            session.add(ErrorLog(module=module, message=message, error_code=error_code, details=details))
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
