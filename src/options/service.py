"""Options service — reads automatically collected snapshots from DB."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.options.pipeline import OptionsPipeline

logger = logging.getLogger(__name__)


class OptionsService:
    def __init__(self) -> None:
        self.pipeline = OptionsPipeline()

    def collect(self, session: Session) -> int:
        return self.pipeline.run(session)

    def get_latest(self, session: Session) -> dict:
        data = self.pipeline.get_latest(session)
        if data:
            return data
        logger.info("No options snapshot — running collection...")
        self.pipeline.run(session)
        data = self.pipeline.get_latest(session)
        if not data:
            raise RuntimeError("Options collection produced no data")
        return data

    def get_screener(self, session: Session) -> dict:
        latest = self.get_latest(session)
        screener = latest["screener"]
        screener["auto"] = True
        screener["updated_at"] = latest["updated_at"]
        return screener

    def get_risk_profile(self, session: Session) -> dict:
        latest = self.get_latest(session)
        risk = latest["risk_profile"]
        risk["auto"] = True
        risk["updated_at"] = latest["updated_at"]
        return risk
