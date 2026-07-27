"""Data Normalization Layer (Ch.3 §3.11).

Converts exchange-specific schemas into a unified internal format.
Example: BTC-USDT / BTC_USDT / BTCUSDT → BTCUSDT
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_symbol(raw: str | None, default: str = "BTCUSDT") -> str:
    """Unify exchange symbol variants into the internal BTCUSDT form."""
    if not raw:
        return default
    s = str(raw).upper().strip()
    s = s.replace(" ", "")
    # Strip common quote/base separators
    s = s.replace("_", "").replace("-", "").replace("/", "")
    # Deribit perpetual / index forms
    if s in {"BTCPERPETUAL", "BTCPERP", "BTCUSD"}:
        return "BTCUSDT"
    if s.startswith("BTC") and "USDT" in s:
        return "BTCUSDT"
    if s == "BTC":
        return "BTCUSDT"
    return s


@dataclass
class NormalizedRecord:
    """Standard fields for every normalized market datapoint (Ch.3 §3.11)."""

    timestamp: str
    symbol: str
    exchange: str
    price: float | None = None
    volume: float | None = None
    source_id: str = field(default_factory=lambda: str(uuid4()))
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "price": self.price,
            "volume": self.volume,
            "source_id": self.source_id,
            **self.extra,
        }


@dataclass
class NormalizedSnapshot:
    """Canonical cross-source market snapshot for one collection cycle."""

    symbol: str = "BTCUSDT"
    price: float | None = None
    narrative: dict = field(default_factory=dict)
    futures: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    spot: dict = field(default_factory=dict)
    bitunix: dict = field(default_factory=dict)
    technical: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    normalized_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "narrative": self.narrative,
            "futures": self.futures,
            "options": self.options,
            "spot": self.spot,
            "bitunix": self.bitunix,
            "technical": self.technical,
            "meta": self.meta,
            "normalized_at": self.normalized_at,
        }


class DataNormalizer:
    """Maps validated source payloads into NormalizedSnapshot / NormalizedRecord."""

    def normalize_record(
        self,
        exchange: str,
        payload: dict[str, Any],
        *,
        symbol_key: str = "symbol",
        price_key: str = "price",
        volume_key: str = "volume",
        timestamp_key: str = "timestamp",
    ) -> NormalizedRecord:
        ts = payload.get(timestamp_key) or utc_now_iso()
        if isinstance(ts, (int, float)):
            tsf = float(ts)
            if tsf > 1e12:
                tsf /= 1000.0
            ts = datetime.fromtimestamp(tsf, tz=timezone.utc).isoformat()
        elif isinstance(ts, datetime):
            ts = (ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)).isoformat()

        reserved = {symbol_key, price_key, volume_key, timestamp_key, "exchange", "source_id"}
        extra = {k: v for k, v in payload.items() if k not in reserved and not str(k).startswith("_")}

        return NormalizedRecord(
            timestamp=str(ts),
            symbol=normalize_symbol(payload.get(symbol_key)),
            exchange=exchange.lower(),
            price=_to_float(payload.get(price_key)),
            volume=_to_float(payload.get(volume_key)),
            source_id=str(payload.get("source_id") or uuid4()),
            extra=extra,
        )

    def normalize(self, validated_payloads: dict[str, dict]) -> NormalizedSnapshot:
        snap = NormalizedSnapshot()
        meta: dict[str, Any] = {}

        if "binance" in validated_payloads:
            raw = validated_payloads["binance"]
            snap.futures = self._normalize_exchange_block("binance", raw)
            snap.symbol = normalize_symbol(raw.get("symbol"), snap.symbol)
            snap.price = _to_float(raw.get("mark_price") or raw.get("price")) or snap.price
            meta["binance"] = "ok"

        if "deribit" in validated_payloads:
            snap.options = self._normalize_exchange_block("deribit", validated_payloads["deribit"])
            meta["deribit"] = "ok"

        if "coinex" in validated_payloads:
            snap.narrative = self._normalize_exchange_block("coinex", validated_payloads["coinex"])
            meta["coinex"] = "ok"

        if "bitunix" in validated_payloads:
            raw = validated_payloads["bitunix"]
            snap.bitunix = self._normalize_exchange_block("bitunix", raw)
            meta["bitunix"] = "ok"
            # Never override primary price from Bitunix (Ch.3 §3.9)

        if "spot" in validated_payloads:
            snap.spot = self._normalize_exchange_block("binance_spot", validated_payloads["spot"])

        snap.meta = meta
        snap.normalized_at = utc_now_iso()
        return snap

    def _normalize_exchange_block(self, exchange: str, raw: dict[str, Any]) -> dict[str, Any]:
        record = self.normalize_record(exchange, raw)
        block = record.to_dict()
        # Preserve nested domain fields
        for key, value in raw.items():
            if key.startswith("_"):
                continue
            if key not in block:
                block[key] = value
        if "symbol" in block:
            block["symbol"] = normalize_symbol(block.get("symbol"))
        return block


_SEP_RE = re.compile(r"[\s_\-/]+")


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
