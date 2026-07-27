"""Bitunix auth — credentials from environment only (Ch.3 §3.18)."""

from __future__ import annotations

from src.config import settings


class BitunixAuth:
    def __init__(self) -> None:
        self.api_key = settings.bitunix_api_key
        self.api_secret = settings.bitunix_api_secret

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def public_headers(self) -> dict[str, str]:
        headers = {"User-Agent": "btc-analyzer/3.0"}
        if self.api_key:
            headers["api-key"] = self.api_key
        return headers
