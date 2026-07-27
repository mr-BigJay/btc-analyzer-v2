"""Standardized database data packages (Ch.11 §11.26)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.db.models import (
    AIDecisionRecord,
    FundingRate,
    MarketCandle,
    MarketScore,
    OpenInterest,
    OptionsAnalyticsSnapshot,
    Symbol,
    TechnicalIndicator,
)
from src.db.models.intelligence_store import FuturesData, SpotData
from src.db.session import get_session
from src.db.seed import resolve_symbol_id


def _row_dict(obj: Any, fields: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in fields:
        val = getattr(obj, f, None)
        if isinstance(val, datetime):
            val = val.isoformat()
        out[f] = val
    return out


def build_data_package(*, symbol: str = "BTCUSDT", timestamp: datetime | None = None) -> dict[str, Any]:
    """Assemble {asset, timestamp, market_data, analysis, scores, decision}."""
    ts = timestamp or datetime.now(timezone.utc)
    session = get_session()
    try:
        symbol_id = resolve_symbol_id(session, symbol)
        sym = session.query(Symbol).filter_by(id=symbol_id).one()

        candle = (
            session.query(MarketCandle)
            .filter_by(symbol_id=symbol_id)
            .order_by(MarketCandle.timestamp.desc())
            .first()
        )
        funding = (
            session.query(FundingRate)
            .filter_by(symbol_id=symbol_id)
            .order_by(FundingRate.timestamp.desc())
            .first()
        )
        oi = (
            session.query(OpenInterest)
            .filter_by(symbol_id=symbol_id)
            .order_by(OpenInterest.timestamp.desc())
            .first()
        )
        spot = (
            session.query(SpotData)
            .filter_by(asset_id=symbol_id)
            .order_by(SpotData.timestamp.desc())
            .first()
        )
        futures = (
            session.query(FuturesData)
            .filter_by(asset_id=symbol_id)
            .order_by(FuturesData.timestamp.desc())
            .first()
        )
        options = (
            session.query(OptionsAnalyticsSnapshot)
            .filter_by(symbol_id=symbol_id)
            .order_by(OptionsAnalyticsSnapshot.timestamp.desc())
            .first()
        )
        tech = (
            session.query(TechnicalIndicator)
            .filter_by(symbol_id=symbol_id)
            .order_by(TechnicalIndicator.timestamp.desc())
            .first()
        )
        score = (
            session.query(MarketScore)
            .filter_by(asset_id=symbol_id)
            .order_by(MarketScore.timestamp.desc())
            .first()
        )
        decision = (
            session.query(AIDecisionRecord)
            .filter_by(asset_id=symbol_id)
            .order_by(AIDecisionRecord.timestamp.desc())
            .first()
        )

        market_data: dict[str, Any] = {}
        if candle:
            market_data["candle"] = _row_dict(candle, ["timestamp", "open", "high", "low", "close", "volume", "timeframe"])
        if funding:
            market_data["funding_rate"] = _row_dict(funding, ["timestamp", "funding_rate", "predicted_rate"])
        if oi:
            market_data["open_interest"] = _row_dict(oi, ["timestamp", "oi", "oi_value"])
        if spot:
            market_data["spot"] = _row_dict(spot, ["timestamp", "price", "volume", "vwap", "cvd"])
        if futures:
            market_data["futures"] = _row_dict(
                futures,
                [
                    "timestamp",
                    "open_interest",
                    "oi_value",
                    "funding_rate",
                    "long_ratio",
                    "short_ratio",
                    "liquidation_long",
                    "liquidation_short",
                ],
            )
        if options:
            market_data["options"] = _row_dict(
                options,
                ["timestamp", "put_call_ratio", "max_pain", "iv_rank", "gamma_exposure", "volatility_skew"],
            )

        analysis: dict[str, Any] = {}
        if tech:
            analysis["technical"] = _row_dict(
                tech, ["timestamp", "timeframe", "rsi", "macd", "atr", "adx", "signal", "ema20", "ema50"]
            )

        scores: dict[str, Any] = {}
        if score:
            scores = _row_dict(
                score,
                [
                    "timestamp",
                    "bias_score",
                    "confidence_score",
                    "risk_score",
                    "mhi",
                    "msi",
                    "data_quality",
                    "market_bias",
                ],
            )

        decision_obj: dict[str, Any] = {}
        if decision:
            decision_obj = _row_dict(
                decision,
                ["timestamp", "market_bias", "narrative", "confidence", "risk_level", "analysis_fingerprint"],
            )
            for key in ("scenarios", "reasoning"):
                raw = getattr(decision, key, None)
                if raw:
                    try:
                        decision_obj[key] = json.loads(raw)
                    except Exception:  # noqa: BLE001
                        decision_obj[key] = raw

        return {
            "asset": sym.symbol,
            "asset_id": sym.id,
            "public_id": getattr(sym, "public_id", None),
            "timestamp": ts.isoformat(),
            "market_data": market_data,
            "analysis": analysis,
            "scores": scores,
            "decision": decision_obj,
        }
    finally:
        session.close()
