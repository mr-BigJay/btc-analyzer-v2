"""Portfolio risk profile — PnL and Greeks across spot prices."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from src.options.models import OptionLeg, RiskPoint, RiskProfile, years_to_expiry
from src.options.pricing import bs_greeks


def position_from_deribit(pos: dict) -> OptionLeg | None:
    from src.options.models import parse_instrument

    parsed = parse_instrument(pos["instrument_name"])
    if not parsed:
        return None

    option_type, strike, expiry = parsed
    size = abs(float(pos.get("size", 0)))
    if size == 0:
        return None

    direction = pos.get("direction", "buy")
    side = "long" if direction == "buy" else "short"

    mark_iv = float(pos.get("mark_iv", 50))
    iv = mark_iv / 100 if mark_iv > 1 else mark_iv

    return OptionLeg(
        instrument_name=pos["instrument_name"],
        option_type=option_type,
        strike=strike,
        expiry=expiry,
        side=side,
        size=size,
        entry_price_btc=float(pos.get("average_price", pos.get("mark_price", 0))),
        iv=iv if iv > 0 else 0.5,
        underlying_at_entry=float(pos.get("index_price", pos.get("underlying_price", 63000))),
    )


def compute_risk_profile(
    legs: list[OptionLeg],
    spot_current: float,
    mode: str = "public",
    spot_range_pct: float = 0.35,
    steps: int = 80,
) -> RiskProfile:
    if not legs:
        return RiskProfile(mode=mode, spot_current=spot_current, points=[])

    now = datetime.now(timezone.utc)
    lo = spot_current * (1 - spot_range_pct)
    hi = spot_current * (1 + spot_range_pct)
    spots = np.linspace(lo, hi, steps)

    points: list[RiskPoint] = []
    for spot in spots:
        total_pnl = 0.0
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_rho = 0.0

        for leg in legs:
            t = years_to_expiry(leg.expiry, now)
            sigma = leg.iv if leg.iv > 0.01 else 0.5
            g = bs_greeks(float(spot), leg.strike, t, sigma, leg.is_call)

            # Deribit premium in BTC → USD at entry and at scenario spot
            entry_usd = leg.entry_price_btc * leg.underlying_at_entry
            scenario_usd = g.price  # BS price already in USD per BTC notional
            pnl_per = (scenario_usd - entry_usd) * leg.sign

            total_pnl += pnl_per * leg.size
            total_delta += g.delta * leg.sign * leg.size
            total_gamma += g.gamma * leg.sign * leg.size
            total_theta += g.theta * leg.sign * leg.size
            total_vega += g.vega * leg.sign * leg.size
            total_rho += g.rho * leg.sign * leg.size

        points.append(
            RiskPoint(
                spot=round(float(spot), 2),
                pnl=round(total_pnl, 2),
                delta=round(total_delta, 4),
                gamma=round(total_gamma, 6),
                theta=round(total_theta, 2),
                vega=round(total_vega, 2),
                rho=round(total_rho, 4),
            )
        )

    return RiskProfile(mode=mode, spot_current=spot_current, points=points, legs=legs)
