"""CoinEx auth — public narrative endpoints; secrets via env only."""

from __future__ import annotations

import os


class CoinExAuth:
    def __init__(self) -> None:
        self.api_key = os.getenv("COINEX_API_KEY", "")
        self.api_secret = os.getenv("COINEX_API_SECRET", "")

    def public_headers(self) -> dict[str, str]:
        return {"User-Agent": "btc-analyzer/3.0"}
