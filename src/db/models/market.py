"""Market Data domain tables (Ch.4 §4.4 / §4.5)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, utcnow


class MarketCandle(Base):
    __tablename__ = "market_candles"
    __table_args__ = (
        Index("ix_market_candles_symbol_timeframe", "symbol_id", "timeframe"),
        Index("ix_market_candles_symbol_timestamp", "symbol_id", "timestamp"),
        Index("ix_market_candles_exchange_timestamp", "exchange_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    exchange = relationship("Exchange", back_populates="candles")
    symbol_ref = relationship("Symbol", back_populates="candles")


class FundingRate(Base):
    __tablename__ = "funding_rates"
    __table_args__ = (
        Index("ix_funding_rates_symbol_timestamp", "symbol_id", "timestamp"),
        Index("ix_funding_rates_exchange_timestamp", "exchange_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    funding_rate: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    exchange = relationship("Exchange", back_populates="funding_rates")
    symbol_ref = relationship("Symbol", back_populates="funding_rates")


class OpenInterest(Base):
    __tablename__ = "open_interest"
    __table_args__ = (
        Index("ix_open_interest_symbol_timestamp", "symbol_id", "timestamp"),
        Index("ix_open_interest_exchange_timestamp", "exchange_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    oi: Mapped[float] = mapped_column(Float, nullable=False)
    oi_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    exchange = relationship("Exchange", back_populates="open_interests")
    symbol_ref = relationship("Symbol", back_populates="open_interests")


class Liquidation(Base):
    __tablename__ = "liquidations"
    __table_args__ = (
        Index("ix_liquidations_symbol_timestamp", "symbol_id", "timestamp"),
        Index("ix_liquidations_exchange_timestamp", "exchange_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    side: Mapped[str | None] = mapped_column(String(8), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    exchange = relationship("Exchange", back_populates="liquidations")
    symbol_ref = relationship("Symbol", back_populates="liquidations")


class OrderBookSnapshot(Base):
    __tablename__ = "orderbook_snapshot"
    __table_args__ = (
        Index("ix_orderbook_symbol_timestamp", "symbol_id", "timestamp"),
        Index("ix_orderbook_exchange_timestamp", "exchange_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    best_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    imbalance: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # full depth JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    exchange = relationship("Exchange", back_populates="orderbooks")
    symbol_ref = relationship("Symbol", back_populates="orderbooks")


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_symbol_timestamp", "symbol_id", "timestamp"),
        Index("ix_trades_exchange_timestamp", "exchange_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    side: Mapped[str | None] = mapped_column(String(8), nullable=True)
    aggressor: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    exchange = relationship("Exchange", back_populates="trades")
    symbol_ref = relationship("Symbol", back_populates="trades")
