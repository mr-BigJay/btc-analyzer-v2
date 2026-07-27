"""CoinEx narrative parser — extract structured fields; store raw separately (Ch.3 §3.8)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def parse_narrative(raw_article: str, symbol: str = "BTCUSDT") -> dict[str, Any]:
    """Parse JSON or lightly structured text into narrative fields.

    Always returns both raw_article and parsed fields.
    """
    parsed: dict[str, Any] = {
        "publication_time": None,
        "symbol": symbol,
        "summary": "",
        "bullish_arguments": [],
        "bearish_arguments": [],
        "support_levels": [],
        "resistance_levels": [],
        "confidence_score": None,
        "bias": "neutral",
    }

    text = (raw_article or "").strip()
    if not text:
        return _envelope(parsed, raw_article="", warning="empty article")

    # Prefer JSON payloads
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, list) and data:
                data = data[0]
            if isinstance(data, dict):
                parsed.update(_from_dict(data, symbol))
                return _envelope(parsed, raw_article=text)
        except json.JSONDecodeError:
            pass

    parsed["summary"] = _first_paragraph(text)
    parsed["bullish_arguments"] = _extract_bullets(text, ("bull", "long", "upside", "看涨"))
    parsed["bearish_arguments"] = _extract_bullets(text, ("bear", "short", "downside", "看跌"))
    parsed["support_levels"] = _extract_levels(text, ("support", "支撑"))
    parsed["resistance_levels"] = _extract_levels(text, ("resistance", "阻力"))
    parsed["publication_time"] = datetime.now(timezone.utc).isoformat()
    return _envelope(parsed, raw_article=text)


def _from_dict(data: dict, symbol: str) -> dict[str, Any]:
    return {
        "publication_time": data.get("publication_time") or data.get("published_at") or data.get("time"),
        "symbol": data.get("symbol") or symbol,
        "summary": data.get("summary") or data.get("content") or data.get("title") or "",
        "bullish_arguments": list(data.get("bullish_arguments") or data.get("bullish") or []),
        "bearish_arguments": list(data.get("bearish_arguments") or data.get("bearish") or []),
        "support_levels": [float(x) for x in (data.get("support_levels") or data.get("support") or []) if _is_num(x)],
        "resistance_levels": [float(x) for x in (data.get("resistance_levels") or data.get("resistance") or []) if _is_num(x)],
        "confidence_score": _f(data.get("confidence_score") or data.get("confidence")),
        "bias": data.get("bias") or data.get("sentiment") or "neutral",
    }


def _envelope(parsed: dict[str, Any], raw_article: str, warning: str | None = None) -> dict[str, Any]:
    return {
        "status": "OK" if raw_article else "EMPTY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": parsed.get("symbol") or "BTCUSDT",
        "exchange": "coinex",
        "publication_time": parsed.get("publication_time"),
        "summary": parsed.get("summary") or "",
        "bullish_arguments": parsed.get("bullish_arguments") or [],
        "bearish_arguments": parsed.get("bearish_arguments") or [],
        "support_levels": parsed.get("support_levels") or [],
        "resistance_levels": parsed.get("resistance_levels") or [],
        "confidence_score": parsed.get("confidence_score"),
        "bias": parsed.get("bias") or "neutral",
        "raw_article": raw_article,
        "parsed": parsed,
        "source_id": str(uuid4()),
        "warning": warning,
        "_required_fields": ["symbol", "timestamp"],
    }


def _first_paragraph(text: str) -> str:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return (parts[0] if parts else text)[:2000]


def _extract_bullets(text: str, keywords: tuple[str, ...]) -> list[str]:
    lines = [ln.strip(" •-\t") for ln in text.splitlines() if ln.strip()]
    hits = []
    for ln in lines:
        low = ln.lower()
        if any(k.lower() in low for k in keywords) and len(ln) > 8:
            hits.append(ln[:500])
    return hits[:10]


def _extract_levels(text: str, keywords: tuple[str, ...]) -> list[float]:
    levels: list[float] = []
    for ln in text.splitlines():
        low = ln.lower()
        if not any(k.lower() in low for k in keywords):
            continue
        for match in re.findall(r"\b(\d{4,6}(?:\.\d+)?)\b", ln):
            try:
                levels.append(float(match))
            except ValueError:
                continue
    # unique preserve order
    seen = set()
    out = []
    for v in levels:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out[:10]


def _is_num(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
