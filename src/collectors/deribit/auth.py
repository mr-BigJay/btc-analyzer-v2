"""Deribit authentication — public options data; secrets via env only (Ch.3 §3.18)."""

from __future__ import annotations

from src.config import settings


class DeribitAuth:
    def __init__(self) -> None:
        self.client_id = settings.deribit_client_id
        self.client_secret = settings.deribit_client_secret

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def public_headers(self) -> dict[str, str]:
        return {"User-Agent": "btc-analyzer/3.0"}
