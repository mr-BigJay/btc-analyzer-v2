"""Centralized symbol registry (Ch.12 §12.16).

Maps provider-specific symbols to internal identifiers so exchange naming
never leaks into business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SymbolMapping:
    provider: str
    external: str
    internal: str
    market: str = "Futures"  # Spot | Futures | Options | Perp


# Default registry — extend when adding adapters (Bybit/OKX/…)
DEFAULT_MAPPINGS: tuple[SymbolMapping, ...] = (
    SymbolMapping("binance", "BTCUSDT", "BTCUSDT", "Futures"),
    SymbolMapping("binance", "BTCUSDT", "BTCUSDT", "Spot"),
    SymbolMapping("binance", "BTC/USDT", "BTCUSDT", "Spot"),
    SymbolMapping("deribit", "BTC-PERPETUAL", "BTCUSD_PERP", "Futures"),
    SymbolMapping("deribit", "BTC", "BTCUSDT", "Options"),
    SymbolMapping("coinex", "BTCUSDT", "BTCUSDT", "Futures"),
    SymbolMapping("bitunix", "BTCUSDT", "BTCUSDT", "Futures"),
)


class SymbolRegistry:
    """Provider → internal symbol abstraction."""

    def __init__(self, mappings: Iterable[SymbolMapping] | None = None) -> None:
        self._maps = list(mappings or DEFAULT_MAPPINGS)
        self._by_provider: dict[tuple[str, str], str] = {}
        for m in self._maps:
            key = (m.provider.lower(), m.external.upper())
            self._by_provider[key] = m.internal
            # Also index without separators
            compact = m.external.upper().replace("-", "").replace("_", "").replace("/", "")
            self._by_provider[(m.provider.lower(), compact)] = m.internal

    def to_internal(self, provider: str, external: str, *, default: str = "BTCUSDT") -> str:
        provider_l = provider.lower()
        ext = external.upper().strip()
        if (provider_l, ext) in self._by_provider:
            return self._by_provider[(provider_l, ext)]
        compact = ext.replace("-", "").replace("_", "").replace("/", "")
        if (provider_l, compact) in self._by_provider:
            return self._by_provider[(provider_l, compact)]
        # Fallback: normalize separators for known BTC pairs
        if compact in {"BTCUSDT", "BTCUSD", "BTCPERPETUAL", "BTCPERP"}:
            if provider_l == "deribit" and "PERP" in compact:
                return "BTCUSD_PERP"
            return "BTCUSDT"
        return default

    def register(self, mapping: SymbolMapping) -> None:
        self._maps.append(mapping)
        self._by_provider[(mapping.provider.lower(), mapping.external.upper())] = mapping.internal

    def list_mappings(self) -> list[dict[str, str]]:
        return [
            {
                "provider": m.provider,
                "external": m.external,
                "internal": m.internal,
                "market": m.market,
            }
            for m in self._maps
        ]


# Process singleton
symbol_registry = SymbolRegistry()
