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
from src.db.access import assert_can_write
from src.db.models import (
    ApiCallLog,
    CoinExAnalysis,
    DailyOutlook,
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
    TradingPlan,
)
from src.db.repositories.intelligence_repo import IntelligenceRepository
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
        """Split futures snapshot into funding_rates + open_interest + futures_data (Ch.11)."""
        session = get_session()
        try:
            assert_can_write("collector", "funding_rates")
            assert_can_write("collector", "futures_data")
            exchange = str(record.get("exchange", "binance"))
            symbol = str(record.get("symbol", "BTCUSDT"))
            exchange_id = resolve_exchange_id(session, exchange)
            symbol_id = resolve_symbol_id(session, symbol)
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
                        oi_value=_f(record.get("open_interest_value") or record.get("oi_value")),
                    )
                )
            IntelligenceRepository(session).append_futures(
                module="collector",
                symbol=symbol,
                exchange=exchange,
                timestamp=ts,
                open_interest=_f(record.get("open_interest")),
                oi_value=_f(record.get("open_interest_value") or record.get("oi_value")),
                funding_rate=_f(record.get("funding_rate")),
                long_ratio=_f(record.get("long_ratio")),
                short_ratio=_f(record.get("short_ratio")),
                liquidation_long=_f(record.get("liquidation_long")),
                liquidation_short=_f(record.get("liquidation_short")),
                payload={k: record.get(k) for k in ("mark_price", "predicted_rate") if k in record},
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
            assert_can_write("collector", "options_analytics")
            assert_can_write("collector", "options_data")
            exchange = str(record.get("exchange", "deribit"))
            symbol = str(record.get("symbol", "BTCUSDT"))
            exchange_id = resolve_exchange_id(session, exchange)
            symbol_id = resolve_symbol_id(session, symbol)
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
            IntelligenceRepository(session).append_options(
                module="collector",
                symbol=symbol,
                exchange=exchange,
                timestamp=ts,
                call_oi=_f(record.get("call_oi")),
                put_oi=_f(record.get("put_oi")),
                pcr=_f(record.get("put_call_ratio") or record.get("pcr")),
                iv=_f(record.get("iv") or record.get("iv_rank")),
                skew=_f(record.get("volatility_skew") or record.get("skew")),
                max_pain=_f(record.get("max_pain")),
                gamma_exposure=_f(record.get("gamma_exposure")),
                payload={k: record.get(k) for k in ("iv_percentile", "dealer_gamma") if k in record},
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
        """Spot tick → tick candle proxy + spot_data row (Ch.11 §11.8)."""
        price = _f(record.get("price"))
        if price is None:
            return
        session = get_session()
        try:
            assert_can_write("collector", "market_candles")
            assert_can_write("collector", "spot_data")
            exchange = str(record.get("exchange", "binance"))
            symbol = str(record.get("symbol", "BTCUSDT"))
            exchange_id = resolve_exchange_id(session, exchange)
            symbol_id = resolve_symbol_id(session, symbol)
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
            IntelligenceRepository(session).append_spot(
                module="collector",
                symbol=symbol,
                exchange=exchange,
                timestamp=ts,
                price=price,
                volume=_f(record.get("volume")),
                vwap=_f(record.get("vwap")),
                bid_volume=_f(record.get("bid_volume")),
                ask_volume=_f(record.get("ask_volume")),
                cvd=_f(record.get("cvd")),
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

    def save_daily_outlook(self, decision_payload: dict[str, Any]) -> None:
        """Persist AI Daily Outlook + Trading Plan (Ch.7 §7.13 / §7.17)."""
        outlook = decision_payload.get("daily_outlook") or {}
        plan = decision_payload.get("trading_plan") or {}
        date = str(outlook.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        scenarios = decision_payload.get("scenarios") or []
        primary = scenarios[0] if scenarios else {}
        alt = scenarios[1] if len(scenarios) > 1 else {}
        dist = decision_payload.get("probability_distribution") or {}
        bull = float(dist.get("trend_continuation") or primary.get("probability") or 50) / 100.0
        bear = float(dist.get("trend_reversal") or (alt.get("probability") if alt else 50) or 50) / 100.0
        # Normalize bull/bear share of directional mass for legacy columns
        directional = bull + bear
        if directional > 0:
            bull_p, bear_p = bull / directional, bear / directional
        else:
            bull_p = bear_p = 0.5

        session = get_session()
        try:
            row = session.query(DailyOutlook).filter_by(date=date).one_or_none()
            if row is None:
                row = DailyOutlook(date=date)
                session.add(row)
            row.bull_probability = bull_p
            row.bear_probability = bear_p
            row.risk_level = decision_payload.get("risk_level")
            row.main_scenario = json.dumps(primary, default=str)
            row.alternative_scenario = json.dumps(alt, default=str)
            row.confidence = float(decision_payload.get("confidence") or 0)
            row.payload = json.dumps(decision_payload, ensure_ascii=False, default=str)
            session.flush()

            session.add(
                TradingPlan(
                    daily_outlook_id=row.id,
                    direction=str(plan.get("preferred_direction") or "no_trade"),
                    entry_low=(plan.get("entry_zone") or [None, None])[0]
                    if plan.get("entry_zone")
                    else None,
                    entry_high=(plan.get("entry_zone") or [None, None])[1]
                    if plan.get("entry_zone") and len(plan.get("entry_zone") or []) > 1
                    else None,
                    stop_loss=plan.get("stop_loss_zone"),
                    tp1=(plan.get("target_levels") or [None])[0] if plan.get("target_levels") else None,
                    tp2=(plan.get("target_levels") or [None, None])[1]
                    if plan.get("target_levels") and len(plan.get("target_levels") or []) > 1
                    else None,
                    tp3=(plan.get("target_levels") or [None, None, None])[2]
                    if plan.get("target_levels") and len(plan.get("target_levels") or []) > 2
                    else None,
                    rr=plan.get("risk_reward"),
                    confidence=float(plan.get("confidence") or 0),
                    payload=json.dumps(plan, ensure_ascii=False, default=str),
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

    # --- Ch.11 intelligence / decision / reporting writers ---

    def append_market_score(self, decision: dict[str, Any]) -> None:
        """Persist scoring DecisionObject (Ch.11 §11.15)."""
        session = get_session()
        try:
            IntelligenceRepository(session).append_market_score(
                module="scoring",
                symbol=str(decision.get("symbol") or "BTCUSDT"),
                bias_score=float(decision.get("market_bias_score") or decision.get("bias_score") or 0),
                confidence_score=float(decision.get("confidence_score") or 0),
                risk_score=float(decision.get("risk_score") or 0),
                mhi=_f(decision.get("market_health_index") or decision.get("mhi")),
                msi=_f(decision.get("market_stress_index") or decision.get("msi")),
                data_quality=_f(decision.get("data_quality_score") or decision.get("data_quality")),
                market_bias=decision.get("market_bias") or decision.get("decision"),
                weight_regime=decision.get("weight_regime"),
                payload=decision,
                engine_version=str(decision.get("engine_version") or "9.0"),
                calculation_version=str(decision.get("calculation_version") or "9.0"),
                timestamp=decision.get("scored_at") or decision.get("timestamp") or decision.get("generated_at"),
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_ai_decision(self, report: dict[str, Any]) -> None:
        """Persist AI Decision history (Ch.11 §11.16)."""
        session = get_session()
        try:
            IntelligenceRepository(session).append_ai_decision(
                module="ai",
                symbol=str(report.get("symbol") or "BTCUSDT"),
                market_bias=report.get("market_bias"),
                narrative=report.get("primary_narrative") or report.get("narrative"),
                confidence=_f(report.get("confidence")),
                scenarios=report.get("scenarios") or report.get("alternative_scenarios"),
                reasoning=report.get("reasoning"),
                risk_level=report.get("risk_level"),
                analysis_fingerprint=report.get("analysis_fingerprint"),
                payload=report,
                engine_version=str(report.get("engine_version") or "7.0"),
                ai_version=str(report.get("ai_version") or "7.0"),
                timestamp=report.get("timestamp") or report.get("generated_at"),
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_report(self, report: dict[str, Any]) -> None:
        """Archive published report (Ch.11 §11.17)."""
        meta = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        report_id = str(meta.get("report_id") or report.get("report_id") or "")
        if not report_id:
            from uuid import uuid4

            report_id = str(uuid4())
        session = get_session()
        try:
            IntelligenceRepository(session).append_report(
                module="reporting",
                report_id=report_id,
                report_type=str(report.get("report_type") or meta.get("report_type") or "Daily Outlook"),
                content=report,
                symbol=str(meta.get("symbol") or report.get("symbol") or "BTCUSDT"),
                engine_version=meta.get("engine_version") or report.get("engine_version"),
                ai_version=meta.get("ai_version") or report.get("ai_version"),
                schema_version=meta.get("schema_version") or report.get("schema_version"),
                published=bool(report.get("published", meta.get("published", True))),
                generated_at=report.get("generated_at") or meta.get("generation_time"),
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_alert(self, alert: dict[str, Any]) -> None:
        """Persist alert notification (Ch.11 §11.18)."""
        session = get_session()
        try:
            IntelligenceRepository(session).append_alert(
                module="reporting",
                alert_type=str(alert.get("type") or alert.get("alert_type") or "system"),
                severity=str(alert.get("severity") or "info"),
                message=str(alert.get("message") or alert.get("title") or ""),
                symbol=alert.get("symbol"),
                delivered=bool(alert.get("delivered", False)),
                payload=alert,
                timestamp=alert.get("timestamp") or alert.get("generated_at"),
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_volatility_data(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            IntelligenceRepository(session).append_volatility(
                module="analysis",
                symbol=record.get("symbol"),
                historical_volatility=_f(record.get("historical_volatility")),
                implied_volatility=_f(record.get("implied_volatility")),
                atr=_f(record.get("atr")),
                bollinger_width=_f(record.get("bollinger_width")),
                volatility_state=record.get("volatility_state") or record.get("volatility"),
                timestamp=record.get("timestamp"),
                payload=record,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def append_structure_snapshot(self, record: dict[str, Any]) -> None:
        session = get_session()
        try:
            IntelligenceRepository(session).append_structure(
                module="analysis",
                symbol=str(record.get("symbol") or "BTCUSDT"),
                timeframe=str(record.get("timeframe") or "1h"),
                trend=record.get("trend"),
                higher_high=record.get("higher_high"),
                higher_low=record.get("higher_low"),
                lower_high=record.get("lower_high"),
                lower_low=record.get("lower_low"),
                bos=record.get("bos"),
                choch=record.get("choch"),
                hh=_f(record.get("hh")),
                hl=_f(record.get("hl")),
                lh=_f(record.get("lh")),
                ll=_f(record.get("ll")),
                timestamp=record.get("timestamp"),
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
