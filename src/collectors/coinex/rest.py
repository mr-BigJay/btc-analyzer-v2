"""CoinEx REST — daily narrative / market analysis fetch (Ch.3 §3.8)."""

from __future__ import annotations

from src.collectors.common import TokenBucketLimiter
from src.collectors.http import RestClient
from src.collectors.coinex.auth import CoinExAuth
from src.config import settings


class CoinExRestClient:
    """Fetches narrative content from configured CoinEx analysis URL."""

    def __init__(self, auth: CoinExAuth | None = None) -> None:
        self.auth = auth or CoinExAuth()
        base = settings.coinex_base_url.rstrip("/")
        self.client = RestClient(
            "coinex",
            base,
            limiter=TokenBucketLimiter(rate_per_sec=2.0, capacity=5.0),
            headers=self.auth.public_headers(),
        )
        self.analysis_path = settings.coinex_analysis_path

    async def fetch_analysis_raw(self) -> str:
        return await self.client.get_text(self.analysis_path)

    async def fetch_analysis_json(self) -> dict:
        return await self.client.get(self.analysis_path)
