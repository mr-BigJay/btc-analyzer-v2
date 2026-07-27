"""Binance Futures collector — market reference layer.

Responsibility (Doc 01 §4):
  Funding, Open Interest, CVD, Order Flow, Liquidations.
  Reference market for price discovery and positioning.
  Never produces a trade decision alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class FuturesEvidence:
    """Structured futures market evidence from Binance."""

    symbol: str = "BTCUSDT"
    price: float | None = None
    funding_rate: float | None = None
    open_interest: float | None = None
    open_interest_change_pct: float | None = None
    cvd_signal: str = "neutral"
    order_flow_bias: str = "neutral"
    liquidation_bias: str = "neutral"
    details: dict = field(default_factory=dict)
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = "binance_futures"


class BinanceFuturesCollector:
    """Collects Binance Futures market-reference data.

    Implementation details arrive in later design documents.
    """

    def collect(self) -> FuturesEvidence:
        raise NotImplementedError("Awaiting Design Doc 02+ for Binance futures spec")
