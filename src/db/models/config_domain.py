"""Configuration + market reference tables (Ch.4 / Ch.11 §11.6–§11.7).

Ch.11 `assets` ≡ `symbols`. Ch.11 exchange metadata includes api_status/last_sync.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, utcnow


class Exchange(Base):
    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="futures")  # spot|futures|options
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")  # critical|high|medium
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    api_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    candles = relationship("MarketCandle", back_populates="exchange")
    funding_rates = relationship("FundingRate", back_populates="exchange")
    open_interests = relationship("OpenInterest", back_populates="exchange")
    liquidations = relationship("Liquidation", back_populates="exchange")
    orderbooks = relationship("OrderBookSnapshot", back_populates="exchange")
    trades = relationship("Trade", back_populates="exchange")
    options = relationship("OptionsChain", back_populates="exchange")


class Symbol(Base):
    """Asset registry (Ch.11 §11.6 assets)."""

    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False, default=lambda: str(uuid4()), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    base_asset: Mapped[str] = mapped_column(String(16), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # active/inactive
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    candles = relationship("MarketCandle", back_populates="symbol_ref")
    funding_rates = relationship("FundingRate", back_populates="symbol_ref")
    open_interests = relationship("OpenInterest", back_populates="symbol_ref")
    liquidations = relationship("Liquidation", back_populates="symbol_ref")
    orderbooks = relationship("OrderBookSnapshot", back_populates="symbol_ref")
    trades = relationship("Trade", back_populates="symbol_ref")
    options = relationship("OptionsChain", back_populates="symbol_ref")
    indicators = relationship("TechnicalIndicator", back_populates="symbol_ref")
    patterns = relationship("ChartPattern", back_populates="symbol_ref")
    structures = relationship("MarketStructure", back_populates="symbol_ref")


class SystemSetting(Base):
    """Non-secret configuration. API secrets stay in environment (Ch.3 §3.18)."""

    __tablename__ = "system_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_system_settings_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    domain: Mapped[str] = mapped_column(String(32), nullable=False, default="general")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# Ch.11 naming alias
Asset = Symbol
