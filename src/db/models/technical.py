"""Technical Analysis domain (Ch.4 §4.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, utcnow


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"
    __table_args__ = (
        Index("ix_technical_indicators_symbol_timeframe", "symbol_id", "timeframe"),
        Index("ix_technical_indicators_symbol_timestamp", "symbol_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ema20: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema50: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema100: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema200: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd: Mapped[float | None] = mapped_column(Float, nullable=True)
    vwap: Mapped[float | None] = mapped_column(Float, nullable=True)
    atr: Mapped[float | None] = mapped_column(Float, nullable=True)
    adx: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    symbol_ref = relationship("Symbol", back_populates="indicators")


class ChartPattern(Base):
    __tablename__ = "chart_patterns"
    __table_args__ = (
        Index("ix_chart_patterns_symbol_timeframe", "symbol_id", "timeframe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    pattern: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    target: Mapped[float | None] = mapped_column(Float, nullable=True)
    invalidation: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    symbol_ref = relationship("Symbol", back_populates="patterns")


class MarketStructure(Base):
    __tablename__ = "market_structure"
    __table_args__ = (Index("ix_market_structure_symbol_timeframe", "symbol_id", "timeframe"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    trend: Mapped[str] = mapped_column(String(16), nullable=False, default="neutral")
    hh: Mapped[float | None] = mapped_column(Float, nullable=True)
    hl: Mapped[float | None] = mapped_column(Float, nullable=True)
    lh: Mapped[float | None] = mapped_column(Float, nullable=True)
    ll: Mapped[float | None] = mapped_column(Float, nullable=True)
    bos: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    choch: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    symbol_ref = relationship("Symbol", back_populates="structures")
