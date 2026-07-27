"""HTTPS-only REST client with rate limiting and retry (Ch.3 §3.5, §3.16, §3.18)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.collectors.common import RetryHandler, TokenBucketLimiter, log_collector_event
import time

logger = logging.getLogger(__name__)


class RestClient:
    """Exchange-agnostic HTTPS REST client. API keys never logged."""

    def __init__(
        self,
        exchange: str,
        base_url: str,
        *,
        limiter: TokenBucketLimiter | None = None,
        retry: RetryHandler | None = None,
        timeout: float = 20.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        if not base_url.startswith("https://"):
            raise ValueError(f"{exchange} REST client requires HTTPS (Ch.3 §3.18)")
        self.exchange = exchange
        self.base_url = base_url.rstrip("/")
        self.limiter = limiter or TokenBucketLimiter()
        self.retry = retry or RetryHandler()
        self.timeout = timeout
        self.headers = headers or {"User-Agent": "btc-analyzer/3.0"}

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        critical: bool = False,
    ) -> Any:
        endpoint = path
        tokens = 0.5 if critical else 1.0

        async def _once() -> Any:
            await self.limiter.wait(tokens)
            url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
            started = time.monotonic()
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url, params=params)
            elapsed_ms = (time.monotonic() - started) * 1000
            if response.status_code == 429:
                self.limiter.pause(30.0)
                log_collector_event(
                    self.exchange, endpoint, elapsed_ms, "RATE_LIMIT", error_code="429"
                )
                raise RuntimeError(f"{self.exchange} rate limited on {endpoint}")
            if response.status_code >= 400:
                log_collector_event(
                    self.exchange,
                    endpoint,
                    elapsed_ms,
                    "HTTP_ERROR",
                    error_code=str(response.status_code),
                )
                raise RuntimeError(
                    f"{self.exchange} HTTP {response.status_code} on {endpoint}: {response.text[:200]}"
                )
            return response.json()

        value, retries, error = await self.retry.run(self.exchange, endpoint, _once)
        if value is None:
            raise RuntimeError(error or f"{self.exchange} GET {endpoint} failed after retries")
        return value

    async def get_text(self, path: str, *, params: dict[str, Any] | None = None) -> str:
        async def _once() -> str:
            await self.limiter.wait()
            url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url, params=params)
            if response.status_code >= 400:
                raise RuntimeError(f"{self.exchange} HTTP {response.status_code} on {path}")
            return response.text

        value, _, error = await self.retry.run(self.exchange, path, _once)
        if value is None:
            raise RuntimeError(error or f"{self.exchange} GET text {path} failed")
        return value
