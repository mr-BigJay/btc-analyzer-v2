import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from src.collector.base import BaseCollector
from src.config import settings

logger = logging.getLogger(__name__)


class ExchangeProvider(ABC):
    name: str = "base"

    @abstractmethod
    def probe(self) -> bool:
        """Return True if this exchange is reachable."""

    @abstractmethod
    def fetch_klines(self, timeframe: str, limit: int) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def fetch_ticker(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def fetch_funding_rates(self, limit: int) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def fetch_open_interest_history(self, limit: int) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def fetch_long_short_ratios(self, limit: int) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def fetch_taker_volumes(self, limit: int) -> list[dict[str, Any]]:
        ...


class BinanceProvider(ExchangeProvider, BaseCollector):
    name = "binance"

    TF_MAP = {"4h": "4h", "1d": "1d", "1w": "1w"}

    def probe(self) -> bool:
        try:
            self._get(
                f"{settings.binance_spot_base}/api/v3/ping",
            )
            return True
        except Exception:
            return False

    def fetch_klines(self, timeframe: str, limit: int) -> list[dict[str, Any]]:
        data = self._get(
            f"{settings.binance_spot_base}/api/v3/klines",
            {
                "symbol": settings.symbol,
                "interval": self.TF_MAP[timeframe],
                "limit": limit,
            },
        )
        rows = []
        for c in data:
            rows.append(
                {
                    "open_time": self.ms_to_datetime(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                    "quote_volume": float(c[7]),
                    "trades": int(c[8]),
                }
            )
        return rows

    def fetch_ticker(self) -> dict[str, Any]:
        data = self._get(
            f"{settings.binance_spot_base}/api/v3/ticker/24hr",
            {"symbol": settings.symbol},
        )
        return {
            "price": float(data["lastPrice"]),
            "price_change_24h": float(data["priceChange"]),
            "price_change_pct_24h": float(data["priceChangePercent"]),
            "high_24h": float(data["highPrice"]),
            "low_24h": float(data["lowPrice"]),
            "volume_24h": float(data["volume"]),
            "quote_volume_24h": float(data["quoteVolume"]),
        }

    def fetch_funding_rates(self, limit: int) -> list[dict[str, Any]]:
        data = self._get(
            f"{settings.binance_futures_base}/fapi/v1/fundingRate",
            {"symbol": settings.futures_symbol, "limit": limit},
        )
        return [
            {
                "funding_rate": float(item["fundingRate"]),
                "mark_price": float(item.get("markPrice", 0)) or None,
                "funding_time": self.ms_to_datetime(item["fundingTime"]),
            }
            for item in data
        ]

    def fetch_open_interest_history(self, limit: int) -> list[dict[str, Any]]:
        data = self._get(
            f"{settings.binance_futures_base}/futures/data/openInterestHist",
            {"symbol": settings.futures_symbol, "period": "1h", "limit": limit},
        )
        return [
            {
                "open_interest": float(item["sumOpenInterest"]),
                "open_interest_value": float(item["sumOpenInterestValue"]),
                "timestamp": self.ms_to_datetime(item["timestamp"]),
            }
            for item in data
        ]

    def fetch_long_short_ratios(self, limit: int) -> list[dict[str, Any]]:
        results = []
        ratio_types = [
            ("global", "globalLongShortAccountRatio"),
            ("top_trader", "topLongShortAccountRatio"),
            ("top_position", "topLongShortPositionRatio"),
        ]
        for ratio_name, endpoint in ratio_types:
            data = self._get(
                f"{settings.binance_futures_base}/futures/data/{endpoint}",
                {"symbol": settings.futures_symbol, "period": "1h", "limit": limit},
            )
            for item in data:
                results.append(
                    {
                        "ratio_type": ratio_name,
                        "long_account": float(item["longAccount"]),
                        "short_account": float(item["shortAccount"]),
                        "long_short_ratio": float(item["longShortRatio"]),
                        "timestamp": self.ms_to_datetime(item["timestamp"]),
                    }
                )
        return results

    def fetch_taker_volumes(self, limit: int) -> list[dict[str, Any]]:
        data = self._get(
            f"{settings.binance_futures_base}/futures/data/takerlongshortRatio",
            {"symbol": settings.futures_symbol, "period": "1h", "limit": limit},
        )
        rows = []
        for item in data:
            buy_vol = float(item["buyVol"])
            sell_vol = float(item["sellVol"])
            rows.append(
                {
                    "buy_volume": buy_vol,
                    "sell_volume": sell_vol,
                    "buy_sell_ratio": buy_vol / sell_vol if sell_vol else 0.0,
                    "timestamp": self.ms_to_datetime(item["timestamp"]),
                }
            )
        return rows


class OKXProvider(ExchangeProvider, BaseCollector):
    name = "okx"

    TF_MAP = {"4h": "4H", "1d": "1D", "1w": "1W"}
    BASE = "https://www.okx.com/api/v5"

    def probe(self) -> bool:
        try:
            data = self._get(f"{self.BASE}/public/time")
            return data.get("code") == "0"
        except Exception:
            return False

    def _okx_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        data = self._get(f"{self.BASE}{path}", params)
        if data.get("code") != "0":
            raise RuntimeError(f"OKX API error: {data.get('msg', data)}")
        return data.get("data", [])

    def fetch_klines(self, timeframe: str, limit: int) -> list[dict[str, Any]]:
        data = self._okx_get(
            "/market/candles",
            {"instId": settings.okx_inst_id, "bar": self.TF_MAP[timeframe], "limit": str(limit)},
        )
        rows = []
        for c in reversed(data):
            rows.append(
                {
                    "open_time": self.ms_to_datetime(int(c[0])),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                    "quote_volume": float(c[6]) if len(c) > 6 else 0.0,
                    "trades": 0,
                }
            )
        return rows

    def fetch_ticker(self) -> dict[str, Any]:
        data = self._okx_get("/market/ticker", {"instId": settings.okx_inst_id})
        if not data:
            raise RuntimeError("OKX ticker empty")
        t = data[0]
        open_24h = float(t["open24h"])
        last = float(t["last"])
        change = last - open_24h
        change_pct = (change / open_24h * 100) if open_24h else 0.0
        return {
            "price": last,
            "price_change_24h": change,
            "price_change_pct_24h": change_pct,
            "high_24h": float(t["high24h"]),
            "low_24h": float(t["low24h"]),
            "volume_24h": float(t["vol24h"]),
            "quote_volume_24h": float(t["volCcy24h"]),
        }

    def fetch_funding_rates(self, limit: int) -> list[dict[str, Any]]:
        data = self._okx_get(
            "/public/funding-rate-history",
            {"instId": settings.okx_swap_id, "limit": str(limit)},
        )
        return [
            {
                "funding_rate": float(item["fundingRate"]),
                "mark_price": None,
                "funding_time": self.ms_to_datetime(int(item["fundingTime"])),
            }
            for item in data
        ]

    def fetch_open_interest_history(self, limit: int) -> list[dict[str, Any]]:
        data = self._okx_get(
            "/rubik/stat/contracts/open-interest-volume",
            {"ccy": "BTC", "period": "1H"},
        )
        rows = []
        for item in data[-limit:]:
            ts, oi_value, _vol = item
            rows.append(
                {
                    "open_interest": float(oi_value),
                    "open_interest_value": float(oi_value),
                    "timestamp": self.ms_to_datetime(int(ts)),
                }
            )
        return rows

    def fetch_long_short_ratios(self, limit: int) -> list[dict[str, Any]]:
        data = self._okx_get(
            "/rubik/stat/contracts/long-short-account-ratio",
            {"ccy": "BTC", "period": "1H"},
        )
        rows = []
        for item in data[-limit:]:
            ts, ratio = item
            ratio_f = float(ratio)
            long_pct = ratio_f / (1 + ratio_f) if ratio_f else 0.5
            short_pct = 1 - long_pct
            rows.append(
                {
                    "ratio_type": "global",
                    "long_account": long_pct,
                    "short_account": short_pct,
                    "long_short_ratio": ratio_f,
                    "timestamp": self.ms_to_datetime(int(ts)),
                }
            )
        return rows

    def fetch_taker_volumes(self, limit: int) -> list[dict[str, Any]]:
        data = self._okx_get(
            "/rubik/stat/taker-volume-contract",
            {"instId": settings.okx_swap_id, "period": "1H"},
        )
        rows = []
        for item in data[-limit:]:
            ts, sell_vol, buy_vol = item
            buy_f = float(buy_vol)
            sell_f = float(sell_vol)
            rows.append(
                {
                    "buy_volume": buy_f,
                    "sell_volume": sell_f,
                    "buy_sell_ratio": buy_f / sell_f if sell_f else 0.0,
                    "timestamp": self.ms_to_datetime(int(ts)),
                }
            )
        return rows


_providers: list[ExchangeProvider] = [BinanceProvider(), OKXProvider()]
_active_provider: ExchangeProvider | None = None


def get_exchange_provider(force: str | None = None) -> ExchangeProvider:
    global _active_provider

    if force and force != "auto":
        for p in _providers:
            if p.name == force:
                if not p.probe():
                    raise RuntimeError(f"Exchange '{force}' is not reachable")
                _active_provider = p
                return p
        raise ValueError(f"Unknown exchange: {force}")

    if _active_provider is not None:
        return _active_provider

    preferred = settings.exchange_provider
    if preferred != "auto":
        return get_exchange_provider(preferred)

    for p in _providers:
        if p.probe():
            logger.info("Using exchange provider: %s", p.name)
            _active_provider = p
            return p

    raise RuntimeError("No exchange provider is reachable (tried: binance, okx)")
