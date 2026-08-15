"""Persist advisor + Telegram settings from the dashboard."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.config import BASE_DIR, settings

logger = logging.getLogger(__name__)

CONFIG_PATH = BASE_DIR / "data" / "advisor_config.json"

PERSISTED_FIELDS = (
    "advisor_enabled",
    "advisor_api_key",
    "advisor_api_base",
    "advisor_model",
    "advisor_cache_minutes",
    "advisor_telegram_enabled",
    "advisor_telegram_proactive",
    "advisor_chat_history_limit",
    "telegram_bot_token",
    "telegram_chat_id",
)


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}...{value[-4:]}"


def load_raw() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to read advisor config")
        return {}


def save_raw(data: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def apply_from_disk() -> None:
    data = load_raw()
    for key in PERSISTED_FIELDS:
        if key in data and data[key] is not None:
            setattr(settings, key, data[key])


def reload_runtime_settings() -> None:
    """Reload dashboard-saved settings (API key, telegram, model)."""
    apply_from_disk()


def is_llm_configured() -> bool:
    reload_runtime_settings()
    return bool(settings.advisor_api_key)


def to_public_dict() -> dict[str, Any]:
    return {
        "advisor_enabled": settings.advisor_enabled,
        "advisor_api_key_set": bool(settings.advisor_api_key),
        "advisor_api_key_masked": mask_secret(settings.advisor_api_key),
        "advisor_api_base": settings.advisor_api_base,
        "advisor_model": settings.advisor_model,
        "advisor_cache_minutes": settings.advisor_cache_minutes,
        "advisor_telegram_enabled": settings.advisor_telegram_enabled,
        "advisor_telegram_proactive": settings.advisor_telegram_proactive,
        "advisor_chat_history_limit": settings.advisor_chat_history_limit,
        "telegram_bot_token_set": bool(settings.telegram_bot_token),
        "telegram_bot_token_masked": mask_secret(settings.telegram_bot_token),
        "telegram_chat_id": settings.telegram_chat_id,
        "configured": bool(settings.advisor_api_key),
        "telegram_configured": bool(settings.telegram_bot_token and settings.telegram_chat_id),
        "config_source": "dashboard" if CONFIG_PATH.exists() else "env",
    }


def update_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    current = load_raw()

    for key in PERSISTED_FIELDS:
        if key not in payload:
            continue
        value = payload[key]

        if key in ("advisor_api_key", "telegram_bot_token"):
            if not value or value == "__KEEP__":
                continue

        if key == "telegram_chat_id" and value is None:
            continue

        current[key] = value
        setattr(settings, key, value)

    save_raw(current)
    return to_public_dict()


def set_api_key(api_key: str, api_base: str | None = None, model: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"advisor_api_key": api_key.strip()}
    if api_base:
        payload["advisor_api_base"] = api_base.strip()
    if model:
        payload["advisor_model"] = model.strip()
    payload["advisor_enabled"] = True
    return update_from_request(payload)
