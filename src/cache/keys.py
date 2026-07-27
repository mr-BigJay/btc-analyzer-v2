"""Redis / hot-cache key catalog (Ch.5 §5.9)."""


class CacheKeys:
    LATEST_MARK_PRICE = "latest_mark_price"
    LATEST_FUNDING_RATE = "latest_funding_rate"
    CURRENT_OPEN_INTEREST = "current_open_interest"
    LATEST_DAILY_OUTLOOK = "latest_daily_outlook"
    ACTIVE_TRADING_PLAN = "active_trading_plan"
    CURRENT_ORDER_BOOK = "current_order_book"
    LATEST_OPTION_CHAIN_SUMMARY = "latest_option_chain_summary"
    WS_BROADCAST = "ws_broadcast"
    BITUNIX_VALIDATION = "bitunix_validation_snapshot"
