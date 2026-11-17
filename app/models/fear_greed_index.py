
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    BigInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class FearGreedIndex(BaseModel):
    __tablename__ = "fear_greed_indices"

    api_timestamp: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    classification: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        default="alternative.me",
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "api_timestamp",
            name="uq_fear_greed_api_timestamp",
        ),
        Index(
            "ix_fear_greed_observed_at",
            "observed_at",
        ),
    )
