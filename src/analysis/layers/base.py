"""Base analysis layer (Ch.6 §6.12 — modular, isolated, no AI)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.analysis.contracts import LayerResult, SignalBias, strength_from_confidence
from src.analysis.context import MarketContext


class BaseLayer(ABC):
    NAME: str = "Base"

    @abstractmethod
    def analyze(self, ctx: MarketContext) -> LayerResult:
        raise NotImplementedError

    def _result(
        self,
        signal: str,
        confidence: float,
        summary: str,
        *,
        timeframe: str,
        details: dict | None = None,
        tags: list[str] | None = None,
        data_quality: float = 1.0,
    ) -> LayerResult:
        conf = max(0.0, min(100.0, confidence * data_quality + (1 - data_quality) * 40))
        return LayerResult(
            layer=self.NAME,
            signal=signal,
            confidence=conf,
            strength=strength_from_confidence(conf).value,
            summary=summary,
            timeframe=timeframe,
            details=details or {},
            tags=tags or [],
            data_quality=data_quality,
        )

    @staticmethod
    def _clamp_signal_from_score(score: float, *, bull_thr: float = 0.25, bear_thr: float = -0.25) -> str:
        if score >= 0.55:
            return SignalBias.BULLISH.value
        if score >= bull_thr:
            return SignalBias.SLIGHTLY_BULLISH.value
        if score <= -0.55:
            return SignalBias.BEARISH.value
        if score <= bear_thr:
            return SignalBias.SLIGHTLY_BEARISH.value
        return SignalBias.NEUTRAL.value
