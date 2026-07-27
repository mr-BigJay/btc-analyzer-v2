"""Options Analytics domain (Ch.4 §4.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, utcnow


class OptionsChain(Base):
    __tablename__ = "options_chain"
    __table_args__ = (
        Index("ix_options_chain_symbol_expiration", "symbol_id", "expiration"),
        Index("ix_options_chain_exchange_timestamp", "exchange_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    expiration: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    strike: Mapped[float | None] = mapped_column(Float, nullable=True)
    type: Mapped[str | None] = mapped_column(String(8), nullable=True)  # call|put
    iv: Mapped[float | None] = mapped_column(Float, nullable=True)
    delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    gamma: Mapped[float | None] = mapped_column(Float, nullable=True)
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    vega: Mapped[float | None] = mapped_column(Float, nullable=True)
    open_interest: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    instrument: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    exchange = relationship("Exchange", back_populates="options")
    symbol_ref = relationship("Symbol", back_populates="options")


class OptionsAnalyticsSnapshot(Base):
    """Derived options metrics snapshot (PCR, max pain, GEX, etc.)."""

    __tablename__ = "options_analytics"
    __table_args__ = (Index("ix_options_analytics_symbol_timestamp", "symbol_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    put_call_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_pain: Mapped[float | None] = mapped_column(Float, nullable=True)
    iv_rank: Mapped[float | None] = mapped_column(Float, nullable=True)
    iv_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    gamma_exposure: Mapped[float | None] = mapped_column(Float, nullable=True)
    dealer_gamma: Mapped[float | None] = mapped_column(Float, nullable=True)
    dealer_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_skew: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
