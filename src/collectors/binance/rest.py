"""Binance REST endpoints — futures + spot public market data (Ch.3 §3.6)."""

from __future__ import annotations

from typing import Any

from src.collectors.common import TokenBucketLimiter
from src.collectors.http import RestClient
from src.collectors.binance.auth import BinanceAuth


class BinanceRestClient:
    FUTURES_BASE = "https://fapi.binance.com"
    SPOT_BASE = "https://api.binance.com"
    DATA_BASE = "https://fapi.binance.com"

    def __init__(self, auth: BinanceAuth | None = None) -> None:
        self.auth = auth or BinanceAuth()
        limiter = TokenBucketLimiter(rate_per_sec=8.0, capacity=20.0)
        headers = self.auth.public_headers()
        self.futures = RestClient("binance", self.FUTURES_BASE, limiter=limiter, headers=headers)
        self.spot = RestClient("binance_spot", self.SPOT_BASE, limiter=limiter, headers=headers)

    async def mark_premium(self, symbol: str) -> dict[str, Any]:
        return await self.futures.get("/fapi/v1/premiumIndex", params={"symbol": symbol}, critical=True)

    async def funding_history(self, symbol: str, limit: int = 20) -> list[dict[str, Any]]:
        data = await self.futures.get(
            "/fapi/v1/fundingRate", params={"symbol": symbol, "limit": limit}
        )
        return data if isinstance(data, list) else []

    async def open_interest(self, symbol: str) -> dict[str, Any]:
        return await self.futures.get("/fapi/v1/openInterest", params={"symbol": symbol}, critical=True)

    async def open_interest_hist(self, symbol: str, period: str = "5m", limit: int = 30) -> list:
        data = await self.futures.get(
            "/futures/data/openInterestHist",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
        return data if isinstance(data, list) else []

    async def long_short_ratio(self, symbol: str, period: str = "5m", limit: int = 30) -> list:
        data = await self.futures.get(
            "/futures/data/globalLongShortAccountRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
        return data if isinstance(data, list) else []

    async def ticker_price(self, symbol: str) -> dict[str, Any]:
        return await self.futures.get("/fapi/v1/ticker/price", params={"symbol": symbol}, critical=True)

    async def depth(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        return await self.futures.get("/fapi/v1/depth", params={"symbol": symbol, "limit": limit})

    async def klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> list:
        data = await self.futures.get(
            "/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        return data if isinstance(data, list) else []

    async def spot_ticker(self, symbol: str) -> dict[str, Any]:
        return await self.spot.get("/api/v3/ticker/24hr", params={"symbol": symbol})

    async def spot_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> list:
        data = await self.spot.get(
            "/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        return data if isinstance(data, list) else []
