from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MarketCandle(BaseModel):
    __tablename__ = "market_candles"

    asset_id: Mapped[str] = mapped_column(
        ForeignKey("market_assets.id", ondelete="CASCADE"),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    timeframe: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    open: Mapped[Decimal] = mapped_column(
        Numeric(30, 12),
        nullable=False,
    )

    high: Mapped[Decimal] = mapped_column(
        Numeric(30, 12),
        nullable=False,
    )

    low: Mapped[Decimal] = mapped_column(
        Numeric(30, 12),
        nullable=False,
    )

    close: Mapped[Decimal] = mapped_column(
        Numeric(30, 12),
        nullable=False,
    )

    volume: Mapped[Decimal] = mapped_column(
        Numeric(35, 12),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "timeframe",
            "timestamp",
            name="uq_market_candle_symbol_timeframe_timestamp",
        ),
        Index(
            "ix_market_candles_symbol_timestamp",
            "symbol",
            "timestamp",
        ),
    )