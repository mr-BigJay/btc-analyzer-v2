"""Data access rules (Ch.11 §11.25) — modules write only to their domains."""

from __future__ import annotations

from enum import Enum


class DataDomain(str, Enum):
    MARKET = "market"
    ANALYSIS = "analysis"
    DECISION = "decision"
    REPORTING = "reporting"
    SYSTEM = "system"
    CONFIG = "config"


# Writer → allowed tables (READ is unrestricted through CentralRepository read APIs)
WRITE_PERMISSIONS: dict[str, set[str]] = {
    "collector": {
        "market_candles",
        "funding_rates",
        "open_interest",
        "liquidations",
        "orderbook_snapshot",
        "trades",
        "options_chain",
        "options_analytics",
        "spot_data",
        "futures_data",
        "options_data",
        "coinex_analysis",
        "exchanges",  # api_status / last_sync only
        "api_call_logs",
        "error_logs",
    },
    "analysis": {
        "technical_indicators",
        "chart_patterns",
        "market_structure",
        "liquidity_zones",
        "volatility_data",
        "feature_store",
    },
    "features": {
        "feature_store",
    },
    "scoring": {
        "market_scores",
    },
    "ai": {
        "ai_decisions",
        "daily_outlook",
        "trading_plan",
    },
    "reporting": {
        "reports",
        "alerts",
    },
    "system": {
        "scheduler_logs",
        "api_call_logs",
        "error_logs",
        "system_settings",
    },
}


def assert_can_write(module: str, table: str) -> None:
    allowed = WRITE_PERMISSIONS.get(module)
    if allowed is None:
        raise PermissionError(f"Unknown data module '{module}'")
    if table not in allowed:
        raise PermissionError(f"Module '{module}' cannot WRITE table '{table}' (Ch.11 §11.25)")


def can_write(module: str, table: str) -> bool:
    return table in WRITE_PERMISSIONS.get(module, set())
