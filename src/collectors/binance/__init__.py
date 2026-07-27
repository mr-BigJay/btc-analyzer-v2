"""Binance Futures collector — Layer 2 Collection (Ch.2 / Ch.3 §3.6).

Purpose: Market Reference (Design Rule 8 — primary futures reference).
Output: ModuleResult[FlowObject]
"""

from src.collectors.binance.collector import BinanceFuturesCollector

__all__ = ["BinanceFuturesCollector"]
