"""Options analytics service — screener + risk profile."""

from __future__ import annotations

import logging
from dataclasses import asdict

from src.config import settings
from src.options.deribit_client import DeribitClient
from src.options.risk_profile import compute_risk_profile, position_from_deribit
from src.options.screener import build_screener, rows_to_legs

logger = logging.getLogger(__name__)

HOURS_MAP = {"1h": 1, "4h": 4, "1d": 24}


class OptionsService:
    def __init__(self) -> None:
        self.client = DeribitClient()

    def get_screener(
        self,
        timeframe: str = "1d",
        min_size: float = 0.5,
        option_type: str | None = None,
        limit: int = 200,
    ) -> dict:
        hours = HOURS_MAP.get(timeframe, 24)
        trades = self.client.get_recent_trades(hours=hours, count=limit)
        rows, summary = build_screener(trades, min_size=min_size, option_type=option_type)
        spot = self.client.get_index_price()

        return {
            "spot_current": spot,
            "timeframe": timeframe,
            "summary": asdict(summary),
            "rows": [asdict(r) for r in rows[:100]],
        }

    def get_risk_profile(
        self,
        mode: str = "auto",
        timeframe: str = "1d",
        min_size: float = 1.0,
        instruments: list[str] | None = None,
    ) -> dict:
        spot = self.client.get_index_price()

        if instruments:
            from src.options.screener import trade_to_row

            legs_input = []
            for name in instruments:
                try:
                    ticker = self.client.get_ticker(name)
                    parsed_row = trade_to_row({
                        "instrument_name": name,
                        "price": ticker.get("mark_price", 0),
                        "amount": 1.0,
                        "contracts": 1.0,
                        "direction": "buy",
                        "index_price": ticker.get("index_price", spot),
                        "iv": ticker.get("mark_iv", 50),
                        "timestamp": ticker.get("timestamp", 0),
                    })
                    if parsed_row:
                        legs_input.append(parsed_row)
                except Exception:
                    logger.warning("Failed to fetch ticker for %s", name)
            legs = rows_to_legs(legs_input)
            profile = compute_risk_profile(legs, spot, mode="selected")
            return self._serialize_profile(profile)

        use_private = mode == "private" or (mode == "auto" and settings.deribit_configured)

        if use_private and settings.deribit_configured:
            try:
                positions = self.client.get_positions()
                legs = [leg for p in positions if (leg := position_from_deribit(p))]
                if legs:
                    profile = compute_risk_profile(legs, spot, mode="private")
                    return self._serialize_profile(profile)
            except Exception:
                logger.exception("Private positions fetch failed, falling back to public")

        hours = HOURS_MAP.get(timeframe, 24)
        trades = self.client.get_recent_trades(hours=hours, count=300)
        rows, summary = build_screener(trades, min_size=min_size)
        legs = rows_to_legs(rows[:30])
        profile = compute_risk_profile(legs, spot, mode="public")
        profile.summary = summary
        return self._serialize_profile(profile)

    @staticmethod
    def _serialize_profile(profile) -> dict:
        return {
            "mode": profile.mode,
            "spot_current": profile.spot_current,
            "legs_count": len(profile.legs),
            "summary": asdict(profile.summary) if profile.summary else None,
            "points": [asdict(p) for p in profile.points],
            "deribit_configured": settings.deribit_configured,
        }
