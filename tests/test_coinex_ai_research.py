"""Tests for CoinEx AI Research parser (futures page AI Research tab)."""

from __future__ import annotations

from src.collectors.coinex.parser import parse_ai_research


SAMPLE = {
    "code": 0,
    "data": {
        "content": (
            "# 1. Market News\n"
            "### [Bearish]{.red} ETF outflows signal caution\n"
            "### [Bullish]{.green} Risk-on sentiment supports dip buys\n"
            "Price oscillating between 64,640 and 65,130.\n"
        ),
        "core_content": "BTC faces a tug-of-war, oscillating between 64,640 and 65,130.",
        "created_at": 1785158828,
        "is_up": None,
        "references": [{"id": "23485", "refer_ids": ["23485"]}],
        "summary": "BTC Consolidates Amid Institutional Caution",
        "trend": {
            "trends": [
                {"period": "short", "content": "Short-term consolidation", "orientation": "flactuate"},
                {"period": "long", "content": "Long-term recovery", "orientation": "up"},
            ],
            "summary": "Tug-of-war between ETF outflows and risk-on.",
        },
    },
    "message": "OK",
}


def test_parse_ai_research_extracts_fields():
    out = parse_ai_research(SAMPLE, symbol="BTCUSDT")
    assert out["summary"] == "BTC Consolidates Amid Institutional Caution"
    assert out["exchange"] == "coinex"
    assert out["source_tab"] == "AI Research"
    assert out["raw_article"].startswith("# 1. Market News")
    assert any("Bearish" in x or "ETF" in x for x in out["bearish_arguments"])
    assert any("Bullish" in x or "Risk-on" in x for x in out["bullish_arguments"])
    assert 64640.0 in out["support_levels"] or 64640 in out["support_levels"]
    assert 65130.0 in out["resistance_levels"] or 65130 in out["resistance_levels"]
    assert out["bias"] in {"bullish", "neutral", "bearish"}
    assert out["publication_time"]
    assert out["scenarios"]
