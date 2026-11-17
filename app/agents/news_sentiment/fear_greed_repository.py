
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.fear_greed_index import FearGreedIndex


def save_fear_greed_observation(
    db: Session,
    observation: dict,
) -> bool:
    statement = (
        insert(FearGreedIndex)
        .values(
            api_timestamp=observation["timestamp"],
            observed_at=observation["observed_at"],
            value=observation["value"],
            classification=observation["classification"],
            source=observation["source"],
        )
        .on_conflict_do_nothing(
            index_elements=["api_timestamp"]
        )
        .returning(FearGreedIndex.id)
    )

    result = db.execute(statement)
    inserted = result.scalar_one_or_none() is not None

    db.commit()

    return inserted


def get_latest_fear_greed(db: Session):
    statement = (
        select(FearGreedIndex)
        .order_by(FearGreedIndex.observed_at.desc())
        .limit(1)
    )

    return db.execute(statement).scalar_one_or_none()


def get_fear_greed_history(
    db: Session,
    limit: int = 30,
):
    statement = (
        select(FearGreedIndex)
        .order_by(FearGreedIndex.observed_at.desc())
        .limit(limit)
    )

    return db.execute(statement).scalars().all()
