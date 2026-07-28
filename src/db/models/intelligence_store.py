"""Chapter 11 analytical / decision / reporting storage (extends Ch.4).

Immutable append-oriented records for scores, AI decisions, reports, alerts,
spot/futures snapshots, volatility, and liquidity zones.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, utcnow


class SpotData(Base):
    """Spot market snapshot (Ch.11 §11.8)."""

    __tablename__ = "spot_data"
    __table_args__ = (Index("ix_spot_data_asset_timestamp", "asset_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    exchange_id: Mapped[int | None] = mapped_column(ForeignKey("exchanges.id"), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    vwap: Mapped[float | None] = mapped_column(Float, nullable=True)
    bid_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    cvd: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FuturesData(Base):
    """Futures / derivatives snapshot (Ch.11 §11.9)."""

    __tablename__ = "futures_data"
    __table_args__ = (Index("ix_futures_data_asset_timestamp", "asset_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    exchange_id: Mapped[int | None] = mapped_column(ForeignKey("exchanges.id"), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    open_interest: Mapped[float | None] = mapped_column(Float, nullable=True)
    oi_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    funding_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    long_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    short_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidation_long: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidation_short: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OptionsData(Base):
    """Options intelligence snapshot (Ch.11 §11.10) — complements options_analytics."""

    __tablename__ = "options_data"
    __table_args__ = (Index("ix_options_data_asset_timestamp", "asset_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    exchange_id: Mapped[int | None] = mapped_column(ForeignKey("exchanges.id"), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    call_oi: Mapped[float | None] = mapped_column(Float, nullable=True)
    put_oi: Mapped[float | None] = mapped_column(Float, nullable=True)
    pcr: Mapped[float | None] = mapped_column(Float, nullable=True)
    iv: Mapped[float | None] = mapped_column(Float, nullable=True)
    skew: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_pain: Mapped[float | None] = mapped_column(Float, nullable=True)
    gamma_exposure: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class VolatilityData(Base):
    """Volatility regime history (Ch.11 §11.11)."""

    __tablename__ = "volatility_data"
    __table_args__ = (Index("ix_volatility_data_asset_timestamp", "asset_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("symbols.id"), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    historical_volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    implied_volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    atr: Mapped[float | None] = mapped_column(Float, nullable=True)
    bollinger_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LiquidityZone(Base):
    """Liquidity zone map (Ch.11 §11.14)."""

    __tablename__ = "liquidity_zones"
    __table_args__ = (
        Index("ix_liquidity_zones_asset_timeframe", "asset_id", "timeframe"),
        Index("ix_liquidity_zones_price", "price_level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, default="1h", index=True)
    price_level: Mapped[float] = mapped_column(Float, nullable=False)
    zone_type: Mapped[str] = mapped_column(String(32), nullable=False)  # High/Low/FVG/OB/...
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    touched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MarketScore(Base):
    """Quantitative scoring history (Ch.11 §11.15)."""

    __tablename__ = "market_scores"
    __table_args__ = (Index("ix_market_scores_asset_timestamp", "asset_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("symbols.id"), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    bias_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mhi: Mapped[float | None] = mapped_column(Float, nullable=True)
    msi: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_bias: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weight_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    engine_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AIDecisionRecord(Base):
    """AI reasoning history (Ch.11 §11.16)."""

    __tablename__ = "ai_decisions"
    __table_args__ = (Index("ix_ai_decisions_asset_timestamp", "asset_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("symbols.id"), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    market_bias: Mapped[str | None] = mapped_column(String(32), nullable=True)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenarios: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    analysis_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReportRecord(Base):
    """Published report archive (Ch.11 §11.17)."""

    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_type_generated", "report_type", "generated_at"),
        Index("ix_reports_report_id", "report_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("symbols.id"), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    engine_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AlertRecord(Base):
    """System / market alerts (Ch.11 §11.18)."""

    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_type_timestamp", "alert_type", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FeatureStoreRecord(Base):
    """Validated engineered feature snapshots (Ch.13 §13.18)."""

    __tablename__ = "feature_store"
    __table_args__ = (
        Index("ix_feature_store_asset_timeframe_ts", "asset_id", "timeframe", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, default="1h", index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    feature_set_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    calculation_engine: Mapped[str | None] = mapped_column(String(32), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    data_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON FeatureSet
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
