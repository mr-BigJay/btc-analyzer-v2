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

CHAT_SYSTEM_PROMPT = """You are the BTC Analyzer AI copilot connected to a live trading dashboard.

You have full access to the latest dashboard JSON context the user shares with each turn.
Speak in natural Persian (Farsi). Be direct, practical, and conversational — not robotic.

You may:
- explain contradictions and risks in the dashboard
- answer follow-up questions about BTC setup, levels, forecast, CoinEx AI, backtest quality
- suggest what to watch next or how to think about the current market
- disagree with weak signals when data does not support them

You must NOT:
- claim you executed trades or changed the bot
- give guaranteed profit promises
- invent prices or metrics absent from context

Keep answers concise unless the user asks for depth. Use short paragraphs or bullets when helpful.
If context is missing something, say so honestly.
"""


def _chat_completion(messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
    if not settings.advisor_api_key:
        raise RuntimeError("Advisor API key not configured")

    base = settings.advisor_api_base.rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.advisor_api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": settings.advisor_model,
        "temperature": 0.55,
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    with httpx.Client(timeout=90.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return data["choices"][0]["message"]["content"]


def chat_with_llm(
    context: dict[str, Any],
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": "Latest dashboard context JSON:\n" + json.dumps(context, ensure_ascii=False),
        },
    ]
    for item in history or []:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return _chat_completion(messages).strip()


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def generate_with_llm(context: dict[str, Any]) -> AdvisorInsight:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Analyze this BTC dashboard snapshot and return JSON only:\n"
                + json.dumps(context, ensure_ascii=False)
            ),
        },
    ]
    content = _chat_completion(messages, json_mode=True)
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
