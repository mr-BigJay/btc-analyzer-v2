"""CoinEx collector — AI Research tab narrative (Ch.3 §3.8).

UI:  https://www.coinex.com/en/futures/btc-usdt  → tab "AI Research"
API: GET /res/ai-analysis/btc

Stores raw markdown article and parsed fields separately.
No market analysis is performed here — extraction only.
"""

from __future__ import annotations

import asyncio
import logging

from src.collectors.base import BaseCollector
from src.collectors.coinex.auth import CoinExAuth
from src.collectors.coinex.parser import parse_ai_research
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

        payload = await self.rest.fetch_ai_research()
        parsed = parse_ai_research(payload, symbol=settings.binance_symbol)
        narrative = NarrativeObject(
            bias=str(parsed.get("bias") or "neutral"),
            scenarios=list(parsed.get("scenarios") or []),
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
