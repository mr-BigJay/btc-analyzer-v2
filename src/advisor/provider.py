"""LLM provider for dashboard advisor (OpenAI-compatible API)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from src.advisor.models import AdvisorInsight
from src.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a BTC trading dashboard analyst. You review structured dashboard JSON and return practical feedback in Persian (Farsi).

Focus on:
- contradictions between timeframes, forecast, derivatives, macro, CoinEx AI, and backtest quality
- data gaps or weak confidence
- actionable ideas (not generic trading advice)

Return ONLY valid JSON with this schema:
{
  "headline": "one short Persian sentence",
  "problems": ["..."],
  "ideas": ["..."],
  "conflicts": ["..."],
  "watch_levels": [{"price": 0, "reason": "..."}],
  "confidence_note": "..."
}

Rules:
- problems: 2-5 items, concrete issues in current dashboard state
- ideas: 2-5 items, improvements or trade-planning angles
- conflicts: 0-4 items, only real contradictions
- watch_levels: 0-4 key prices with short reasons
- Write in clear Persian, concise bullets
- Do not invent prices not present in context
"""


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def generate_with_llm(context: dict[str, Any]) -> AdvisorInsight:
    if not settings.advisor_api_key:
        raise RuntimeError("Advisor API key not configured")

    base = settings.advisor_api_base.rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.advisor_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.advisor_model,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Analyze this BTC dashboard snapshot and return JSON only:\n"
                    + json.dumps(context, ensure_ascii=False)
                ),
            },
        ],
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    parsed = _parse_json_response(content)
    return AdvisorInsight(
        headline=str(parsed.get("headline") or ""),
        problems=[str(x) for x in parsed.get("problems") or []],
        ideas=[str(x) for x in parsed.get("ideas") or []],
        conflicts=[str(x) for x in parsed.get("conflicts") or []],
        watch_levels=list(parsed.get("watch_levels") or []),
        confidence_note=str(parsed.get("confidence_note") or ""),
        source="llm",
        model=settings.advisor_model,
    )
