"""Notifications (Telegram and future channels) — Ch.10 delivery."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from src.config import settings
from src.logging_setup import get_logger

log = get_logger("notifier")


def send_telegram(text: str, *, parse_mode: str | None = None) -> bool:
    """Deliver a concise message to the configured Telegram chat."""
    token = (settings.telegram_bot_token or "").strip()
    chat_id = (settings.telegram_chat_id or "").strip()
    if not token or not chat_id:
        log.debug("Telegram not configured — skip send")
        return False
    if not text:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text[:4000]}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
            ok = '"ok":true' in body.replace(" ", "").lower() or '"ok": true' in body
            log.info("telegram send ok={}", ok)
            return ok
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        log.warning("telegram send failed: {}", exc)
        return False
