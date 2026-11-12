from sqlalchemy import Boolean, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel

class MarketAsset(BaseModel):
    __tablename__ = "market_assets"

    coingecko_id: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    binance_pair: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
    )
    market_cap_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    market_cap: Mapped[bool] = mapped_column(
        Numeric(30, 2),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False
    )