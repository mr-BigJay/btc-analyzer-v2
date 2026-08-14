"""CoinEx AI Research tab (chart AI report) via public web API."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.collector.base import BaseCollector
from src.config import settings
from src.db.models import CoinExAiResearchSnapshot

logger = logging.getLogger(__name__)


class CoinExAiResearchCollector(BaseCollector):
    source_name = "coinex_ai_research"

    def _coinex_res_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{settings.coinex_web_base.rstrip('/')}{path}"
        headers = {
            "platform": "web",
            "API-VERSION": "v2",
            "Accept-Language": settings.coinex_ai_lang,
        }
        import httpx

        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"CoinEx AI Research API error: {data.get('message', data)}")
        return data.get("data", {})

    def fetch_report(self, asset: str) -> dict[str, Any]:
        return self._coinex_res_get(f"/res/ai-analysis/{asset.lower()}")

    def collect(self, session: Session) -> int:
        asset = settings.coinex_ai_asset.lower()
        report = self.fetch_report(asset)

        summary = str(report.get("summary") or "").strip()
        core_content = str(report.get("core_content") or "").strip()
        content = str(report.get("content") or "").strip()
        if not summary and not core_content and not content:
            raise RuntimeError(f"CoinEx AI Research empty for {asset}")

        trends = report.get("trend") or {}
        trend_items = trends.get("trends") or []
        short_trend = ""
        long_trend = ""
        short_orientation = ""
        long_orientation = ""
        for item in trend_items:
            period = str(item.get("period") or "").lower()
            if period == "short":
                short_trend = str(item.get("content") or "")
                short_orientation = str(item.get("orientation") or "")
            elif period == "long":
                long_trend = str(item.get("content") or "")
                long_orientation = str(item.get("orientation") or "")

        created_at = report.get("created_at")
        if isinstance(created_at, (int, float)) and created_at > 0:
            published_at = self.ms_to_datetime(int(created_at * 1000))
        else:
            published_at = self.now()

        prev = session.execute(
            select(CoinExAiResearchSnapshot)
            .where(CoinExAiResearchSnapshot.asset == asset)
            .order_by(CoinExAiResearchSnapshot.collected_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if (
            prev
            and prev.summary == summary
            and prev.core_content == core_content
            and prev.short_orientation == short_orientation
            and prev.long_orientation == long_orientation
        ):
            logger.info("CoinEx AI Research %s unchanged — skip duplicate row", asset.upper())
            return 0

        row = CoinExAiResearchSnapshot(
            asset=asset,
            summary=summary,
            core_content=core_content,
            content=content,
            short_trend=short_trend,
            long_trend=long_trend,
            short_orientation=short_orientation,
            long_orientation=long_orientation,
            trend_summary=str(trends.get("summary") or core_content or summary),
            asset_tier=str(report.get("asset_tier") or ""),
            published_at=published_at,
            collected_at=self.now(),
        )
        session.add(row)
        session.commit()

        logger.info(
            "CoinEx AI Research %s: %s | short=%s long=%s",
            asset.upper(),
            summary[:80],
            short_trend or "n/a",
            long_trend or "n/a",
        )
        return 1
