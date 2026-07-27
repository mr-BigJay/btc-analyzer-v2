"""Persistence for analytical, scoring, AI, and report intelligence (Ch.11 §11.25)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.db.access import assert_can_write
from src.db.models.intelligence_store import (
    AIDecisionRecord,
    AlertRecord,
    FuturesData,
    LiquidityZone,
    MarketScore,
    OptionsData,
    ReportRecord,
    SpotData,
    VolatilityData,
)
from src.db.models.technical import MarketStructure, TechnicalIndicator
from src.db.seed import resolve_exchange_id, resolve_symbol_id


def _ts(value: datetime | str | None = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _json(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


class IntelligenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append_spot(
        self,
        *,
        module: str,
        symbol: str,
        price: float | None = None,
        volume: float | None = None,
        vwap: float | None = None,
        bid_volume: float | None = None,
        ask_volume: float | None = None,
        cvd: float | None = None,
        exchange: str | None = None,
        timestamp: datetime | str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> SpotData:
        assert_can_write(module, "spot_data")
        asset_id = resolve_symbol_id(self.session, symbol)
        exchange_id = resolve_exchange_id(self.session, exchange) if exchange else None
        row = SpotData(
            asset_id=asset_id,
            exchange_id=exchange_id,
            timestamp=_ts(timestamp),
            price=price,
            volume=volume,
            vwap=vwap,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            cvd=cvd,
            payload=_json(payload),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_futures(
        self,
        *,
        module: str,
        symbol: str,
        open_interest: float | None = None,
        oi_value: float | None = None,
        funding_rate: float | None = None,
        long_ratio: float | None = None,
        short_ratio: float | None = None,
        liquidation_long: float | None = None,
        liquidation_short: float | None = None,
        exchange: str | None = None,
        timestamp: datetime | str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> FuturesData:
        assert_can_write(module, "futures_data")
        asset_id = resolve_symbol_id(self.session, symbol)
        exchange_id = resolve_exchange_id(self.session, exchange) if exchange else None
        row = FuturesData(
            asset_id=asset_id,
            exchange_id=exchange_id,
            timestamp=_ts(timestamp),
            open_interest=open_interest,
            oi_value=oi_value,
            funding_rate=funding_rate,
            long_ratio=long_ratio,
            short_ratio=short_ratio,
            liquidation_long=liquidation_long,
            liquidation_short=liquidation_short,
            payload=_json(payload),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_options(
        self,
        *,
        module: str,
        symbol: str,
        call_oi: float | None = None,
        put_oi: float | None = None,
        pcr: float | None = None,
        iv: float | None = None,
        skew: float | None = None,
        max_pain: float | None = None,
        gamma_exposure: float | None = None,
        exchange: str | None = None,
        timestamp: datetime | str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> OptionsData:
        assert_can_write(module, "options_data")
        asset_id = resolve_symbol_id(self.session, symbol)
        exchange_id = resolve_exchange_id(self.session, exchange) if exchange else None
        row = OptionsData(
            asset_id=asset_id,
            exchange_id=exchange_id,
            timestamp=_ts(timestamp),
            call_oi=call_oi,
            put_oi=put_oi,
            pcr=pcr,
            iv=iv,
            skew=skew,
            max_pain=max_pain,
            gamma_exposure=gamma_exposure,
            payload=_json(payload),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_volatility(
        self,
        *,
        module: str,
        symbol: str | None = None,
        historical_volatility: float | None = None,
        implied_volatility: float | None = None,
        atr: float | None = None,
        bollinger_width: float | None = None,
        volatility_state: str | None = None,
        timestamp: datetime | str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> VolatilityData:
        assert_can_write(module, "volatility_data")
        asset_id = resolve_symbol_id(self.session, symbol) if symbol else None
        row = VolatilityData(
            asset_id=asset_id,
            timestamp=_ts(timestamp),
            historical_volatility=historical_volatility,
            implied_volatility=implied_volatility,
            atr=atr,
            bollinger_width=bollinger_width,
            volatility_state=volatility_state,
            payload=_json(payload),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_liquidity_zone(
        self,
        *,
        module: str,
        symbol: str,
        price_level: float,
        zone_type: str,
        strength: float = 0.0,
        touched: bool = False,
        timeframe: str = "1h",
        timestamp: datetime | str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> LiquidityZone:
        assert_can_write(module, "liquidity_zones")
        asset_id = resolve_symbol_id(self.session, symbol)
        row = LiquidityZone(
            asset_id=asset_id,
            timeframe=timeframe,
            price_level=float(price_level),
            zone_type=zone_type,
            strength=float(strength),
            touched=bool(touched),
            timestamp=_ts(timestamp),
            payload=_json(payload),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_technical(
        self,
        *,
        module: str,
        symbol: str,
        timeframe: str,
        rsi: float | None = None,
        macd: float | None = None,
        adx: float | None = None,
        atr: float | None = None,
        signal: str | None = None,
        ema_values: dict[str, Any] | None = None,
        ema20: float | None = None,
        ema50: float | None = None,
        ema100: float | None = None,
        ema200: float | None = None,
        payload: dict[str, Any] | None = None,
        engine_version: str | None = None,
        calculation_version: str | None = None,
        timestamp: datetime | str | None = None,
    ) -> TechnicalIndicator:
        assert_can_write(module, "technical_indicators")
        symbol_id = resolve_symbol_id(self.session, symbol)
        emas = ema_values or {}
        row = TechnicalIndicator(
            symbol_id=symbol_id,
            timeframe=timeframe,
            timestamp=_ts(timestamp),
            rsi=rsi,
            macd=macd,
            adx=adx,
            atr=atr,
            signal=signal,
            ema20=ema20 if ema20 is not None else _f(emas.get("ema20") or emas.get("20")),
            ema50=ema50 if ema50 is not None else _f(emas.get("ema50") or emas.get("50")),
            ema100=ema100 if ema100 is not None else _f(emas.get("ema100") or emas.get("100")),
            ema200=ema200 if ema200 is not None else _f(emas.get("ema200") or emas.get("200")),
            ema_values=_json(emas) if emas else None,
            payload=_json(payload),
            engine_version=engine_version,
            calculation_version=calculation_version,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_structure(
        self,
        *,
        module: str,
        symbol: str,
        timeframe: str,
        trend: str | None = None,
        higher_high: bool | None = None,
        higher_low: bool | None = None,
        lower_high: bool | None = None,
        lower_low: bool | None = None,
        bos: bool | None = None,
        choch: bool | None = None,
        hh: float | None = None,
        hl: float | None = None,
        lh: float | None = None,
        ll: float | None = None,
        timestamp: datetime | str | None = None,
    ) -> MarketStructure:
        assert_can_write(module, "market_structure")
        symbol_id = resolve_symbol_id(self.session, symbol)
        row = MarketStructure(
            symbol_id=symbol_id,
            timeframe=timeframe,
            timestamp=_ts(timestamp),
            trend=trend or "neutral",
            higher_high=higher_high,
            higher_low=higher_low,
            lower_high=lower_high,
            lower_low=lower_low,
            bos=bos,
            choch=choch,
            hh=hh,
            hl=hl,
            lh=lh,
            ll=ll,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_market_score(
        self,
        *,
        module: str,
        symbol: str,
        bias_score: float,
        confidence_score: float,
        risk_score: float,
        mhi: float | None = None,
        msi: float | None = None,
        data_quality: float | None = None,
        market_bias: str | None = None,
        weight_regime: str | None = None,
        payload: dict[str, Any] | None = None,
        engine_version: str | None = None,
        calculation_version: str | None = None,
        timestamp: datetime | str | None = None,
    ) -> MarketScore:
        assert_can_write(module, "market_scores")
        asset_id = resolve_symbol_id(self.session, symbol)
        row = MarketScore(
            asset_id=asset_id,
            timestamp=_ts(timestamp),
            bias_score=float(bias_score),
            confidence_score=float(confidence_score),
            risk_score=float(risk_score),
            mhi=mhi,
            msi=msi,
            data_quality=data_quality,
            market_bias=market_bias,
            weight_regime=weight_regime,
            payload=_json(payload),
            engine_version=engine_version,
            calculation_version=calculation_version,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_ai_decision(
        self,
        *,
        module: str,
        symbol: str,
        market_bias: str | None,
        narrative: str | None,
        confidence: float | None,
        scenarios: dict[str, Any] | list[Any] | None = None,
        reasoning: dict[str, Any] | list[Any] | None = None,
        risk_level: str | None = None,
        analysis_fingerprint: str | None = None,
        payload: dict[str, Any] | None = None,
        engine_version: str | None = None,
        ai_version: str | None = None,
        timestamp: datetime | str | None = None,
    ) -> AIDecisionRecord:
        assert_can_write(module, "ai_decisions")
        asset_id = resolve_symbol_id(self.session, symbol)
        row = AIDecisionRecord(
            asset_id=asset_id,
            timestamp=_ts(timestamp),
            market_bias=market_bias,
            narrative=narrative,
            scenarios=_json(scenarios if scenarios is not None else {}),
            reasoning=_json(reasoning if reasoning is not None else {}),
            confidence=float(confidence) if confidence is not None else None,
            risk_level=risk_level,
            analysis_fingerprint=analysis_fingerprint,
            payload=_json(payload),
            engine_version=engine_version,
            ai_version=ai_version,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_report(
        self,
        *,
        module: str,
        report_id: str,
        report_type: str,
        content: dict[str, Any] | str,
        symbol: str | None = None,
        engine_version: str | None = None,
        ai_version: str | None = None,
        schema_version: str | None = None,
        published: bool = True,
        generated_at: datetime | str | None = None,
    ) -> ReportRecord:
        assert_can_write(module, "reports")
        asset_id = resolve_symbol_id(self.session, symbol) if symbol else None
        row = ReportRecord(
            report_id=report_id,
            report_type=report_type,
            generated_at=_ts(generated_at),
            asset_id=asset_id,
            content=_json(content) or "{}",
            engine_version=engine_version,
            ai_version=ai_version,
            schema_version=schema_version,
            published=published,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def append_alert(
        self,
        *,
        module: str,
        alert_type: str,
        severity: str,
        message: str,
        symbol: str | None = None,
        delivered: bool = False,
        payload: dict[str, Any] | None = None,
        timestamp: datetime | str | None = None,
    ) -> AlertRecord:
        assert_can_write(module, "alerts")
        row = AlertRecord(
            alert_type=alert_type,
            severity=severity,
            message=message,
            symbol=(symbol or "").upper() or None,
            timestamp=_ts(timestamp),
            delivered=delivered,
            payload=_json(payload),
        )
        self.session.add(row)
        self.session.flush()
        return row


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
