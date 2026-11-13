
import logging

from app.integrations.news.rss_client import RSSNewsClient
from app.agents.news_sentiment.deduplicator import (
    deduplicate_articles,
)
from app.agents.news_sentiment.classifier import (
    classify_news,
)

logger = logging.getLogger(__name__)


async def run_news_analysis(assets: list[dict]) -> dict:
    client = RSSNewsClient()

    try:
        collection = await client.fetch_all()

    finally:
        await client.close()

    deduplication = deduplicate_articles(
        collection["articles"]
    )

    analyzed_articles = []

    for article in deduplication["articles"]:
        try:
            analysis = classify_news(
                article,
                assets,
            )

            analyzed_articles.append(analysis)

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

        severity_counts[severity] += 1
        sentiment_counts[sentiment] += 1

    return {
        "status": (
            "failed"
            if not collection["successful_sources"]
            else "partial"
            if collection["failed_sources"]
            else "ok"
        ),
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
        "articles": analyzed_articles,
    }
