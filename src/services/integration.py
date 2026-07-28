"""Integration service facade (Ch.18)."""

from __future__ import annotations

from typing import Any

from src.api_spec.auth import issue_jwt, parse_api_keys, verify_jwt
from src.api_spec.catalog import api_catalog
from src.api_spec.contracts import ApiRole
from src.api_spec.market_contract import build_market_intelligence_response
from src.api_spec.observability import api_metrics
from src.api_spec.validation import supported_symbols, validate_symbol
from src.api_spec.webhooks import SUPPORTED_EVENTS, webhook_registry
from src.config import settings


class IntegrationService:
    def status(self) -> dict[str, Any]:
        return api_catalog()

    def metrics(self) -> dict[str, Any]:
        return api_metrics.snapshot()

    def list_assets(self) -> dict[str, Any]:
        symbols = supported_symbols()
        return {
            "assets": [
                {
                    "symbol": s,
                    "base": s.replace("USDT", "").replace("USD", "") if s.endswith(("USDT", "USD")) else s,
                    "quote": "USDT" if s.endswith("USDT") else "USD",
                    "enabled": True,
                }
                for s in symbols
            ],
            "default": settings.default_symbol or settings.binance_symbol,
            "count": len(symbols),
        }

    def asset_metadata(self, symbol: str) -> dict[str, Any] | None:
        ok, _ = validate_symbol(symbol)
        if not ok:
            return None
        sym = symbol.upper()
        return {
            "symbol": sym,
            "base": sym.replace("USDT", "").replace("USD", ""),
            "quote": "USDT" if sym.endswith("USDT") else "USD",
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"],
            "streams": ["/ws/v1/market/" + sym],
            "enabled": True,
        }

    def market_intelligence(self, symbol: str) -> dict[str, Any] | None:
        ok, _ = validate_symbol(symbol)
        if not ok:
            return None
        return build_market_intelligence_response(symbol=symbol.upper()).to_dict()

    def issue_token(self, *, subject: str, role: str | None = None, api_key: str | None = None) -> dict[str, Any]:
        # If api_key provided, map role from configured keys
        resolved_role = role or ApiRole.ANALYST.value
        if api_key:
            keys = parse_api_keys()
            if api_key not in keys:
                raise PermissionError("Invalid API key")
            resolved_role = keys[api_key]
            subject = subject or f"key:{api_key[:6]}"
        access = issue_jwt(subject=subject, role=resolved_role)
        refresh = issue_jwt(subject=subject, role=resolved_role, ttl_sec=int(settings.api_jwt_ttl_sec) * 24)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "Bearer",
            "expires_in": int(settings.api_jwt_ttl_sec),
            "role": resolved_role,
        }

    def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        payload = verify_jwt(refresh_token)
        if not payload:
            raise PermissionError("Invalid refresh token")
        return self.issue_token(subject=str(payload.get("sub") or "user"), role=str(payload.get("role") or ApiRole.VIEWER.value))

    def register_webhook(self, *, url: str, events: list[str] | None = None, secret: str = "") -> dict[str, Any]:
        sub = webhook_registry.subscribe(url=url, events=events or list(SUPPORTED_EVENTS), secret=secret)
        return sub.to_dict()

    def list_webhooks(self) -> list[dict[str, Any]]:
        return webhook_registry.list()

    def delete_webhook(self, subscription_id: str) -> bool:
        return webhook_registry.unsubscribe(subscription_id)

    def dispatch_webhook(self, event: str, data: dict[str, Any], *, dry_run: bool = True) -> list[dict[str, Any]]:
        return webhook_registry.deliver(event, data, dry_run=dry_run)
