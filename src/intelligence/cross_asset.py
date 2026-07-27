"""Cross-asset intelligence (Ch.8 §8.11).

Uses optional cached correlation snapshot. Without data, bias is Neutral
and incompleteness is reported — never invents prices/correlations.
"""

from __future__ import annotations

from typing import Any

from src.storage.redis_cache import redis_cache

CROSS_ASSET_CACHE_KEY = "cross_asset_context"

WATCHLIST = ("ETH", "SOL", "Gold", "Silver", "Nasdaq", "S&P 500", "DXY", "VIX", "Oil")


def assess_cross_asset() -> tuple[str, dict[str, Any], float]:
    """Return (cross_asset_bias, snapshot, completeness)."""
    cached = redis_cache.get(CROSS_ASSET_CACHE_KEY)
    if isinstance(cached, dict) and cached.get("assets"):
        bias = str(cached.get("bias") or "Neutral")
        completeness = float(cached.get("completeness") or 0.75)
        return bias, cached, min(1.0, completeness)

    # Placeholder structure — empty correlations until feed exists
    snapshot = {
        "assets": {name: {"correlation": None, "bias": "Unknown"} for name in WATCHLIST},
        "note": "Cross-asset feed not configured — bias Neutral by design (no fabrication)",
    }
    return "Neutral", snapshot, 0.25
