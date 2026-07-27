"""Participant model + institutional footprint (Ch.8 §8.5–§8.6)."""

from __future__ import annotations

from typing import Any

from src.intelligence.contracts import InstitutionalActivity, Participant
from src.intelligence.helpers import all_tags, layer_map, signed


def estimate_participants(analysis: dict[str, Any]) -> tuple[str, str, dict[str, float]]:
    """Return (dominant_participant, institutional_activity, scores)."""
    layers = layer_map(analysis)
    tags = all_tags(analysis)
    spot = layers.get("Spot") or {}
    futures = layers.get("Futures") or {}
    options = layers.get("Options") or {}
    technical = layers.get("Technical") or {}

    scores = {p.value: 0.0 for p in Participant}

    # Retail — emotional / momentum
    if "Overbought" in tags or "Oversold" in tags:
        scores[Participant.RETAIL.value] += 1.5
    if abs(signed(str(technical.get("signal") or ""))) > 0 and float(technical.get("confidence") or 0) > 70:
        scores[Participant.RETAIL.value] += 0.8
    if "Leveraged Bullish" in tags or "Leveraged Bearish" in tags:
        scores[Participant.RETAIL.value] += 1.0

    # Professionals — tactical
    if "Short Squeeze Risk" in tags or "Long Squeeze Risk" in tags:
        scores[Participant.PROFESSIONAL.value] += 1.5
    if analysis.get("conflicts"):
        scores[Participant.PROFESSIONAL.value] += 0.8
    scores[Participant.PROFESSIONAL.value] += 0.5  # baseline presence

    # Whales — large spot accumulation/distribution
    details = spot.get("details") or {}
    large_buy = float(details.get("large_trade_buy_usd") or details.get("large_buy") or 0)
    large_sell = float(details.get("large_trade_sell_usd") or details.get("large_sell") or 0)
    if large_buy > large_sell * 1.2 and large_buy > 0:
        scores[Participant.WHALES.value] += 2.0
    if large_sell > large_buy * 1.2 and large_sell > 0:
        scores[Participant.WHALES.value] += 2.0
    if "Accumulation" in tags or "Distribution" in tags:
        scores[Participant.WHALES.value] += 1.2

    # Institutions — strategic + options
    if "Dealer Support" in tags or "Dealer Resistance" in tags or "Bullish Hedging" in tags or "Bearish Hedging" in tags:
        scores[Participant.INSTITUTIONS.value] += 1.8
    if "Gamma Pinning" in tags or float(options.get("confidence") or 0) >= 65:
        scores[Participant.INSTITUTIONS.value] += 1.0
    if "Accumulation" in tags and signed(str(spot.get("signal") or "")) > 0:
        scores[Participant.INSTITUTIONS.value] += 1.2

    # Options dealers
    if "Gamma Pinning" in tags or "Dealer Support" in tags or "Dealer Resistance" in tags:
        scores[Participant.OPTIONS_DEALERS.value] += 2.5
    if "Volatility Expansion" in tags:
        scores[Participant.OPTIONS_DEALERS.value] += 0.8

    dominant = max(scores, key=scores.get)

    # Institutional footprint
    inst_score = 0.0
    if "Accumulation" in tags or "Buyer Dominance" in tags:
        inst_score += 1.5
    if "Distribution" in tags or "Seller Dominance" in tags:
        inst_score -= 1.5
    if signed(str(options.get("signal") or "")) > 0:
        inst_score += 0.8
    elif signed(str(options.get("signal") or "")) < 0:
        inst_score -= 0.8
    if large_buy > large_sell:
        inst_score += 0.7
    elif large_sell > large_buy:
        inst_score -= 0.7
    if "Dealer Support" in tags:
        inst_score += 0.6
    if "Dealer Resistance" in tags:
        inst_score -= 0.6

    if inst_score >= 1.2:
        activity = InstitutionalActivity.BUYING.value
    elif inst_score <= -1.2:
        activity = InstitutionalActivity.SELLING.value
    else:
        activity = InstitutionalActivity.NEUTRAL.value

    # futures unused except via tags — keep for future footprint rules
    _ = futures

    return dominant, activity, scores
