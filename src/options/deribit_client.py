"""Deribit API client — public + authenticated private endpoints."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class DeribitClient:
    def __init__(self) -> None:
        self.base = settings.deribit_base_url
        self._token: str | None = None
        self._token_expires: float = 0.0
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    def _rpc(self, method: str, params: dict | None = None, auth: bool = False) -> Any:
        headers = {}
        if auth:
            headers["Authorization"] = f"Bearer {self._ensure_token()}"

        payload = {"jsonrpc": "2.0", "id": int(time.time()), "method": method, "params": params or {}}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.base, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"Deribit API error: {data['error']}")
            return data.get("result")

    def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        if not settings.deribit_configured:
            raise RuntimeError("Deribit API credentials not configured")

        result = self._rpc(
            "public/auth",
            {
                "grant_type": "client_credentials",
                "client_id": settings.deribit_client_id,
                "client_secret": settings.deribit_client_secret,
            },
        )
        self._token = result["access_token"]
        self._token_expires = time.time() + result.get("expires_in", 3600)
        logger.info("Deribit authenticated")
        return self._token

    def get_index_price(self) -> float:
        result = self._rpc("public/get_index_price", {"index_name": "btc_usd"})
        return float(result["index_price"])

    def get_recent_trades(self, hours: int = 24, count: int = 500) -> list[dict]:
        start = int((time.time() - hours * 3600) * 1000)
        result = self._rpc(
            "public/get_last_trades_by_currency_and_time",
            {
                "currency": settings.deribit_currency,
                "kind": "option",
                "start_timestamp": start,
                "count": count,
                "include_old": True,
            },
        )
        return result.get("trades", [])

    def get_ticker(self, instrument_name: str) -> dict:
        return self._rpc("public/ticker", {"instrument_name": instrument_name})

    def get_positions(self) -> list[dict]:
        result = self._rpc(
            "private/get_positions",
            {"currency": settings.deribit_currency, "kind": "option"},
            auth=True,
        )
        return result if isinstance(result, list) else []

    def get_open_interests_summary(self) -> list[dict]:
        result = self._rpc(
            "public/get_book_summary_by_currency",
            {"currency": settings.deribit_currency, "kind": "option"},
        )
        return result if isinstance(result, list) else []
