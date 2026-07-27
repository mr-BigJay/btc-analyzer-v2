"""Data Collection Engine — orchestrates Collect → Validate → Normalize → Cache → DB (Ch.3).

Never performs market analysis.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.collectors.binance import BinanceFuturesCollector
from src.collectors.bitunix import BitunixCollector
from src.collectors.coinex import CoinExCollector
from src.collectors.deribit import DeribitOptionsCollector
from src.config import settings
from src.core import ModuleResult, ModuleStatus
from src.pipeline.normalization import DataNormalizer, NormalizedSnapshot
from src.pipeline.quality import DataQualityGate, QualityAssessment
from src.pipeline.validation import DataValidator, ValidationReport
from src.storage.repository import CentralRepository

logger = logging.getLogger(__name__)


@dataclass
class CollectionCycleResult:
    ok: bool
    snapshot: NormalizedSnapshot | None
    results: dict[str, ModuleResult] = field(default_factory=dict)
    validations: dict[str, ValidationReport] = field(default_factory=dict)
    quality: dict[str, QualityAssessment] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "validations": {
                k: {
                    "ok": v.ok,
                    "issues": [asdict(i) for i in v.issues],
                    "rejected_count": v.rejected_count,
                }
                for k, v in self.validations.items()
            },
            "quality": {k: v.to_dict() for k, v in self.quality.items()},
            "warnings": self.warnings,
            "collected_at": self.collected_at,
        }


class DataCollectionEngine:
    """Independent collectors → validate → normalize → cache → append-only DB."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.validator = DataValidator()
        self.normalizer = DataNormalizer()
        self.quality = DataQualityGate()
        self.binance = BinanceFuturesCollector(self.repository)
        self.deribit = DeribitOptionsCollector(self.repository)
        self.coinex = CoinExCollector(self.repository)
        self.bitunix = BitunixCollector(self.repository)

    async def run_minute_cycle(self) -> CollectionCycleResult:
        """1-minute job: price, funding, open interest (+ Bitunix validation snapshot)."""
        tasks = {}
        if settings.binance_futures_enabled:
            tasks["binance"] = self.binance.collect_async()
        if settings.bitunix_enabled:
            tasks["bitunix"] = self.bitunix.collect_async()

        gathered = await asyncio.gather(
            *[self._safe(name, coro) for name, coro in tasks.items()],
        )
        live_results = {name: result for name, result in gathered}

        # Resilient fallback for failures (cache only — avoid nested asyncio.run)
        results: dict[str, ModuleResult] = {}
        for name, result in live_results.items():
            if result.status == ModuleStatus.SKIPPED:
                results[name] = result
            elif result.status in {ModuleStatus.OK, ModuleStatus.DEGRADED} and result.data is not None:
                self.repository.save_snapshot(result.module, result.to_dict())
                self.repository.cache_hot(result.module, result.to_dict())
                results[name] = result
            else:
                collector = {"binance": self.binance, "bitunix": self.bitunix}[name]
                results[name] = collector.fallback_from_cache(result.warning or "live failed")

        return self._finalize(results, persist_futures=True)

    async def run_options_cycle(self) -> CollectionCycleResult:
        """1-hour job: option chain update."""
        if not settings.deribit_enabled:
            return CollectionCycleResult(ok=True, snapshot=NormalizedSnapshot(), warnings=["Deribit disabled"])

        try:
            result = await self.deribit.collect_async()
            if result.status == ModuleStatus.OK:
                self.repository.save_snapshot(result.module, result.to_dict())
                self.repository.cache_hot(result.module, result.to_dict())
            elif result.status == ModuleStatus.ERROR:
                result = self.deribit.fallback_from_cache(result.warning)
        except Exception as exc:  # noqa: BLE001
            result = self.deribit.fallback_from_cache(exc)

        return self._finalize({"deribit": result}, persist_options=True)

    async def run_narrative_cycle(self) -> CollectionCycleResult:
        """Daily narrative fetch (also usable on demand)."""
        try:
            result = await self.coinex.collect_async()
            if result.status == ModuleStatus.OK:
                self.repository.save_snapshot(result.module, result.to_dict())
                self.repository.cache_hot(result.module, result.to_dict())
            elif result.status == ModuleStatus.ERROR:
                result = self.coinex.fallback_from_cache(result.warning)
        except Exception as exc:  # noqa: BLE001
            result = self.coinex.fallback_from_cache(exc)
        return self._finalize({"coinex": result}, persist_narrative=True)

    async def run_technical_cache_refresh(self) -> CollectionCycleResult:
        """5-minute technical OHLCV cache refresh (data only — no analysis)."""
        warnings: list[str] = []
        try:
            ohlcv = await self.binance.collect_ohlcv_async(interval="1h", limit=200)
            spot = await self.binance.collect_spot_async()
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": settings.binance_symbol,
                "timeframe": "1h",
                "exchange": "binance",
                "ohlcv": ohlcv,
                "spot": spot,
                "source_id": f"tech-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            }
            report = self.validator.validate("technical_cache", {
                **record,
                "status": "OK",
                "_required_fields": ["symbol", "timestamp"],
            })
            if report.ok or all(i.severity == "warning" for i in report.issues):
                self.repository.append_technical_cache(record)
                self.repository.memory.set("technical_cache_1h", record)
                from src.storage.redis_cache import redis_cache

                redis_cache.set("technical_cache_1h", record, ttl_sec=600)
            else:
                warnings.append("technical_cache validation failed — not stored")
            snap = self.normalizer.normalize({"spot": spot})
            return CollectionCycleResult(ok=True, snapshot=snap, warnings=warnings)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Technical cache refresh failed: %s", exc)
            return CollectionCycleResult(ok=False, snapshot=None, warnings=[str(exc)])

    async def run_full_cycle(self) -> CollectionCycleResult:
        """Collect all enabled sources once (manual / bootstrap)."""
        parts = await asyncio.gather(
            self.run_minute_cycle(),
            self.run_options_cycle(),
            self.run_narrative_cycle(),
            return_exceptions=True,
        )
        warnings: list[str] = []
        results: dict[str, ModuleResult] = {}
        for part in parts:
            if isinstance(part, Exception):
                warnings.append(str(part))
                continue
            results.update(part.results)
            warnings.extend(part.warnings)
        return self._finalize(
            results,
            persist_futures=True,
            persist_options=True,
            persist_narrative=True,
            extra_warnings=warnings,
        )

    def run_full_cycle_sync(self) -> CollectionCycleResult:
        return asyncio.run(self.run_full_cycle())

    def run_minute_cycle_sync(self) -> CollectionCycleResult:
        return asyncio.run(self.run_minute_cycle())

    def run_options_cycle_sync(self) -> CollectionCycleResult:
        return asyncio.run(self.run_options_cycle())

    def run_technical_cache_sync(self) -> CollectionCycleResult:
        return asyncio.run(self.run_technical_cache_refresh())

    def run_narrative_cycle_sync(self) -> CollectionCycleResult:
        return asyncio.run(self.run_narrative_cycle())

    async def _safe(self, name: str, coro) -> tuple[str, ModuleResult]:
        try:
            return name, await coro
        except Exception as exc:  # noqa: BLE001
            logger.warning("Collector %s failed: %s", name, exc)
            return name, ModuleResult(
                module=name,
                status=ModuleStatus.ERROR,
                confidence=0.0,
                warning=str(exc),
                source_live=False,
                error_code=type(exc).__name__,
            )

    def _finalize(
        self,
        results: dict[str, ModuleResult],
        *,
        persist_futures: bool = False,
        persist_options: bool = False,
        persist_narrative: bool = False,
        extra_warnings: list[str] | None = None,
    ) -> CollectionCycleResult:
        warnings = list(extra_warnings or [])
        validations: dict[str, ValidationReport] = {}
        quality: dict[str, QualityAssessment] = {}
        validated_payloads: dict[str, dict] = {}

        for name, result in results.items():
            data = result.data
            if data is None:
                warnings.append(f"{name}: no data")
                continue
            payload = asdict(data) if hasattr(data, "__dataclass_fields__") else dict(data)
            payload.setdefault("exchange", name.lower())
            payload.setdefault("timestamp", result.timestamp)
            # Do not inject ModuleStatus into API status field (Ch.3 §3.10 checks HTTP/API status separately)
            if result.source_live and result.status == ModuleStatus.OK:
                payload.setdefault("api_status", "OK")
            if "symbol" not in payload:
                payload["symbol"] = settings.binance_symbol

            report = self.validator.validate(name, payload)
            validations[name] = report
            hard_errors = [i for i in report.issues if i.severity == "error"]
            if hard_errors:
                warnings.append(f"{name}: validation rejected ({len(hard_errors)} errors)")
                # Invalid records must never enter the database
                continue

            q = self.quality.assess(payload, source_live=result.source_live)
            if result.status == ModuleStatus.DEGRADED:
                q.degraded = True
                q.confidence = min(q.confidence, result.confidence)
                q.reasons.append("module degraded")
            quality[name] = q
            if q.degraded:
                warnings.append(f"{name}: quality degraded conf={q.confidence:.2f}")
            validated_payloads[name] = payload

            # Append-only persistence
            try:
                if persist_futures and name == "binance":
                    self.repository.append_futures(self.normalizer.normalize_record("binance", payload).to_dict() | payload)
                    if payload.get("order_book"):
                        self.repository.append_orderbook(
                            {
                                "timestamp": payload.get("timestamp"),
                                "symbol": payload.get("symbol"),
                                "exchange": "binance",
                                "spread": None,
                                "order_book": payload.get("order_book"),
                                "source_id": payload.get("source_id"),
                            }
                        )
                if persist_options and name == "deribit":
                    self.repository.append_options(self.normalizer.normalize_record("deribit", payload).to_dict() | payload)
                if persist_narrative and name == "coinex":
                    self.repository.append_coinex_analysis(payload)
                if name == "bitunix" and payload.get("order_book"):
                    self.repository.append_orderbook(
                        {
                            "timestamp": payload.get("timestamp"),
                            "symbol": payload.get("symbol"),
                            "exchange": "bitunix",
                            "spread": payload.get("spread"),
                            "order_book": payload.get("order_book"),
                            "source_id": payload.get("source_id"),
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Persist failed for %s", name)
                warnings.append(f"{name}: persist error {exc}")

        snapshot = self.normalizer.normalize(validated_payloads) if validated_payloads else None
        ok = bool(validated_payloads) and not any(
            r.status == ModuleStatus.ERROR and name in {"binance", "deribit"}
            for name, r in results.items()
        )
        return CollectionCycleResult(
            ok=ok,
            snapshot=snapshot,
            results=results,
            validations=validations,
            quality=quality,
            warnings=warnings,
        )
