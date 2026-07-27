"""CoinEx AI Research parser — raw article + structured fields (Ch.3 §3.8).

Maps the AI Research tab payload from:
  GET /res/ai-analysis/{coin}
into NarrativeObject fields. Raw markdown is stored separately from parsed output.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def parse_ai_research(payload: dict[str, Any], symbol: str = "BTCUSDT") -> dict[str, Any]:
    """Parse CoinEx `/res/ai-analysis/{coin}` response into narrative fields."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(data, dict):
        return _envelope(
            {
                "publication_time": None,
                "symbol": symbol,
                "summary": "",
                "bullish_arguments": [],
                "bearish_arguments": [],
                "support_levels": [],
                "resistance_levels": [],
                "confidence_score": None,
                "bias": "neutral",
                "scenarios": [],
                "core_content": "",
                "trend": {},
                "references": [],
            },
            raw_article="",
            warning="empty ai research payload",
        )

    content = str(data.get("content") or "")
    core = str(data.get("core_content") or "")
    summary = str(data.get("summary") or "")
    trend = data.get("trend") if isinstance(data.get("trend"), dict) else {}
    references = data.get("references") if isinstance(data.get("references"), list) else []

    bullish = _extract_labeled_sections(content, ("bullish", "看涨"))
    bearish = _extract_labeled_sections(content, ("bearish", "看跌"))
    # Also pull from orientation-tagged trend lines
    for item in trend.get("trends") or []:
        if not isinstance(item, dict):
            continue
        orient = str(item.get("orientation") or "").lower()
        line = str(item.get("content") or "").strip()
        if not line:
            continue
        if orient in {"up", "bullish", "long"}:
            bullish.append(line)
        elif orient in {"down", "bearish", "short"}:
            bearish.append(line)

    s_core, r_core = _extract_range_levels(core)
    s_lbl = _extract_levels(f"{core}\n{content}", ("support", "支撑"))
    r_lbl = _extract_levels(f"{core}\n{content}", ("resistance", "阻力"))
    support = _dedupe_floats(s_core + s_lbl)[:10]
    resistance = _dedupe_floats(r_core + r_lbl)[:10]
    bias = _bias_from_trend(trend, bullish, bearish)
    scenarios = _scenarios_from_trend(trend)
    pub = _publication_time(data.get("created_at"))

    parsed = {
        "publication_time": pub,
        "symbol": symbol,
        "summary": summary or core[:500],
        "bullish_arguments": _dedupe(bullish)[:15],
        "bearish_arguments": _dedupe(bearish)[:15],
        "support_levels": support,
        "resistance_levels": resistance,
        "confidence_score": 0.75 if summary and content else 0.4,
        "bias": bias,
        "scenarios": scenarios,
        "core_content": core,
        "trend": trend,
        "references": references,
        "is_up": data.get("is_up"),
    }

    # Store raw article as markdown content (+ JSON envelope for traceability)
    raw_article = content or json.dumps(data, ensure_ascii=False)
    return _envelope(parsed, raw_article=raw_article)


def parse_narrative(raw_article: str, symbol: str = "BTCUSDT") -> dict[str, Any]:
    """Backward-compatible entry: JSON string or plain text."""
    text = (raw_article or "").strip()
    if not text:
        return parse_ai_research({}, symbol=symbol)

    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                # Full API envelope or bare data object
                if "data" in data or "content" in data or "summary" in data:
                    return parse_ai_research(data, symbol=symbol)
        except json.JSONDecodeError:
            pass

    # Plain markdown fallback (treat as content body)
    return parse_ai_research({"content": text, "summary": _first_paragraph(text)}, symbol=symbol)


def _bias_from_trend(trend: dict, bullish: list[str], bearish: list[str]) -> str:
    orients = []
    for item in trend.get("trends") or []:
        if isinstance(item, dict) and item.get("orientation"):
            orients.append(str(item["orientation"]).lower())
    if "up" in orients and "down" not in orients:
        return "bullish"
    if "down" in orients and "up" not in orients:
        return "bearish"
    if len(bullish) > len(bearish) + 1:
        return "bullish"
    if len(bearish) > len(bullish) + 1:
        return "bearish"
    return "neutral"


