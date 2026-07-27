"""CoinEx collector — daily textual market analysis (Ch.3 §3.8)."""

from __future__ import annotations

import asyncio
import logging

from src.collectors.base import BaseCollector
from src.collectors.coinex.auth import CoinExAuth
from src.collectors.coinex.parser import parse_narrative
from src.collectors.coinex.rest import CoinExRestClient
from src.config import settings
from src.core import ModuleResult, ModuleStatus, NarrativeObject
from src.storage.repository import CentralRepository

logger = logging.getLogger(__name__)


class CoinExCollector(BaseCollector[NarrativeObject]):
    MODULE = "CoinEx"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        super().__init__(repository)
        self.auth = CoinExAuth()
        self.rest = CoinExRestClient(self.auth)

    def _rebuild_data(self, raw: dict) -> NarrativeObject:
        fields = NarrativeObject.__dataclass_fields__
        return NarrativeObject(**{k: v for k, v in raw.items() if k in fields})

    async def collect_async(self) -> ModuleResult[NarrativeObject]:
        if not settings.coinex_enabled:
            return ModuleResult(
                module=self.MODULE,
                status=ModuleStatus.SKIPPED,
                confidence=0.0,
                data=NarrativeObject(),
                warning="CoinEx disabled",
                source_live=False,
            )

        raw_text = ""
        try:
            # Prefer JSON if path looks like API; fall back to text
            if self.rest.analysis_path.endswith(".json") or "api" in self.rest.analysis_path:
                data = await self.rest.fetch_analysis_json()
                raw_text = data if isinstance(data, str) else __import__("json").dumps(data, ensure_ascii=False)
            else:
                raw_text = await self.rest.fetch_analysis_raw()
        except Exception as exc:  # noqa: BLE001
            # Fall through to empty parse — resilient wrapper handles cache
            raise RuntimeError(f"CoinEx fetch failed: {exc}") from exc

        parsed = parse_narrative(raw_text, symbol=settings.binance_symbol)
        narrative = NarrativeObject(
            bias=str(parsed.get("bias") or "neutral"),
            scenarios=[],
            support_levels=list(parsed.get("support_levels") or []),
            resistance_levels=list(parsed.get("resistance_levels") or []),
            summary=str(parsed.get("summary") or ""),
            bullish_arguments=list(parsed.get("bullish_arguments") or []),
            bearish_arguments=list(parsed.get("bearish_arguments") or []),
            raw_article=parsed.get("raw_article"),
        )
        conf = parsed.get("confidence_score")
        confidence = float(conf) if conf is not None else (0.7 if narrative.summary else 0.3)
        return ModuleResult(
            module=self.MODULE,
            status=ModuleStatus.OK,
            confidence=confidence,
            data=narrative,
            source_live=True,
            warning=parsed.get("warning"),
        )

    def collect(self) -> ModuleResult[NarrativeObject]:
        return asyncio.run(self.collect_async())
