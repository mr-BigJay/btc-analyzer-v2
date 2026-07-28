"""MarketContext — read-only snapshot for analysis layers (Ch.6).

Built from Central Repository / Redis only — never calls collectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.cache.keys import CacheKeys
from src.config import settings
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository


@dataclass
class MarketContext:
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    mark_price: float | None = None
    index_price: float | None = None
    volume: float | None = None
    # Futures
    funding_rate: float | None = None
    open_interest: float | None = None
    open_interest_value: float | None = None
    long_short_ratio: float | None = None
    liquidations: dict[str, Any] = field(default_factory=dict)
    order_book: dict[str, Any] = field(default_factory=dict)
    # Options
    put_call_ratio: float | None = None
    max_pain: float | None = None
    iv_rank: float | None = None
    iv_percentile: float | None = None
    gamma_exposure: float | None = None
    dealer_gamma: float | None = None
    dealer_delta: float | None = None
    volatility_skew: float | None = None
    option_chain: list[dict] = field(default_factory=list)
    implied_volatility_mean: float | None = None
    # Candles / OHLCV
    ohlcv: list[dict] = field(default_factory=list)
    # Spot extras
    spot_price: float | None = None
    spot_volume: float | None = None
    # Meta
    source_flags: dict[str, bool] = field(default_factory=dict)
    # Ch.13 engineered features (optional hydration)
    features: dict[str, Any] = field(default_factory=dict)
    feature_data_quality: float | None = None

    @property
    def closes(self) -> list[float]:
        out = []
        for row in self.ohlcv:
            c = row.get("close")
            if c is not None:
                try:
                    out.append(float(c))
                except (TypeError, ValueError):
                    pass
        return out

    @property
    def highs(self) -> list[float]:
        return [_f(r.get("high")) for r in self.ohlcv if _f(r.get("high")) is not None]  # type: ignore[misc]

    @property
    def lows(self) -> list[float]:
        return [_f(r.get("low")) for r in self.ohlcv if _f(r.get("low")) is not None]  # type: ignore[misc]

    @property
    def volumes(self) -> list[float]:
        return [_f(r.get("volume")) or 0.0 for r in self.ohlcv]


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_market_context(
    repository: CentralRepository | None = None,
    *,
    symbol: str | None = None,
    timeframe: str = "1h",
) -> MarketContext:
    repo = repository or CentralRepository()
    symbol = symbol or settings.binance_symbol
    ctx = MarketContext(symbol=symbol, timeframe=timeframe)

    # Hot cache first
    ctx.mark_price = _f(redis_cache.get(CacheKeys.LATEST_MARK_PRICE))
    ctx.funding_rate = _f(redis_cache.get(CacheKeys.LATEST_FUNDING_RATE))
    ctx.open_interest = _f(redis_cache.get(CacheKeys.CURRENT_OPEN_INTEREST))
    ob = redis_cache.get(CacheKeys.CURRENT_ORDER_BOOK)
    if isinstance(ob, dict):
        ctx.order_book = ob

    binance = repo.load_snapshot("Binance") or {}
    bdata = binance.get("data") if isinstance(binance.get("data"), dict) else {}
    if bdata:
        ctx.source_flags["binance"] = True
        ctx.mark_price = ctx.mark_price or _f(bdata.get("mark_price"))
        ctx.index_price = _f(bdata.get("index_price"))
        ctx.funding_rate = ctx.funding_rate if ctx.funding_rate is not None else _f(bdata.get("funding_rate"))
        ctx.open_interest = ctx.open_interest if ctx.open_interest is not None else _f(bdata.get("open_interest"))
        ctx.open_interest_value = _f(bdata.get("open_interest_value"))
        ctx.long_short_ratio = _f(bdata.get("long_short_ratio"))
        ctx.volume = _f(bdata.get("volume"))
        if isinstance(bdata.get("order_book"), dict):
            ctx.order_book = bdata["order_book"]
        if isinstance(bdata.get("liquidations"), dict):
            ctx.liquidations = bdata["liquidations"]

    deribit = repo.load_snapshot("Deribit") or {}
    ddata = deribit.get("data") if isinstance(deribit.get("data"), dict) else {}
    if ddata:
        ctx.source_flags["deribit"] = True
        ctx.put_call_ratio = _f(ddata.get("put_call_ratio"))
        ctx.max_pain = _f(ddata.get("max_pain"))
        ctx.iv_rank = _f(ddata.get("iv_rank"))
        ctx.iv_percentile = _f(ddata.get("iv_percentile"))
        ctx.gamma_exposure = _f(ddata.get("gamma_exposure"))
        ctx.dealer_gamma = _f(ddata.get("dealer_gamma"))
        ctx.dealer_delta = _f(ddata.get("dealer_delta"))
        ctx.volatility_skew = _f(ddata.get("volatility_skew"))
        ctx.implied_volatility_mean = _f(ddata.get("implied_volatility_mean"))
        if isinstance(ddata.get("option_chain"), list):
            ctx.option_chain = ddata["option_chain"]

    # Technical cache / OHLCV
    tech = redis_cache.get("technical_cache_1h")
    if not isinstance(tech, dict):
        # file snapshot fallback via memory key used by collection engine
        pass
    if isinstance(tech, dict) and isinstance(tech.get("ohlcv"), list):
        ctx.ohlcv = tech["ohlcv"]
        ctx.source_flags["ohlcv"] = True
        spot = tech.get("spot") if isinstance(tech.get("spot"), dict) else {}
        ctx.spot_price = _f(spot.get("price"))
        ctx.spot_volume = _f(spot.get("volume"))

    # Also try loading from DB last candles if ohlcv empty
    if not ctx.ohlcv:
        ctx.ohlcv = _load_candles_from_db(repo, symbol, timeframe)

    feat = redis_cache.get("latest_feature_set")
    if isinstance(feat, dict):
        ctx.features = feat.get("outputs") or {}
        ctx.feature_data_quality = feat.get("data_quality")
        ctx.source_flags["features"] = True

    return ctx


def _load_candles_from_db(repo: CentralRepository, symbol: str, timeframe: str) -> list[dict]:
    try:
        from src.db.models import MarketCandle, Symbol
        from src.db.session import get_session

        session = get_session()
        try:
            sym = session.query(Symbol).filter_by(symbol=symbol).one_or_none()
            if not sym:
                return []
            rows = (
                session.query(MarketCandle)
                .filter_by(symbol_id=sym.id, timeframe=timeframe)
                .order_by(MarketCandle.timestamp.desc())
                .limit(200)
                .all()
            )
            rows = list(reversed(rows))
            return [
                {
                    "open_time": r.timestamp.isoformat() if r.timestamp else None,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                }
                for r in rows
            ]
        finally:
            session.close()
    except Exception:  # noqa: BLE001
        return []
