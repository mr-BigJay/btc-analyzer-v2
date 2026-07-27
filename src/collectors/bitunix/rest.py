"""Bitunix REST — execution-validation market snapshot (Ch.3 §3.9).

Never used as primary analytical source.
"""

from __future__ import annotations

from typing import Any

from src.collectors.common import TokenBucketLimiter
from src.collectors.http import RestClient
from src.collectors.bitunix.auth import BitunixAuth
from src.config import settings


class BitunixRestClient:
    def __init__(self, auth: BitunixAuth | None = None) -> None:
        self.auth = auth or BitunixAuth()
        self.client = RestClient(
            "bitunix",
            settings.bitunix_base_url,
            limiter=TokenBucketLimiter(rate_per_sec=3.0, capacity=6.0),
            headers=self.auth.public_headers(),
        )

    async def ticker(self, symbol: str) -> dict[str, Any]:
        return await self.client.get(
            "/api/v1/market/ticker",
            params={"symbol": symbol},
            critical=True,
        )

    async def depth(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        return await self.client.get(
            "/api/v1/market/depth",
            params={"symbol": symbol, "limit": limit},
        )

    async def funding(self, symbol: str) -> dict[str, Any]:
        return await self.client.get(
            "/api/v1/market/funding_rate",
            params={"symbol": symbol},
        )
