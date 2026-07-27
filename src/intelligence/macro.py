"""Macro intelligence (Ch.8 §8.10).

Reads optional cached macro context. Never fabricates missing event data —
defaults to Neutral with explicit incompleteness.
"""

from __future__ import annotations

from typing import Any

from src.storage.redis_cache import redis_cache

# Optional cache key populated by future macro collectors / manual overrides
MACRO_CACHE_KEY = "macro_context"


def assess_macro(*, macro_event: bool = False) -> tuple[str, list[dict[str, Any]], float]:
    """Return (macro_bias, events, completeness 0–1)."""
    cached = redis_cache.get(MACRO_CACHE_KEY)
    events: list[dict[str, Any]] = []
    completeness = 0.35  # exchange-centric mode without full macro feed

    if isinstance(cached, dict):
        events = list(cached.get("events") or [])
        bias = str(cached.get("bias") or "Neutral")
        completeness = float(cached.get("completeness") or 0.8)
        if events:
            return bias, events, min(1.0, completeness)

    if macro_event:
        events = [
            {
                "name": "Scheduled macro event window",
                "impact_score": 70,
                "bias": "Uncertain",
                "note": "Elevated uncertainty — event details not fully loaded",
            }
        ]
        return "Cautious", events, 0.45

    return "Neutral", events, completeness
