"""Binance authentication — public market data needs no keys (Ch.3 §3.18).

Optional API keys via environment / settings only — never hardcoded.
"""

from __future__ import annotations

from src.config import settings


class BinanceAuth:
    """Read-only credentials from environment — never hardcoded."""

    def __init__(self) -> None:
        self.api_key = settings.binance_api_key
        self.api_secret = settings.binance_api_secret

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def public_headers(self) -> dict[str, str]:
        headers = {"User-Agent": "btc-analyzer/3.0"}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        return headers
