"""Deribit options collector (Ch.3 §3.7)."""

from __future__ import annotations

import asyncio
import logging

from src.collectors.base import BaseCollector
from src.collectors.deribit.auth import DeribitAuth
from src.collectors.deribit.parser import parse_option_chain
from src.collectors.deribit.rest import DeribitRestClient
from src.config import settings
from src.core import ModuleResult, ModuleStatus, OptionsObject
from src.storage.repository import CentralRepository

logger = logging.getLogger(__name__)


class DeribitOptionsCollector(BaseCollector[OptionsObject]):
    MODULE = "Deribit"
    MARKET = "Options"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        super().__init__(repository)
        self.auth = DeribitAuth()
        self.rest = DeribitRestClient(self.auth)
        self.currency = settings.deribit_currency

    def _rebuild_data(self, raw: dict) -> OptionsObject:
        fields = OptionsObject.__dataclass_fields__
        return OptionsObject(**{k: v for k, v in raw.items() if k in fields})

    async def collect_async(self) -> ModuleResult[OptionsObject]:
        instruments, summaries, index_price = await asyncio.gather(
            self.rest.get_instruments(self.currency),
            self.rest.get_book_summary(self.currency),
            self.rest.get_index_price(self.currency),
        )
        raw = parse_option_chain(instruments, summaries, index_price)
        options = OptionsObject(
            currency=self.currency,
            put_call_ratio=raw.get("put_call_ratio"),
            max_pain=raw.get("max_pain"),
            iv_rank=raw.get("iv_rank"),
            iv_percentile=raw.get("iv_percentile"),
            gamma_exposure=raw.get("gamma_exposure"),
            dealer_gamma=raw.get("dealer_gamma"),
            dealer_delta=raw.get("dealer_delta"),
            volatility_skew=raw.get("volatility_skew"),
            option_chain=raw.get("option_chain") or [],
            volume=raw.get("volume"),
            open_interest=raw.get("open_interest"),
        )
        return ModuleResult(
            module=self.MODULE,
            status=ModuleStatus.OK,
            confidence=1.0 if options.option_chain else 0.4,
            data=options,
            source_live=True,
            warning=None if options.option_chain else "Empty option chain",
        )

    def collect(self) -> ModuleResult[OptionsObject]:
        return asyncio.run(self.collect_async())
