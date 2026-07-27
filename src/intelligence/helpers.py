"""Shared helpers for Market Intelligence Framework."""

from __future__ import annotations

from typing import Any

from src.analysis.contracts import MarketAnalysisOutput


def as_dict(analysis: MarketAnalysisOutput | dict[str, Any]) -> dict[str, Any]:
    if isinstance(analysis, MarketAnalysisOutput):
        return analysis.to_dict()
    return dict(analysis)


def layer_map(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in analysis.get("layer_results") or []:
        if isinstance(row, dict) and row.get("layer"):
            out[str(row["layer"])] = row
    return out


def all_tags(analysis: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    for row in analysis.get("layer_results") or []:
        tags.update(row.get("tags") or [])
    return tags


def signed(signal: str) -> float:
    s = signal or ""
    if s in ("Bullish", "bullish"):
        return 1.0
    if s in ("Slightly Bullish", "slightly_bullish"):
        return 0.5
    if s in ("Bearish", "bearish"):
        return -1.0
    if s in ("Slightly Bearish", "slightly_bearish"):
        return -0.5
    return 0.0
