"""Black-Scholes option pricing and Greeks."""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.stats import norm


@dataclass
class OptionGreeks:
    price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


def _d1d2(spot: float, strike: float, t: float, sigma: float, rate: float = 0.0) -> tuple[float, float]:
    if t <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        return 0.0, 0.0
    sqrt_t = math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma**2) * t) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    return d1, d2


def bs_greeks(
    spot: float,
    strike: float,
    t_years: float,
    sigma: float,
    is_call: bool,
    rate: float = 0.0,
) -> OptionGreeks:
    """Return USD option price and Greeks (per 1 contract, 1 BTC notional)."""
    if t_years <= 1e-8:
        intrinsic = max(spot - strike, 0) if is_call else max(strike - spot, 0)
        return OptionGreeks(intrinsic, 0.0, 0.0, 0.0, 0.0, 0.0)

    d1, d2 = _d1d2(spot, strike, t_years, sigma, rate)
    sqrt_t = math.sqrt(t_years)
    pdf_d1 = norm.pdf(d1)
    disc = math.exp(-rate * t_years)

    if is_call:
        price = spot * norm.cdf(d1) - strike * disc * norm.cdf(d2)
        delta = norm.cdf(d1)
        theta = (
            -(spot * pdf_d1 * sigma) / (2 * sqrt_t)
            - rate * strike * disc * norm.cdf(d2)
        ) / 365
        rho = strike * t_years * disc * norm.cdf(d2) / 100
    else:
        price = strike * disc * norm.cdf(-d2) - spot * norm.cdf(-d1)
        delta = norm.cdf(d1) - 1
        theta = (
            -(spot * pdf_d1 * sigma) / (2 * sqrt_t)
            + rate * strike * disc * norm.cdf(-d2)
        ) / 365
        rho = -strike * t_years * disc * norm.cdf(-d2) / 100

    gamma = pdf_d1 / (spot * sigma * sqrt_t)
    vega = spot * pdf_d1 * sqrt_t / 100

    return OptionGreeks(
        price=max(price, 0.0),
        delta=delta,
        gamma=gamma,
        theta=theta,
        vega=vega,
        rho=rho,
    )
