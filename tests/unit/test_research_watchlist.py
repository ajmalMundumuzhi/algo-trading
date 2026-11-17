
import uuid
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.agents.research.watchlist_service import (
    review_research_candidate,
)
from app.models.research_watchlist import (
    ResearchWatchlistDecision,
)


@pytest.fixture
def reviewer():
    return SimpleNamespace(
        id=uuid.uuid4(),
        is_active=True,
    )


@pytest.fixture
def db(reviewer):
    database = MagicMock()
    database.get.return_value = reviewer
    return database


def make_candidate(
    coverage=85.0,
    research_score=75.0,
    last_researched_at="current",
):
    if last_researched_at == "current":
        last_researched_at = datetime.now(timezone.utc)

    return SimpleNamespace(
        id=uuid.uuid4(),
        coingecko_id="test-coin",
        name="Test Coin",
        symbol="TEST",
        coverage=coverage,
        research_score=research_score,
        last_researched_at=last_researched_at,
        decision=ResearchWatchlistDecision.PENDING,
        review_reason=None,
        reviewed_by=None,
        reviewed_at=None,
    )


def test_approval_allowed_with_fresh_final_research(db, reviewer):
    candidate = make_candidate()
    db.scalar.return_value = candidate

    result = review_research_candidate(
        db,
        coingecko_id="test-coin",
        reviewer_id=reviewer.id,
        decision=ResearchWatchlistDecision.APPROVED,
        reason="Research passed review",
    )

    assert result.decision == ResearchWatchlistDecision.APPROVED
    assert result.reviewed_by == reviewer.id
    db.commit.assert_called_once()


def test_approval_blocked_with_insufficient_coverage(db, reviewer):
    candidate = make_candidate(
        coverage=25.0,
        research_score=None,
    )
    db.scalar.return_value = candidate

    with pytest.raises(ValueError, match="provisional research"):
        review_research_candidate(
            db,
            coingecko_id="test-coin",
            reviewer_id=reviewer.id,
            decision=ResearchWatchlistDecision.APPROVED,
        )

    db.commit.assert_not_called()


def test_approval_blocked_without_research_timestamp(db, reviewer):
    candidate = make_candidate(last_researched_at=None)
    db.scalar.return_value = candidate

    with pytest.raises(ValueError, match="outdated"):
        review_research_candidate(
            db,
            coingecko_id="test-coin",
            reviewer_id=reviewer.id,
            decision=ResearchWatchlistDecision.APPROVED,
        )

    db.commit.assert_not_called()


def test_rejection_allowed_for_provisional_candidate(db, reviewer):
    candidate = make_candidate(
        coverage=25.0,
        research_score=None,
    )
    db.scalar.return_value = candidate

    result = review_research_candidate(
        db,
        coingecko_id="test-coin",
        reviewer_id=reviewer.id,
        decision=ResearchWatchlistDecision.REJECTED,
        reason="Insufficient research evidence",
    )

    assert result.decision == ResearchWatchlistDecision.REJECTED
    assert result.review_reason == "Insufficient research evidence"
    db.commit.assert_called_once()


def test_approval_blocked_for_inactive_reviewer(db, reviewer):
    reviewer.is_active = False

    candidate = make_candidate()
    db.scalar.return_value = candidate

    with pytest.raises(ValueError, match="Active reviewer"):
        review_research_candidate(
            db,
            coingecko_id="test-coin",
            reviewer_id=reviewer.id,
            decision=ResearchWatchlistDecision.APPROVED,
        )

    db.commit.assert_not_called()


def test_approval_blocked_when_research_is_older_than_seven_days(
    db,
    reviewer,
):
    candidate = make_candidate(
        last_researched_at=datetime.now(timezone.utc)
        - timedelta(days=8),
    )
    db.scalar.return_value = candidate

    with pytest.raises(ValueError, match="outdated"):
        review_research_candidate(
            db,
            coingecko_id="test-coin",
            reviewer_id=reviewer.id,
            decision=ResearchWatchlistDecision.APPROVED,
        )

    db.commit.assert_not_called()
