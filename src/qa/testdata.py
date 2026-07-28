"""Test data management catalog (Ch.22 §22.17)."""

from __future__ import annotations

from typing import Any

from src.qa.contracts import TEST_DATA_CATEGORIES, utc_now_iso


def synthetic_tick(symbol: str = "BTCUSDT", price: float = 65000.0) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "price": price,
        "timestamp": utc_now_iso(),
        "source": "synthetic",
    }


def corrupted_tick() -> dict[str, Any]:
    return {"symbol": "", "price": -1, "timestamp": None, "source": "corrupted"}


def edge_case_catalog() -> dict[str, Any]:
    return {
        "categories": TEST_DATA_CATEGORIES,
        "examples": {
            "Synthetic data": synthetic_tick(),
            "Corrupted inputs": corrupted_tick(),
            "High-volatility periods": {"atr_pct": 8.5, "regime": "high_vol"},
            "Low-liquidity periods": {"spread_bps": 45, "depth_usd": 12_000},
        },
        "production_data_modified": False,
        "timestamp": utc_now_iso(),
    }
