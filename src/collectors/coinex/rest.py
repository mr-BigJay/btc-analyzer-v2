"""CoinEx REST — AI Research tab on futures page (Ch.3 §3.8).

Source UI: https://www.coinex.com/en/futures/btc-usdt (tab: AI Research)
API:       GET https://www.coinex.com/res/ai-analysis/{coin}
"""

from __future__ import annotations

from typing import Any

from src.collectors.common import TokenBucketLimiter
from src.collectors.http import RestClient
from src.collectors.coinex.auth import CoinExAuth
from src.config import settings


class CoinExRestClient:
    """Fetches CoinEx AI Research JSON for a coin (default: btc)."""

    def __init__(self, auth: CoinExAuth | None = None) -> None:
        self.auth = auth or CoinExAuth()
        base = settings.coinex_base_url.rstrip("/")
        headers = {
            **self.auth.public_headers(),
            "Accept": "application/json, text/plain, */*",
            "Origin": base,
            "Referer": settings.coinex_futures_page_url,
        }
        self.client = RestClient(
            "coinex",
            base,
            limiter=TokenBucketLimiter(rate_per_sec=2.0, capacity=5.0),
            headers=headers,
        )
        self.coin = settings.coinex_ai_coin.lower()

    @property
    def analysis_path(self) -> str:
        return f"/res/ai-analysis/{self.coin}"

    async def fetch_ai_research(self) -> dict[str, Any]:
        """Return the raw API envelope `{code, data, message}`."""
        payload = await self.client.get(self.analysis_path, critical=True)
        if not isinstance(payload, dict):
            raise RuntimeError("CoinEx AI Research returned non-object payload")
        if payload.get("code") not in (0, "0", None):
            raise RuntimeError(
                f"CoinEx AI Research error code={payload.get('code')} msg={payload.get('message')}"
            )
        data = payload.get("data")
        if not isinstance(data, dict) or not data:
            raise RuntimeError("CoinEx AI Research empty data")
        return payload

    async def fetch_ai_summary(self) -> dict[str, Any]:
        return await self.client.get(f"/res/ai-analysis/{self.coin}/summary")
