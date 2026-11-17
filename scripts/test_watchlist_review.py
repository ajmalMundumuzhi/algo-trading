
from sqlalchemy import select

from app.core.database import SessionLocal
from app.agents.research.watchlist_service import (
    save_research_candidate,
    review_research_candidate,
)
from app.models import User, UserRole
from app.models.research_watchlist import (
    ResearchWatchlist,
    ResearchWatchlistDecision,
)


def main():
    db = SessionLocal()

    test_ids = [
        "test-watchlist-approval",
        "test-watchlist-rejection",
    ]

    try:
        reviewer = db.scalar(
            select(User).where(
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
            )
        )

        if reviewer is None:
            raise ValueError("No active admin reviewer found.")

        print("Reviewer:", reviewer.email)

        for coin_id in test_ids:
            existing = db.scalar(
                select(ResearchWatchlist).where(
                    ResearchWatchlist.coingecko_id == coin_id
                )
            )

            if existing is not None:
                db.delete(existing)

        db.commit()

        approved_candidate = save_research_candidate(
            db,
            coingecko_id=test_ids[0],
            name="Test Approval Coin",
            symbol="TAC",
            market_cap_rank=450,
            research_score=75.0,
            coverage=90.0,
        )

        rejected_candidate = save_research_candidate(
            db,
            coingecko_id=test_ids[1],
            name="Test Rejection Coin",
            symbol="TRC",
            market_cap_rank=460,
            research_score=35.0,
            coverage=85.0,
        )

        approved = review_research_candidate(
            db,
            coingecko_id=approved_candidate.coingecko_id,
            reviewer_id=reviewer.id,
            decision=ResearchWatchlistDecision.APPROVED,
            reason="Test approval workflow.",
        )

        rejected = review_research_candidate(
            db,
            coingecko_id=rejected_candidate.coingecko_id,
            reviewer_id=reviewer.id,
            decision=ResearchWatchlistDecision.REJECTED,
            reason="Test rejection workflow.",
        )

        db.refresh(approved)
        db.refresh(rejected)

        print("\nAPPROVAL TEST")
        print("Decision:", approved.decision.value)
        print("Reviewer ID matches:", approved.reviewed_by == reviewer.id)
        print("Reviewed at:", approved.reviewed_at is not None)
        print("Reason:", approved.review_reason)

        print("\nREJECTION TEST")
        print("Decision:", rejected.decision.value)
        print("Reviewer ID matches:", rejected.reviewed_by == reviewer.id)
        print("Reviewed at:", rejected.reviewed_at is not None)
        print("Reason:", rejected.review_reason)

        approval_passed = (
            approved.decision == ResearchWatchlistDecision.APPROVED
            and approved.reviewed_by == reviewer.id
            and approved.reviewed_at is not None
        )

        rejection_passed = (
            rejected.decision == ResearchWatchlistDecision.REJECTED
            and rejected.reviewed_by == reviewer.id
            and rejected.reviewed_at is not None
        )

        print("\nRESULT")
        print("Approval:", "PASS" if approval_passed else "FAIL")
        print("Rejection:", "PASS" if rejection_passed else "FAIL")

        if not approval_passed or not rejection_passed:
            raise AssertionError("Watchlist review test failed.")

    finally:
        for coin_id in test_ids:
            candidate = db.scalar(
                select(ResearchWatchlist).where(
                    ResearchWatchlist.coingecko_id == coin_id
                )
            )

            if candidate is not None:
                db.delete(candidate)

        db.commit()
        db.close()

        print("\nTemporary test candidates cleaned up.")


if __name__ == "__main__":
    main()
