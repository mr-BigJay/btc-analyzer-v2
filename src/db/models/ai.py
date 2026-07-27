"""AI Analysis domain (Ch.4 §4.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, utcnow


class CoinExAnalysis(Base):
    __tablename__ = "coinex_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    bullish_points: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    bearish_points: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    support_levels: Mapped[str | None] = mapped_column(Text, nullable=True)
    resistance_levels: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias: Mapped[str | None] = mapped_column(String(16), nullable=True)
    symbol_id: Mapped[int | None] = mapped_column(ForeignKey("symbols.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DailyOutlook(Base):
    __tablename__ = "daily_outlook"
    __table_args__ = (Index("ix_daily_outlook_date", "date", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(16), nullable=False)
    bull_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    bear_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    expected_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_candle: Mapped[str | None] = mapped_column(String(32), nullable=True)
    volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    main_scenario: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternative_scenario: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    trading_plans = relationship("TradingPlan", back_populates="daily_outlook")


class TradingPlan(Base):
    __tablename__ = "trading_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    daily_outlook_id: Mapped[int] = mapped_column(ForeignKey("daily_outlook.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp1: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp2: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp3: Mapped[float | None] = mapped_column(Float, nullable=True)
    rr: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    daily_outlook = relationship("DailyOutlook", back_populates="trading_plans")
