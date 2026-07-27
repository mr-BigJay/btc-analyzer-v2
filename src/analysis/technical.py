"""Technical Analysis Engine — chart intelligence (Ch.2 §2.5).

Indicators (EMA, VWAP, ATR, MACD, RSI, ADX, Bollinger, Fibonacci, Trend, S/R)
live here — not Funding/OI (those belong to Futures/Binance).
"""

from __future__ import annotations

from src.core import AnalysisObject, ChartObject, ModuleResult


class TechnicalAnalysisEngine:
    ENGINE = "technical"

    def analyze(self, chart: ModuleResult[ChartObject] | ChartObject) -> AnalysisObject:
        raise NotImplementedError("Awaiting Design Book Chapter 3+")

    def build_chart(self, symbol: str = "BTCUSDT", timeframe: str = "1d") -> ModuleResult[ChartObject]:
        """Produce Chart Object from OHLCV (collection of candles is separate)."""
        raise NotImplementedError("Awaiting Design Book Chapter 3+")
