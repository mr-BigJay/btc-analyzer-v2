"""Build options screener from Deribit trades."""

from __future__ import annotations

from datetime import datetime, timezone

from src.options.models import ScreenerRow, ScreenerSummary, parse_instrument


def trade_to_row(trade: dict) -> ScreenerRow | None:
    parsed = parse_instrument(trade["instrument_name"])
    if not parsed:
        return None

    option_type, strike, expiry = parsed
    price_btc = float(trade["price"])
    size = float(trade.get("contracts", trade.get("amount", 0)))
    underlying = float(trade.get("index_price", 0))
    iv = float(trade.get("iv", 0))
    side = "long" if trade.get("direction") == "buy" else "short"
    entry_value_usd = price_btc * size * underlying

    ts = datetime.fromtimestamp(trade["timestamp"] / 1000, tz=timezone.utc)

    return ScreenerRow(
        instrument_name=trade["instrument_name"],
        option_type=option_type,
        expiry_utc=expiry.strftime("%Y-%m-%d %H:%M"),
        strike=strike,
        underlying=underlying,
        price_btc=price_btc,
        iv=iv,
        side=side,
        size=size,
        entry_price_btc=price_btc,
        entry_value_usd=round(entry_value_usd, 2),
        entry_date=ts.strftime("%Y-%m-%d %H:%M:%S"),
    )


def build_screener(
    trades: list[dict],
    min_size: float = 0.0,
    option_type: str | None = None,
) -> tuple[list[ScreenerRow], ScreenerSummary]:
    rows: list[ScreenerRow] = []
    for trade in trades:
        row = trade_to_row(trade)
        if not row:
            continue
        if row.size < min_size:
            continue
        if option_type and row.option_type != option_type:
            continue
        rows.append(row)

    rows.sort(key=lambda r: r.entry_value_usd, reverse=True)

    summary = ScreenerSummary(
        position_count=len(rows),
        total_size=round(sum(r.size for r in rows), 2),
        total_entry_value_usd=round(sum(r.entry_value_usd for r in rows), 2),
    )
    return rows, summary


def rows_to_legs(rows: list[ScreenerRow]) -> list:
    from src.options.models import OptionLeg

    legs = []
    for r in rows:
        parsed = parse_instrument(r.instrument_name)
        if not parsed:
            continue
        option_type, strike, expiry = parsed
        legs.append(
            OptionLeg(
                instrument_name=r.instrument_name,
                option_type=option_type,
                strike=strike,
                expiry=expiry,
                side=r.side,
                size=r.size,
                entry_price_btc=r.entry_price_btc,
                iv=r.iv / 100 if r.iv > 1 else r.iv,
                underlying_at_entry=r.underlying,
            )
        )
    return legs
