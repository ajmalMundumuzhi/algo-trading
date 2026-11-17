
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ResearchWatchlistDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ResearchWatchlist(BaseModel):
    __tablename__ = "research_watchlist"

    __table_args__ = (
        Index("ix_research_watchlist_decision", "decision"),
        Index("ix_research_watchlist_market_cap_rank", "market_cap_rank"),
    )

    coingecko_id: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    market_cap_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    research_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    coverage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    last_researched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    decision: Mapped[ResearchWatchlistDecision] = mapped_column(
        Enum(
            ResearchWatchlistDecision,
            name="research_watchlist_decision",
            values_callable=lambda decisions: [
                decision.value for decision in decisions
            ],
        ),
        default=ResearchWatchlistDecision.PENDING,
        nullable=False,
    )

    review_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
