from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class OptionLeg:
    instrument_name: str
    option_type: str  # call | put
    strike: float
    expiry: datetime
    side: str  # long | short
    size: float
    entry_price_btc: float
    iv: float
    underlying_at_entry: float
    entry_time: datetime | None = None

    @property
    def is_call(self) -> bool:
        return self.option_type == "call"

    @property
    def sign(self) -> float:
        return 1.0 if self.side == "long" else -1.0


@dataclass
class ScreenerRow:
    instrument_name: str
    option_type: str
    expiry_utc: str
    strike: float
    underlying: float
    price_btc: float
    iv: float
    side: str
    size: float
    entry_price_btc: float
    entry_value_usd: float
    entry_date: str


@dataclass
class ScreenerSummary:
    position_count: int
    total_size: float
    total_entry_value_usd: float


@dataclass
class RiskPoint:
    spot: float
    pnl: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


@dataclass
class RiskProfile:
    mode: str
    spot_current: float
    points: list[RiskPoint]
    legs: list[OptionLeg] = field(default_factory=list)
    summary: ScreenerSummary | None = None


INSTRUMENT_RE = re.compile(r"^BTC-(\d{1,2}[A-Z]{3}\d{2})-(\d+(?:\.\d+)?)-([CP])$")
EXPIRY_RE = re.compile(r"^(\d{1,2})([A-Z]{3})(\d{2})$")
MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def parse_instrument(name: str) -> tuple[str, float, datetime] | None:
    m = INSTRUMENT_RE.match(name)
    if not m:
        return None
    expiry_str, strike_str, cp = m.groups()
    em = EXPIRY_RE.match(expiry_str)
    if not em:
        return None
    day, mon, yr = em.groups()
    expiry = datetime(int(f"20{yr}"), MONTHS[mon], int(day), 8, 0, tzinfo=timezone.utc)
    option_type = "call" if cp == "C" else "put"
    return option_type, float(strike_str), expiry


def years_to_expiry(expiry: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    return max((expiry - now).total_seconds() / (365.25 * 24 * 3600), 1e-8)
