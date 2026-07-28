"""Domain intelligence cards (Ch.17 §17.8)."""

from __future__ import annotations

from typing import Any

from src.dashboard.colors import bias_tone, msi_tone, risk_tone
from src.dashboard.contracts import DomainCard, MetricItem, SemanticColor


def _layer_map(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in analysis.get("layer_results") or []:
        if isinstance(row, dict) and row.get("layer"):
            out[str(row["layer"])] = row
    return out


def _detail(layer: dict[str, Any], *keys: str) -> Any:
    details = layer.get("details") or {}
    for k in keys:
        if details.get(k) is not None:
            return details.get(k)
        if layer.get(k) is not None:
            return layer.get(k)
    return None


def build_domain_cards(
    *,
    analysis: dict[str, Any],
    intelligence: dict[str, Any],
    snapshot: dict[str, Any] | None = None,
) -> list[DomainCard]:
    layers = _layer_map(analysis)
    snap = snapshot or {}
    cards: list[DomainCard] = []

    spot = layers.get("Spot") or {}
    cards.append(
        DomainCard(
            id="spot",
            title="Spot",
            icon="spot",
            tone=bias_tone(str(spot.get("signal") or intelligence.get("spot_bias") or "")),
            summary=str(spot.get("summary") or "Spot pressure and flow."),
            metrics=[
                MetricItem("Price", snap.get("mark_price") or _detail(spot, "price", "last_price"), hint="Last / mark"),
                MetricItem("Volume", _detail(spot, "volume", "volume_24h"), hint="24h volume"),
                MetricItem("VWAP", _detail(spot, "vwap"), hint="Volume-weighted"),
                MetricItem("Spot Pressure", _detail(spot, "spot_pressure", "pressure") or spot.get("signal"), hint="Directional pressure"),
            ],
        )
    )

    fut = layers.get("Futures") or {}
    cards.append(
        DomainCard(
            id="futures",
            title="Futures",
            icon="futures",
            tone=SemanticColor.BLUE.value,
            summary=str(fut.get("summary") or intelligence.get("derivatives_thesis") or "Derivatives positioning."),
            metrics=[
                MetricItem("Open Interest", snap.get("open_interest") or _detail(fut, "open_interest", "oi"), hint="OI"),
                MetricItem("Funding Rate", snap.get("funding_rate") or _detail(fut, "funding_rate", "funding"), hint="Perp funding"),
                MetricItem("Long/Short", _detail(fut, "long_short_ratio", "ls_ratio"), hint="Account ratio"),
                MetricItem("Liquidations", _detail(fut, "liquidations", "liq_24h"), hint="Recent liquidations"),
            ],
        )
    )

    opt = layers.get("Options") or {}
    cards.append(
        DomainCard(
            id="options",
            title="Options",
            icon="options",
            tone=SemanticColor.BLUE.value,
            summary=str(opt.get("summary") or "Options structure."),
            metrics=[
                MetricItem("Put/Call", _detail(opt, "put_call_ratio", "pc_ratio"), hint="PCR"),
                MetricItem("Max Pain", _detail(opt, "max_pain"), hint="Expiry max pain"),
                MetricItem("IV Rank", _detail(opt, "iv_rank", "ivr"), hint="IV percentile"),
                MetricItem("Gamma Exposure", _detail(opt, "gamma_exposure", "gex"), hint="Dealer GEX"),
            ],
        )
    )

    liq = layers.get("Liquidity") or {}
    cards.append(
        DomainCard(
            id="liquidity",
            title="Liquidity",
            icon="liquidity",
            tone=msi_tone("High") if "Vacuum" in str(intelligence.get("liquidity_state") or "") else SemanticColor.BLUE.value,
            summary=str(intelligence.get("liquidity_state") or liq.get("summary") or "Liquidity map."),
            metrics=[
                MetricItem("Above", _detail(liq, "liquidity_above"), hint="Resting liquidity above"),
                MetricItem("Below", _detail(liq, "liquidity_below"), hint="Resting liquidity below"),
                MetricItem("Sweep Prob.", _detail(liq, "sweep_probability") or ("Yes" if "Sweep" in str(intelligence.get("liquidity_state") or "") else "—"), hint="Sweep risk"),
                MetricItem("Order Blocks", _detail(liq, "order_blocks"), hint="Key OBs"),
            ],
        )
    )

    vol = layers.get("Volatility") or {}
    vol_regime = intelligence.get("volatility_regime") or analysis.get("volatility") or _detail(vol, "regime")
    cards.append(
        DomainCard(
            id="volatility",
            title="Volatility",
            icon="volatility",
            tone=risk_tone(str(vol_regime)),
            summary=f"Regime: {vol_regime or '—'}",
            metrics=[
                MetricItem("ATR", _detail(vol, "atr"), hint="Average true range"),
                MetricItem("HV", _detail(vol, "historical_volatility", "hv"), hint="Historical vol"),
                MetricItem("IV/HV", _detail(vol, "iv_hv_ratio"), hint="Implied vs realized"),
                MetricItem("Regime", vol_regime, hint="Current vol regime"),
            ],
        )
    )

    structure = layers.get("Market Structure") or layers.get("Technical") or {}
    cards.append(
        DomainCard(
            id="structure",
            title="Market Structure",
            icon="structure",
            tone=bias_tone(str(structure.get("signal") or analysis.get("market_bias") or "")),
            summary=str(structure.get("summary") or f"Trend quality under {analysis.get('market_regime') or '—'}."),
            metrics=[
                MetricItem("Trend", analysis.get("market_regime") or _detail(structure, "trend"), hint="Structure trend"),
                MetricItem("BOS", _detail(structure, "bos") or ("Yes" if "BOS" in str(structure.get("tags") or []) else "—"), hint="Break of structure"),
                MetricItem("CHoCH", _detail(structure, "choch") or ("Yes" if "CHoCH" in str(structure.get("tags") or []) else "—"), hint="Change of character"),
                MetricItem("Trend Quality", _detail(structure, "trend_quality", "quality") or structure.get("confidence"), hint="Structure confidence"),
            ],
        )
    )

    return cards
