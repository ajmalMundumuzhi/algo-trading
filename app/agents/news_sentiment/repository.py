
import hashlib
import logging
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.market_asset import MarketAsset
from app.models.news_article import NewsArticle

logger = logging.getLogger(__name__)


def get_active_news_assets(db: Session) -> list[dict]:
    statement = (
        select(MarketAsset)
        .where(MarketAsset.is_active.is_(True))
        .order_by(
            MarketAsset.market_cap_rank.asc().nullslast()
        )
    )

    assets = db.execute(statement).scalars().all()

    return [
        {
            "name": asset.name,
            "symbol": asset.symbol,
            "aliases": [],
        }
        for asset in assets
    ]


def create_article_fingerprint(article: dict) -> str:
    title = article.get("title", "")

    normalized_title = re.sub(
        r"\s+",
        " ",
        re.sub(r"[^\w\s]", "", title.lower()),
    ).strip()

    identity = normalized_title or article.get(
        "url", ""
    ).strip().lower()

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


def parse_published_at(value: str | datetime | None) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return None


def save_analyzed_articles(
    db: Session,
    articles: list[dict],
) -> dict:
    if not articles:
        return {
            "received": 0,
            "inserted": 0,
            "duplicates": 0,
        }

    records = []

    for item in articles:
        article = item["article"]
        analysis = item["analysis"]

        sentiment_details = analysis.get("sentiment", {})
        severity_details = analysis.get("severity", {})

        records.append({
            "article_fingerprint": create_article_fingerprint(
                article
            ),
            "source": article["source"],
            "title": article["title"],
            "summary": article.get("summary"),
            "url": article["url"],
            "published_at": parse_published_at(
                article.get("published_at")
            ),
            "sentiment": sentiment_details.get("sentiment"),
            "severity": severity_details.get("severity"),
            "affected_coins": analysis.get(
                "affected_coins", []
            ),
            "sentiment_details": sentiment_details,
            "severity_details": severity_details,
            "analysis_status": "completed",
        })

    statement = (
        insert(NewsArticle)
        .values(records)
        .on_conflict_do_nothing(
            index_elements=["article_fingerprint"]
        )
        .returning(NewsArticle.id)
    )

    try:
        inserted_ids = (
            db.execute(statement)
            .scalars()
            .all()
        )

        db.commit()

        inserted = len(inserted_ids)

        return {
            "received": len(records),
            "inserted": inserted,
            "duplicates": len(records) - inserted,
        }

    except Exception:
        db.rollback()

        logger.exception(
            "Failed to save analyzed news articles"
        )

        raise
