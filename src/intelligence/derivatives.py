"""Derivatives intelligence — relational, not isolated metrics (Ch.8 §8.8)."""

from __future__ import annotations

from typing import Any

from src.intelligence.helpers import all_tags, layer_map, signed


def analyze_derivatives(analysis: dict[str, Any]) -> str:
    layers = layer_map(analysis)
    tags = all_tags(analysis)
    spot = layers.get("Spot") or {}
    futures = layers.get("Futures") or {}
    options = layers.get("Options") or {}
    bias = str(analysis.get("market_bias") or "Neutral")

    spot_sig = signed(str(spot.get("signal") or ""))
    fut_sig = signed(str(futures.get("signal") or ""))
    opt_sig = signed(str(options.get("signal") or ""))
    fut_summary = str(futures.get("summary") or "").lower()

    oi_rising = "open interest increasing" in fut_summary or "oi increas" in fut_summary or "Leveraged Bullish" in tags
    oi_falling = "open interest decreasing" in fut_summary or "oi decreas" in fut_summary
    neg_funding = "negative funding" in fut_summary or "Negative Funding" in tags
    pos_funding = "positive funding" in fut_summary or "Funding" in tags and "positive" in fut_summary
    price_up = "Bullish" in bias or spot_sig > 0
    price_down = "Bearish" in bias or spot_sig < 0

    if oi_rising and neg_funding and price_up:
        return "Potential Short Squeeze — rising OI + negative funding + rising price"
    if oi_rising and pos_funding and price_up and spot_sig <= 0:
        return "Crowded long risk — rising OI/funding without spot confirmation"
    if oi_rising and pos_funding and price_down:
        return "Potential Long Squeeze — rising OI + positive funding + falling price"
    if oi_falling and price_down:
        return "Deleveraging markdown — falling OI with downside pressure"
    if opt_sig > 0 and fut_sig < 0:
        return "Options constructive vs futures pressure — institutional hedges diverge from leverage"
    if opt_sig < 0 and fut_sig > 0:
        return "Futures bid vs options caution — tactical leverage against hedging"
    if fut_sig > 0 and spot_sig > 0 and opt_sig >= 0:
        return "Aligned derivatives/spot stack — constructive leveraged participation"
    if fut_sig < 0 and spot_sig < 0:
        return "Bearish spot-futures alignment — downside derivatives pressure"
    if "Gamma Pinning" in tags:
        return "Gamma pinning — dealers likely suppressing realized moves near max pain"
    return "No dominant derivatives relationship thesis — mixed or incomplete signals"
