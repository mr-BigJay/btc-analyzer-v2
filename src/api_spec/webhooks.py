"""Webhook subscriptions and signed delivery (Ch.18 §18.18)."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from uuid import uuid4

from src.api_spec.contracts import WebhookSubscription, utc_now_iso
from src.config import settings
from src.logging_setup import get_logger
from src.storage.redis_cache import redis_cache

log = get_logger("api_spec.webhooks")

WEBHOOK_STORE_KEY = "api:webhooks"
SUPPORTED_EVENTS = [
    "Report Generated",
    "Alert Created",
    "Market Regime Changed",
    "Data Quality Warning",
    "System Recovery",
]


class WebhookRegistry:
    def list(self) -> list[dict[str, Any]]:
        raw = redis_cache.get(WEBHOOK_STORE_KEY)
        return list(raw) if isinstance(raw, list) else []

    def _save(self, rows: list[dict[str, Any]]) -> None:
        redis_cache.set(WEBHOOK_STORE_KEY, rows, ttl_sec=86400 * 30)

    def subscribe(self, *, url: str, events: list[str], secret: str = "") -> WebhookSubscription:
        allowed = [e for e in events if e in SUPPORTED_EVENTS]
        sub = WebhookSubscription(
            url=url,
            events=allowed or list(SUPPORTED_EVENTS),
            secret=secret or (settings.api_webhook_signing_secret or str(uuid4())),
        )
        rows = self.list()
        rows.append(sub.to_dict())
        self._save(rows)
        return sub

    def unsubscribe(self, subscription_id: str) -> bool:
        rows = self.list()
        nxt = [r for r in rows if r.get("subscription_id") != subscription_id]
        if len(nxt) == len(rows):
            return False
        self._save(nxt)
        return True

    def sign_payload(self, payload: dict[str, Any], secret: str) -> str:
        body = json.dumps(payload, sort_keys=True, default=str).encode()
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def deliver(
        self,
        event: str,
        data: dict[str, Any],
        *,
        dry_run: bool = True,
    ) -> list[dict[str, Any]]:
        """Signed HTTPS POST — dry_run records intent without network I/O by default."""
        results = []
        envelope = {
            "event": event,
            "timestamp": utc_now_iso(),
            "delivery_id": str(uuid4()),
            "data": data,
        }
        for sub in self.list():
            if not sub.get("active"):
                continue
            if event not in (sub.get("events") or []):
                continue
            secret = str(sub.get("secret") or "")
            signature = self.sign_payload(envelope, secret)
            record = {
                "subscription_id": sub.get("subscription_id"),
                "url": sub.get("url"),
                "event": event,
                "signature": signature,
                "status": "queued" if dry_run else "sent",
                "dry_run": dry_run,
            }
            if not dry_run:
                try:
                    import urllib.request

                    req = urllib.request.Request(
                        str(sub["url"]),
                        data=json.dumps(envelope).encode(),
                        headers={
                            "Content-Type": "application/json",
                            "X-BTC-Analyzer-Signature": signature,
                            "X-BTC-Analyzer-Event": event,
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                        record["status"] = "delivered" if 200 <= resp.status < 300 else "failed"
                        record["http_status"] = resp.status
                except Exception as exc:  # noqa: BLE001
                    record["status"] = "failed"
                    record["error"] = str(exc)
                    log.warning("webhook delivery failed: {}", exc)
            results.append(record)
        return results


webhook_registry = WebhookRegistry()
