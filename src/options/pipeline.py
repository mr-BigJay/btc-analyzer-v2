"""Automatic options data collection and persistence."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.config import settings
from src.db.models import OptionsSnapshot
from src.options.deribit_client import DeribitClient
from src.options.risk_profile import compute_risk_profile, position_from_deribit
from src.options.screener import build_screener, rows_to_legs

logger = logging.getLogger(__name__)


class OptionsPipeline:
    """Collects Deribit data, computes risk profile, saves to DB — fully automatic."""

    def __init__(self) -> None:
        self.client = DeribitClient()

    def run(self, session: Session) -> int:
        spot = self.client.get_index_price()
        mode = "public"
        legs = []
        summary = None
        screener_rows = []

        if settings.deribit_configured:
            try:
                positions = self.client.get_positions()
                legs = [leg for p in positions if (leg := position_from_deribit(p))]
                if legs:
                    mode = "private"
            except Exception:
                logger.exception("Private positions failed, using public trades")

        trades = self.client.get_recent_trades(hours=24, count=500)
        screener_rows, summary = build_screener(trades, min_size=settings.options_min_size)

        if mode == "public":
            legs = rows_to_legs(screener_rows[: settings.options_top_legs])

        profile = compute_risk_profile(legs, spot, mode=mode)
        if mode == "public":
            profile.summary = summary

        screener_data = {
            "spot_current": spot,
            "mode": mode,
            "timeframe": "1d",
            "summary": asdict(summary) if summary else None,
            "rows": [asdict(r) for r in screener_rows[:100]],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        risk_data = {
            "mode": profile.mode,
            "spot_current": profile.spot_current,
            "legs_count": len(profile.legs),
            "summary": asdict(profile.summary) if profile.summary else None,
            "points": [asdict(p) for p in profile.points],
            "deribit_configured": settings.deribit_configured,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        snapshot = OptionsSnapshot(
            mode=mode,
            spot_current=spot,
            screener_payload=json.dumps(screener_data, ensure_ascii=False),
            risk_payload=json.dumps(risk_data, ensure_ascii=False),
        )
        session.add(snapshot)
        session.commit()
        logger.info("Options snapshot saved: mode=%s legs=%d", mode, len(legs))
        return 1

    @staticmethod
    def get_latest(session: Session) -> dict | None:
        row = session.execute(
            select(OptionsSnapshot).order_by(desc(OptionsSnapshot.created_at)).limit(1)
        ).scalar_one_or_none()
        if not row:
            return None
        screener = json.loads(row.screener_payload)
        risk = json.loads(row.risk_payload)
        return {
            "screener": screener,
            "risk_profile": risk,
            "mode": row.mode,
            "spot_current": row.spot_current,
            "updated_at": row.created_at.isoformat(),
        }
