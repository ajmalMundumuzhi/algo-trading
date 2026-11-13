
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class NewsArticle(BaseModel):
    __tablename__ = "news_articles"

    article_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    sentiment: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    severity: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    affected_coins: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    sentiment_details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    severity_details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    analysis_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "article_fingerprint",
            name="uq_news_articles_fingerprint",
        ),
        Index(
            "ix_news_articles_published_at",
            "published_at",
        ),
        Index(
            "ix_news_articles_severity",
            "severity",
        ),
        Index(
            "ix_news_articles_source",
            "source",
        ),
    )
