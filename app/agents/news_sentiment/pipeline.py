
import logging

from app.agents.news_sentiment.classifier import classify_news
from app.agents.news_sentiment.deduplicator import deduplicate_articles
from app.agents.news_sentiment.repository import (
    get_active_news_assets,
    save_analyzed_articles,
)
from app.core.database import SessionLocal
from app.integrations.news.rss_client import RSSNewsClient

logger = logging.getLogger(__name__)


async def run_news_analysis(assets: list[dict] | None = None) -> dict:
    if assets is None:
        with SessionLocal() as db:
            assets = get_active_news_assets(db)

    if not assets:
        raise RuntimeError(
            "No active market assets found in the database"
        )

    client = RSSNewsClient()

    try:
        collection = await client.fetch_all()
    finally:
        await client.close()

    deduplication = deduplicate_articles(
        collection["articles"]
    )

    analyzed_articles = []
    persistence_records = []

    for article in deduplication["articles"]:
        try:
            analysis = classify_news(article, assets)

            analyzed_articles.append(analysis)

            persistence_records.append({
                "article": article,
                "analysis": analysis,
            })

        except Exception:
            logger.exception(
                "Failed to classify article: %s",
                article.get("article_id"),
            )

    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    sentiment_counts = {
        "positive": 0,
        "negative": 0,
        "neutral": 0,
    }

    for article in analyzed_articles:
        severity = article["severity"]["severity"]
        sentiment = article["sentiment"]["sentiment"]

        if severity in severity_counts:
            severity_counts[severity] += 1

        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1

    persistence = {
        "status": "pending",
        "received": len(persistence_records),
        "inserted": 0,
        "duplicates": 0,
    }

    try:
        with SessionLocal() as db:
            persistence_result = save_analyzed_articles(
                db,
                persistence_records,
            )

        persistence = {
            "status": "ok",
            **persistence_result,
        }

    except Exception:
        logger.exception(
            "Failed to persist analyzed news articles"
        )

        persistence["status"] = "failed"

    if not collection["successful_sources"]:
        pipeline_status = "failed"
    elif (
        collection["failed_sources"]
        or persistence["status"] == "failed"
    ):
        pipeline_status = "partial"
    else:
        pipeline_status = "ok"

    return {
        "status": pipeline_status,
        "assets_loaded": len(assets),
        "collection": {
            "total_articles": collection["total_articles"],
            "successful_sources": collection["successful_sources"],
            "failed_sources": collection["failed_sources"],
        },
        "deduplication": {
            "total_received": deduplication["total_received"],
            "unique_articles": deduplication["unique_articles"],
            "duplicates_removed": deduplication["duplicates_removed"],
        },
        "analysis": {
            "total_analyzed": len(analyzed_articles),
            "sentiment_counts": sentiment_counts,
            "severity_counts": severity_counts,
        },
        "persistence": persistence,
        "articles": analyzed_articles,
    }
