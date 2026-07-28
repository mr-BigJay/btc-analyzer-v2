"""Typed collector families (Ch.12 §12.6).

Wrap exchange adapters into Spot / Futures / Options / Volatility / Macro roles
so analysis never depends on provider-specific collectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from src.collectors.binance import BinanceFuturesCollector
from src.collectors.bitunix import BitunixCollector
from src.collectors.coinex import CoinExCollector
from src.collectors.deribit import DeribitOptionsCollector
from src.core import ModuleResult
from src.storage.repository import CentralRepository


@dataclass
class TypedCollectorResult:
    collector_type: str
    providers: list[str]
    results: dict[str, ModuleResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "collector_type": self.collector_type,
            "providers": self.providers,
            "results": {k: v.to_dict() for k, v in self.results.items()},
        }


class SpotCollector:
    """Trades, order book, candles, VWAP, volume."""

    TYPE = "Spot"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.binance = BinanceFuturesCollector(self.repository)

    def collect(self) -> TypedCollectorResult:
        # Spot path uses Binance spot helper when available
        import asyncio

        async def _run() -> dict:
            return await self.binance.collect_spot_async()

        try:
            data = asyncio.run(_run())
            from src.core import ModuleResult, ModuleStatus

            result = ModuleResult(
                module="BinanceSpot",
                status=ModuleStatus.OK,
                confidence=0.9,
                data=data,
                source_live=True,
            )
        except Exception as exc:  # noqa: BLE001
            result = self.binance.fallback_from_cache(exc)
        return TypedCollectorResult(self.TYPE, ["binance"], {"binance_spot": result})


class FuturesCollector:
    """OI, funding, liquidations, L/S ratio, basis."""

    TYPE = "Futures"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.binance = BinanceFuturesCollector(self.repository)
        self.bitunix = BitunixCollector(self.repository)

    def collect(self) -> TypedCollectorResult:
        results = {
            "binance": self.binance.collect_resilient(),
            "bitunix": self.bitunix.collect_resilient(),
        }
        return TypedCollectorResult(self.TYPE, ["binance", "bitunix"], results)


class OptionsCollector:
    """PCR, max pain, OI by strike, IV surface, GEX, skew."""

    TYPE = "Options"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.deribit = DeribitOptionsCollector(self.repository)

    def collect(self) -> TypedCollectorResult:
        return TypedCollectorResult(self.TYPE, ["deribit"], {"deribit": self.deribit.collect_resilient()})


class VolatilityCollector:
    """HV / RV / ATR / Bollinger width — derived from cached OHLCV, not fabricated."""

    TYPE = "Volatility"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()

    def collect(self) -> TypedCollectorResult:
        from src.core import ModuleResult, ModuleStatus
        from src.core.contracts import utc_now_iso

        cached = self.repository.memory.get("technical_cache_1h") or self.repository.load_snapshot("technical")
        ohlcv = []
        if isinstance(cached, dict):
            ohlcv = cached.get("ohlcv") or (cached.get("data") or {}).get("ohlcv") or []
        payload = {
            "timestamp": utc_now_iso(),
            "symbol": "BTCUSDT",
            "exchange": "derived",
            "candle_count": len(ohlcv) if isinstance(ohlcv, list) else 0,
            "historical_volatility": None,
            "realized_volatility": None,
            "atr": None,
            "bollinger_width": None,
            "source": "technical_cache",
        }
        # Compute simple realized vol / ATR when enough candles exist
        if isinstance(ohlcv, list) and len(ohlcv) >= 20:
            closes = []
            trs = []
            for c in ohlcv[-30:]:
                if not isinstance(c, dict):
                    continue
                try:
                    closes.append(float(c["close"]))
                    h, low, o = float(c["high"]), float(c["low"]), float(c.get("open") or c["close"])
                    trs.append(max(h - low, abs(h - o), abs(low - o)))
                except (KeyError, TypeError, ValueError):
                    continue
            if len(closes) >= 2:
                import math

                rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
                if rets:
                    mean = sum(rets) / len(rets)
                    var = sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1)
                    payload["realized_volatility"] = round(math.sqrt(var) * math.sqrt(365) * 100, 4)
                    payload["historical_volatility"] = payload["realized_volatility"]
            if trs:
                payload["atr"] = round(sum(trs) / len(trs), 4)
                mid = sum(closes[-20:]) / min(20, len(closes)) if closes else 0
                if mid:
                    payload["bollinger_width"] = round((max(closes[-20:]) - min(closes[-20:])) / mid, 6)

        status = ModuleStatus.OK if payload.get("atr") is not None else ModuleStatus.DEGRADED
        result = ModuleResult(
            module="Volatility",
            status=status,
            confidence=0.8 if status == ModuleStatus.OK else 0.4,
            data=payload,
            source_live=False,
            warning=None if status == ModuleStatus.OK else "Insufficient OHLCV for volatility metrics",
        )
        return TypedCollectorResult(self.TYPE, ["derived"], {"volatility": result})


class MacroCollector:
    """Economic calendar / CPI / FOMC / ETF / DXY / yields.

    Does not fabricate missing macro feeds — returns DEGRADED placeholder until
    a dedicated macro provider adapter is configured.
    """

    TYPE = "Macro"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()

    def collect(self) -> TypedCollectorResult:
        from src.core import ModuleResult, ModuleStatus
        from src.core.contracts import utc_now_iso

        cached = self.repository.load_snapshot("Macro")
        if isinstance(cached, dict) and cached.get("data"):
            data = cached["data"] if isinstance(cached.get("data"), dict) else cached
            result = ModuleResult(
                module="Macro",
                status=ModuleStatus.DEGRADED,
                confidence=0.3,
                data=data,
                source_live=False,
                warning="Using cached macro snapshot — live macro feed not configured",
            )
        else:
            result = ModuleResult(
                module="Macro",
                status=ModuleStatus.DEGRADED,
                confidence=0.0,
                data={
                    "timestamp": utc_now_iso(),
                    "symbol": "BTCUSDT",
                    "exchange": "macro",
                    "economic_calendar": [],
                    "cpi": None,
                    "fomc": None,
                    "etf_flows": None,
                    "dxy": None,
                    "treasury_yields": None,
                    "feed_configured": False,
                },
                source_live=False,
                warning="Macro provider adapter not configured — values withheld",
            )
        return TypedCollectorResult(self.TYPE, ["macro"], {"macro": result})


COLLECTOR_TYPES: dict[str, Callable[..., Any]] = {
    "spot": SpotCollector,
    "futures": FuturesCollector,
    "options": OptionsCollector,
    "volatility": VolatilityCollector,
    "macro": MacroCollector,
}
