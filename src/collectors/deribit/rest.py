"""Deribit REST — public options market intelligence (Ch.3 §3.7)."""

from __future__ import annotations

from typing import Any

from src.collectors.common import TokenBucketLimiter
from src.collectors.http import RestClient
from src.collectors.deribit.auth import DeribitAuth
from src.config import settings


class DeribitRestClient:
    def __init__(self, auth: DeribitAuth | None = None) -> None:
        self.auth = auth or DeribitAuth()
        self.client = RestClient(
            "deribit",
            settings.deribit_base_url,
            limiter=TokenBucketLimiter(rate_per_sec=5.0, capacity=10.0),
            headers=self.auth.public_headers(),
        )

    async def get_instruments(self, currency: str = "BTC", kind: str = "option") -> list[dict]:
        data = await self.client.get(
            "/public/get_instruments",
            params={"currency": currency, "kind": kind, "expired": "false"},
            critical=True,
        )
        return data.get("result", data) if isinstance(data, dict) else []

    async def get_book_summary(self, currency: str = "BTC") -> list[dict]:
        data = await self.client.get(
            "/public/get_book_summary_by_currency",
            params={"currency": currency, "kind": "option"},
            critical=True,
        )
        return data.get("result", data) if isinstance(data, dict) else []

    async def get_index_price(self, currency: str = "BTC") -> float | None:
        data = await self.client.get(
            "/public/get_index_price",
            params={"index_name": f"{currency.lower()}_usd"},
            critical=True,
        )
        result = data.get("result", {}) if isinstance(data, dict) else {}
        try:
            return float(result.get("index_price"))
        except (TypeError, ValueError):
            return None

    async def ticker(self, instrument_name: str) -> dict[str, Any]:
        data = await self.client.get(
            "/public/ticker",
            params={"instrument_name": instrument_name},
        )
        return data.get("result", data) if isinstance(data, dict) else {}
