"""Deribit parsers + derived options metrics (collection-layer math only).

Derived metrics listed in Ch.3 §3.7 are computed here as data transforms,
not trading recommendations.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_option_chain(
    instruments: list[dict],
    summaries: list[dict],
    index_price: float | None,
) -> dict[str, Any]:
    summary_by_name = {s.get("instrument_name"): s for s in summaries if isinstance(s, dict)}
    chain: list[dict[str, Any]] = []
    call_oi = 0.0
    put_oi = 0.0
    call_vol = 0.0
    put_vol = 0.0
    total_oi = 0.0
    strike_call_oi: dict[float, float] = defaultdict(float)
    strike_put_oi: dict[float, float] = defaultdict(float)
    ivs: list[float] = []
    gex = 0.0
    dealer_gamma = 0.0
    dealer_delta = 0.0

    for inst in instruments:
        name = inst.get("instrument_name")
        if not name:
            continue
        summary = summary_by_name.get(name, {})
        option_type = (inst.get("option_type") or "").lower()
        strike = _f(inst.get("strike"))
        expiry = inst.get("expiration_timestamp")
        oi = _f(summary.get("open_interest")) or 0.0
        vol = _f(summary.get("volume")) or 0.0
        mark_iv = _f(summary.get("mark_iv"))
        greeks_raw = summary.get("greeks") if isinstance(summary.get("greeks"), dict) else {}
        greeks = {
            "delta": _f(greeks_raw.get("delta") if greeks_raw else summary.get("delta")),
            "gamma": _f(greeks_raw.get("gamma") if greeks_raw else summary.get("gamma")),
            "vega": _f(greeks_raw.get("vega") if greeks_raw else summary.get("vega")),
            "theta": _f(greeks_raw.get("theta") if greeks_raw else summary.get("theta")),
        }
        # Book summary may embed mark_iv / greeks differently
        if mark_iv is None:
            mark_iv = _f(summary.get("mark_iv"))
        if mark_iv is not None:
            ivs.append(mark_iv)

        if option_type == "call":
            call_oi += oi
            call_vol += vol
            if strike is not None:
                strike_call_oi[strike] += oi
        elif option_type == "put":
            put_oi += oi
            put_vol += vol
            if strike is not None:
                strike_put_oi[strike] += oi

        total_oi += oi
        gamma = greeks.get("gamma") or 0.0
        delta = greeks.get("delta") or 0.0
        # Approximate dealer as short retail → negative customer gamma
        if index_price and strike:
            gex += -oi * gamma * (index_price**2) * 0.01
            dealer_gamma += -oi * gamma
            dealer_delta += -oi * delta

        chain.append(
            {
                "instrument": name,
                "option_type": option_type,
                "strike": strike,
                "expiration": expiry,
                "volume": vol,
                "open_interest": oi,
                "mark_iv": mark_iv,
                "greeks": greeks,
                "bid": _f(summary.get("bid_price")),
                "ask": _f(summary.get("ask_price")),
                "mark_price": _f(summary.get("mark_price")),
            }
        )

    put_call_ratio = (put_oi / call_oi) if call_oi > 0 else None
    max_pain = _compute_max_pain(strike_call_oi, strike_put_oi)
    iv_mean = sum(ivs) / len(ivs) if ivs else None
    # IV rank / percentile need history — placeholders until technical_cache accumulates
    iv_rank = None
    iv_percentile = None
    skew = _compute_skew(chain, index_price)

    return {
        "status": "OK",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": "BTCUSDT",
        "exchange": "deribit",
        "currency": "BTC",
        "index_price": index_price,
        "option_chain": chain,
        "volume": call_vol + put_vol,
        "open_interest": total_oi,
        "put_call_ratio": put_call_ratio,
        "max_pain": max_pain,
        "iv_rank": iv_rank,
        "iv_percentile": iv_percentile,
        "implied_volatility_mean": iv_mean,
        "gamma_exposure": gex,
        "dealer_gamma": dealer_gamma,
        "dealer_delta": dealer_delta,
        "volatility_skew": skew,
        "source_id": str(uuid4()),
        "_required_fields": ["symbol", "timestamp", "option_chain"],
    }


def _compute_max_pain(
    call_oi: dict[float, float],
    put_oi: dict[float, float],
) -> float | None:
    strikes = sorted(set(call_oi) | set(put_oi))
    if not strikes:
        return None
    best_strike = None
    best_pain = None
    for settlement in strikes:
        pain = 0.0
        for k, oi in call_oi.items():
            pain += max(0.0, settlement - k) * oi
        for k, oi in put_oi.items():
            pain += max(0.0, k - settlement) * oi
        if best_pain is None or pain < best_pain:
            best_pain = pain
            best_strike = settlement
    return best_strike


def _compute_skew(chain: list[dict], spot: float | None) -> float | None:
    if not spot or spot <= 0:
        return None
    call_ivs = []
    put_ivs = []
    for row in chain:
        iv = row.get("mark_iv")
        strike = row.get("strike")
        if iv is None or strike is None:
            continue
        moneyness = strike / spot
        if row.get("option_type") == "call" and 1.05 <= moneyness <= 1.15:
            call_ivs.append(iv)
        if row.get("option_type") == "put" and 0.85 <= moneyness <= 0.95:
            put_ivs.append(iv)
    if not call_ivs or not put_ivs:
        return None
    return (sum(put_ivs) / len(put_ivs)) - (sum(call_ivs) / len(call_ivs))
