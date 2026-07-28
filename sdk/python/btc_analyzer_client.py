"""Thin Python SDK wrapper around BTC Analyzer public API (Ch.18 §18.22).

Does not duplicate business logic — only HTTP helpers for published contracts.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class BtcAnalyzerClient:
    """Minimal REST client for `/api/v1/`."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        api_key: str | None = None,
        access_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.access_token = access_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        if self.access_token:
            h["Authorization"] = f"Bearer {self.access_token}"
        return h

    def request(self, method: str, path: str, *, params: dict[str, Any] | None = None, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode(errors="replace")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"status": "error", "error": {"code": "HTTP_ERROR", "message": raw}}

    def health(self) -> dict[str, Any]:
        return self.request("GET", "/api/v1/system/health")

    def assets(self) -> dict[str, Any]:
        return self.request("GET", "/api/v1/assets")

    def market(self, symbol: str = "BTCUSDT") -> dict[str, Any]:
        return self.request("GET", f"/api/v1/market/{symbol}")

    def alerts(self, **params: Any) -> dict[str, Any]:
        return self.request("GET", "/api/v1/alerts", params=params)

    def daily_report(self, symbol: str = "BTCUSDT") -> dict[str, Any]:
        return self.request("GET", f"/api/v1/reports/daily/{symbol}")
