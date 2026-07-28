"""Admin console contracts — post-install GUI configuration (ops panel)."""

from __future__ import annotations

from typing import Any

ADMIN_SCHEMA_VERSION = "1.0"

# Keys editable from the Persian admin UI (mapped to Settings attributes)
EDITABLE_FIELDS: dict[str, dict[str, Any]] = {
    "timezone": {"attr": "timezone", "type": "str", "label": "منطقه زمانی", "group": "general"},
    "log_level": {"attr": "log_level", "type": "str", "label": "سطح لاگ", "group": "general"},
    "default_symbol": {"attr": "default_symbol", "type": "str", "label": "نماد پیش‌فرض", "group": "general"},
    "supported_assets": {"attr": "supported_assets", "type": "str", "label": "دارایی‌های پشتیبانی‌شده", "group": "general"},
    "domain": {"attr": None, "type": "str", "label": "دامنه عمومی", "group": "site", "env": "DOMAIN"},
    "certbot_email": {"attr": None, "type": "str", "label": "ایمیل Certbot", "group": "site", "env": "CERTBOT_EMAIL"},
    "api_auth_enabled": {"attr": "api_auth_enabled", "type": "bool", "label": "فعال‌سازی احراز هویت API", "group": "api"},
    "api_keys": {"attr": "api_keys", "type": "secret", "label": "کلیدهای API (key:Role,...)", "group": "api"},
    "api_jwt_secret": {"attr": "api_jwt_secret", "type": "secret", "label": "رمز JWT", "group": "api"},
    "api_rate_limit_per_minute": {"attr": "api_rate_limit_per_minute", "type": "int", "label": "سقف نرخ درخواست/دقیقه", "group": "api"},
    "telegram_bot_token": {"attr": "telegram_bot_token", "type": "secret", "label": "توکن ربات تلگرام", "group": "telegram"},
    "telegram_chat_id": {"attr": "telegram_chat_id", "type": "str", "label": "شناسه چت تلگرام", "group": "telegram"},
    "binance_futures_enabled": {"attr": "binance_futures_enabled", "type": "bool", "label": "Binance فعال", "group": "exchange"},
    "binance_api_key": {"attr": "binance_api_key", "type": "secret", "label": "Binance API Key", "group": "exchange"},
    "binance_api_secret": {"attr": "binance_api_secret", "type": "secret", "label": "Binance API Secret", "group": "exchange"},
    "deribit_enabled": {"attr": "deribit_enabled", "type": "bool", "label": "Deribit فعال", "group": "exchange"},
    "deribit_client_id": {"attr": "deribit_client_id", "type": "secret", "label": "Deribit Client ID", "group": "exchange"},
    "deribit_client_secret": {"attr": "deribit_client_secret", "type": "secret", "label": "Deribit Client Secret", "group": "exchange"},
    "bitunix_enabled": {"attr": "bitunix_enabled", "type": "bool", "label": "Bitunix فعال", "group": "exchange"},
    "bitunix_api_key": {"attr": "bitunix_api_key", "type": "secret", "label": "Bitunix API Key", "group": "exchange"},
    "bitunix_api_secret": {"attr": "bitunix_api_secret", "type": "secret", "label": "Bitunix API Secret", "group": "exchange"},
    "coinex_enabled": {"attr": "coinex_enabled", "type": "bool", "label": "CoinEx فعال", "group": "exchange"},
    "daily_outlook_hour_utc": {"attr": "daily_outlook_hour_utc", "type": "int", "label": "ساعت Daily Outlook (UTC)", "group": "scheduler"},
    "daily_outlook_minute_utc": {"attr": "daily_outlook_minute_utc", "type": "int", "label": "دقیقه Daily Outlook (UTC)", "group": "scheduler"},
    "collection_interval_minutes": {"attr": "collection_interval_minutes", "type": "int", "label": "بازه جمع‌آوری (دقیقه)", "group": "scheduler"},
    "scoring_min_dqs": {"attr": "scoring_min_dqs", "type": "float", "label": "حداقل DQS", "group": "scoring"},
    "scoring_min_confidence": {"attr": "scoring_min_confidence", "type": "float", "label": "حداقل اطمینان", "group": "scoring"},
}

GROUPS = {
    "general": "عمومی",
    "site": "سایت و دامنه",
    "api": "امنیت API",
    "telegram": "تلگرام",
    "exchange": "صرافی‌ها",
    "scheduler": "زمان‌بندی",
    "scoring": "امتیازدهی",
}

SETUP_STEPS = [
    {"id": "admin_password", "title": "رمز مدیر", "description": "تعیین رمز پنل مدیریت"},
    {"id": "jwt_secret", "title": "رمز JWT", "description": "جایگزینی رمز پیش‌فرض توسعه"},
    {"id": "api_access", "title": "دسترسی API", "description": "کلید API یا فعال‌سازی احراز هویت"},
    {"id": "exchanges", "title": "صرافی‌ها", "description": "اختیاری — کلیدهای داده بازار"},
    {"id": "telegram", "title": "تلگرام", "description": "اختیاری — اعلان‌ها"},
    {"id": "first_run", "title": "اولین تحلیل", "description": "اجرای جمع‌آوری و تحلیل از پنل"},
]
