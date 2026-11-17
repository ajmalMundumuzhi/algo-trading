
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.models.research_watchlist import (
    ResearchWatchlist,
    ResearchWatchlistDecision,
)


MINIMUM_APPROVAL_COVERAGE = 80.0
RESEARCH_FRESHNESS_DAYS = 7


def is_research_fresh(
    candidate: ResearchWatchlist,
    now: datetime | None = None,
) -> bool:
    if candidate.last_researched_at is None:
        return False

    if now is None:
        now = datetime.now(timezone.utc)

    researched_at = candidate.last_researched_at

    if researched_at.tzinfo is None:
        researched_at = researched_at.replace(tzinfo=timezone.utc)

    age = now - researched_at

    return timedelta(0) <= age <= timedelta(
        days=RESEARCH_FRESHNESS_DAYS
    )


def save_research_candidate(
    db: Session,
    *,
    coingecko_id: str,
    name: str,
    symbol: str,
    market_cap_rank: int | None = None,
    research_score: float | None = None,
    coverage: float | None = None,
) -> ResearchWatchlist:
    candidate = db.scalar(
        select(ResearchWatchlist).where(
            ResearchWatchlist.coingecko_id == coingecko_id
        )
    )

    is_final_score = (
        coverage is not None
        and coverage >= MINIMUM_APPROVAL_COVERAGE
        and research_score is not None
    )

    safe_research_score = (
        research_score if is_final_score else None
    )

    now = datetime.now(timezone.utc)

    if candidate is None:
        candidate = ResearchWatchlist(
            coingecko_id=coingecko_id,
            name=name,
            symbol=symbol,
            market_cap_rank=market_cap_rank,
            research_score=safe_research_score,
            coverage=coverage,
            last_researched_at=now,
            decision=ResearchWatchlistDecision.PENDING,
        )

        db.add(candidate)

    else:
        candidate.name = name
        candidate.symbol = symbol
        candidate.market_cap_rank = market_cap_rank
        candidate.research_score = safe_research_score
        candidate.coverage = coverage
        candidate.last_researched_at = now

    db.commit()
    db.refresh(candidate)

    return candidate


def review_research_candidate(
    db: Session,
    *,
    coingecko_id: str,
    reviewer_id: uuid.UUID,
    decision: ResearchWatchlistDecision,
    reason: str | None = None,
) -> ResearchWatchlist:
    if decision not in {
        ResearchWatchlistDecision.APPROVED,
        ResearchWatchlistDecision.REJECTED,
    }:
        raise ValueError("Decision must be approved or rejected.")

    reviewer = db.get(User, reviewer_id)

    if reviewer is None or not reviewer.is_active:
        raise ValueError("Active reviewer account not found.")

    candidate = db.scalar(
        select(ResearchWatchlist).where(
            ResearchWatchlist.coingecko_id == coingecko_id
        )
    )

    if candidate is None:
        raise ValueError("Research candidate not found.")

    if decision == ResearchWatchlistDecision.APPROVED:
        if candidate.coverage is None:
            raise ValueError(
                "Cannot approve a candidate without research coverage."
            )

        if candidate.coverage < MINIMUM_APPROVAL_COVERAGE:
            raise ValueError(
                "Cannot approve a candidate with provisional research. "
                f"Minimum required coverage is "
                f"{MINIMUM_APPROVAL_COVERAGE}%."
            )

        if candidate.research_score is None:
            raise ValueError(
                "Cannot approve a candidate without a final research score."
            )

        if not is_research_fresh(candidate):
            raise ValueError(
                "Cannot approve a candidate with outdated research. "
                f"Research must be refreshed within "
                f"{RESEARCH_FRESHNESS_DAYS} days."
            )

    candidate.decision = decision
    candidate.review_reason = reason
    candidate.reviewed_by = reviewer.id
    candidate.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(candidate)

    return candidate


def get_research_watchlist(
    db: Session,
    decision: ResearchWatchlistDecision | None = None,
) -> list[ResearchWatchlist]:
    query = select(ResearchWatchlist).order_by(
        ResearchWatchlist.created_at.desc()
    )

    if decision is not None:
        query = query.where(
            ResearchWatchlist.decision == decision
        )

    return list(db.scalars(query).all())