def _scenarios_from_trend(trend: dict) -> list[str]:
    out = []
    for item in trend.get("trends") or []:
        if not isinstance(item, dict):
            continue
        period = item.get("period") or ""
        content = item.get("content") or ""
        orient = item.get("orientation") or ""
        if content:
            out.append(f"{period}: {content} ({orient})".strip())
    summary = trend.get("summary")
    if summary:
        out.insert(0, str(summary))
    return out


def _publication_time(created_at: Any) -> str | None:
    if created_at is None:
        return None
    try:
        ts = float(created_at)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return str(created_at)


def _extract_labeled_sections(content: str, labels: tuple[str, ...]) -> list[str]:
    """Extract markdown headings/lines tagged Bullish/Bearish (CoinEx AI format)."""
    hits: list[str] = []
    for ln in content.splitlines():
        low = ln.lower()
        if any(f"[{lab}]" in low or lab in low for lab in labels):
            cleaned = re.sub(r"\{\.[a-z]+\}", "", ln)
            cleaned = re.sub(r"^#+\s*", "", cleaned).strip(" #-*\t")
            if cleaned:
                hits.append(cleaned[:500])
    return hits


def _extract_range_levels(text: str) -> tuple[list[float], list[float]]:
    """Extract lo/hi pairs from phrases like 'between 64,640 and 65,130'."""
    support: list[float] = []
    resistance: list[float] = []
    for a, b in re.findall(
        r"(\d{2,3}(?:,\d{3})+(?:\.\d+)?|\d{5,6}(?:\.\d+)?)\s*(?:and|to|-|–|—)\s*(\d{2,3}(?:,\d{3})+(?:\.\d+)?|\d{5,6}(?:\.\d+)?)",
        text,
        flags=re.I,
    ):
        try:
            lo, hi = float(a.replace(",", "")), float(b.replace(",", ""))
            if lo > hi:
                lo, hi = hi, lo
            if _is_btc_price(lo) and _is_btc_price(hi):
                support.append(lo)
                resistance.append(hi)
        except ValueError:
            continue
    return support, resistance


def _is_btc_price(value: float) -> bool:
    return 10_000 <= value <= 500_000


def _extract_levels(text: str, keywords: tuple[str, ...]) -> list[float]:
    """Extract prices only from lines with explicit S/R labels (not 'supported')."""
    levels: list[float] = []
    # Require word-boundary / explicit level phrasing to avoid "supported by…"
    label_re = re.compile(
        r"(?i)(?:\b(?:support|resistance)\s*(?:level|zone)?\b|\b(?:支撑|阻力)\b)"
    )
    for ln in text.splitlines():
        low = ln.lower()
        # Keep keyword filter for chinese + english; reject 'supported'
        if "supported" in low and "support level" not in low and "support zone" not in low:
            # still allow if explicit support level also present
            if not label_re.search(ln):
                continue
        if not any(re.search(rf"(?i)\b{re.escape(k)}\b", ln) for k in keywords):
            continue
        if not label_re.search(ln) and not any(k in ln for k in ("支撑", "阻力")):
            continue
        for match in re.findall(r"\b(\d{2,3}(?:,\d{3})+(?:\.\d+)?|\d{5,6}(?:\.\d+)?)\b", ln):
            try:
                val = float(match.replace(",", ""))
            except ValueError:
                continue
            if _is_btc_price(val):
                levels.append(val)
    return levels


def _envelope(parsed: dict[str, Any], raw_article: str, warning: str | None = None) -> dict[str, Any]:
    return {
        "api_status": "OK" if raw_article else "EMPTY",
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
        "scenarios": parsed.get("scenarios") or [],
        "core_content": parsed.get("core_content") or "",
        "trend": parsed.get("trend") or {},
        "references": parsed.get("references") or [],
        "raw_article": raw_article,
        "parsed": parsed,
        "source_id": str(uuid4()),
        "source_page": "https://www.coinex.com/en/futures/btc-usdt#aiReport",
        "source_tab": "AI Research",
        "warning": warning,
        "_required_fields": ["symbol", "timestamp"],
    }


def _first_paragraph(text: str) -> str:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return (parts[0] if parts else text)[:2000]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _dedupe_floats(values: list[float]) -> list[float]:
    seen: set[float] = set()
    out: list[float] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out
