"""Localization helpers (Ch.10 §10.17) — analytics remain language-independent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


LABELS = {
    "en": {
        "market_bias": "Market Bias",
        "confidence": "Confidence",
        "regime": "Regime",
        "primary_scenario": "Primary Scenario",
        "risk": "Risk",
        "trading_plan": "Trading Plan",
        "disclaimer": "Disclaimer",
    },
    "fa": {
        "market_bias": "بایاس بازار",
        "confidence": "اطمینان",
        "regime": "رژیم",
        "primary_scenario": "سناریوی اصلی",
        "risk": "ریسک",
        "trading_plan": "پلن معاملاتی",
        "disclaimer": "سلب مسئولیت",
    },
}


def labels_for(language: str = "en") -> dict[str, str]:
    return dict(LABELS.get(language, LABELS["en"]))


def format_timestamp(value: str | None, *, language: str = "en", tz_name: str = "UTC") -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Keep UTC ISO for machine; human label differs lightly by language
    stamp = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if language == "fa":
        return stamp  # numerical Gregorian stamp; full Jalali can be added later
    return stamp


def localize_report_shell(report: dict[str, Any], *, language: str = "en", timezone: str = "UTC") -> dict[str, Any]:
    """Attach localization shell without mutating analytical numbers."""
    out = dict(report)
    meta = dict(out.get("metadata") or {})
    meta["language"] = language
    meta["timezone"] = timezone
    meta["labels"] = labels_for(language)
    meta["generated_at_local"] = format_timestamp(out.get("generated_at"), language=language, tz_name=timezone)
    out["metadata"] = meta
    return out
