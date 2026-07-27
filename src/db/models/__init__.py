"""ORM models — six domains (Ch.4 §4.4)."""

from src.db.models.ai import CoinExAnalysis, DailyOutlook, TradingPlan
from src.db.models.config_domain import Exchange, Symbol, SystemSetting
from src.db.models.market import (
    FundingRate,
    Liquidation,
    MarketCandle,
    OpenInterest,
    OrderBookSnapshot,
    Trade,
)
from src.db.models.options import OptionsAnalyticsSnapshot, OptionsChain
from src.db.models.system import ApiCallLog, ErrorLog, SchedulerLog
from src.db.models.technical import ChartPattern, MarketStructure, TechnicalIndicator
from src.db.session import get_engine, get_session, init_db, reset_engine

# Back-compat aliases for transitional imports
DailyOutlookRecord = DailyOutlook
TradingPlanRecord = TradingPlan
CoinExAnalysisRecord = CoinExAnalysis
OrderBookSnapshotRecord = OrderBookSnapshot
LiquidationEventRecord = Liquidation

__all__ = [
    "Exchange",
    "Symbol",
    "SystemSetting",
    "MarketCandle",
    "FundingRate",
    "OpenInterest",
    "Liquidation",
    "OrderBookSnapshot",
    "Trade",
    "OptionsChain",
    "OptionsAnalyticsSnapshot",
    "TechnicalIndicator",
    "ChartPattern",
    "MarketStructure",
    "CoinExAnalysis",
    "DailyOutlook",
    "TradingPlan",
    "SchedulerLog",
    "ApiCallLog",
    "ErrorLog",
    "get_engine",
    "get_session",
    "init_db",
    "reset_engine",
    # aliases
    "DailyOutlookRecord",
    "TradingPlanRecord",
    "CoinExAnalysisRecord",
    "OrderBookSnapshotRecord",
    "LiquidationEventRecord",
]
