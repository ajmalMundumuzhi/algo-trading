
import logging

from app.agents.news_sentiment.classifier import classify_news
from app.agents.news_sentiment.deduplicator import deduplicate_articles
from app.agents.news_sentiment.fear_greed_collector import (
    collect_fear_greed,
)
from app.agents.news_sentiment.market_context import (
    get_market_context,
)
from app.agents.news_sentiment.repository import (
    get_active_news_assets,
    save_analyzed_articles,
)
from app.core.database import SessionLocal
from app.integrations.news.rss_client import RSSNewsClient

logger = logging.getLogger(__name__)

NEWS_MARKET_TIMEFRAME = "1h"


def attach_market_context(
    db,
    analysis: dict,
    context_cache: dict,
) -> dict:
    affected_coins = analysis.get("affected_coins", [])
    market_contexts = []

    for coin in affected_coins:
        symbol = coin.get("symbol")

        if not symbol:
            continue

        symbol = symbol.strip().upper()
        name = coin.get("name")

        cache_key = (symbol, name)

        if cache_key not in context_cache:
            try:
                context_cache[cache_key] = get_market_context(
                    db=db,
                    symbol=symbol,
                    timeframe=NEWS_MARKET_TIMEFRAME,
                    asset_name=name,
                )
            except Exception:
                logger.exception(
                    "Failed to retrieve market context for %s",
                    symbol,
                )

                context_cache[cache_key] = {
                    "status": "failed",
                    "symbol": symbol,
                    "timeframe": NEWS_MARKET_TIMEFRAME,
                    "reason": "Market context retrieval failed",
                    "latest_candle_price": None,
                    "previous_candle_price": None,
                    "price_change_pct": None,
                    "volume": None,
                    "latest_candle_timestamp": None,
                    "candle_age_minutes": None,
                }

        market_contexts.append(context_cache[cache_key])

    analysis["market_context"] = market_contexts

    return analysis


async def run_news_analysis(
    assets: list[dict] | None = None,
) -> dict:
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

    try:
        fear_greed = await collect_fear_greed()
    except Exception as exc:
        logger.exception("Fear & Greed collection failed")

        fear_greed = {
            "status": "failed",
            "error": str(exc),
        }

    deduplication = deduplicate_articles(
        collection["articles"]
    )

    analyzed_articles = []
    persistence_records = []
    context_cache = {}

    with SessionLocal() as db:
        for article in deduplication["articles"]:
            try:
                analysis = classify_news(article, assets)

                analysis = attach_market_context(
                    db=db,
                    analysis=analysis,
                    context_cache=context_cache,
                )

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

    market_context_counts = {
        "available": 0,
        "stale": 0,
        "unavailable": 0,
        "ambiguous": 0,
        "failed": 0,
    }

    for article in analyzed_articles:
        for context in article.get("market_context", []):
            status = context.get("status")

            if status in market_context_counts:
                market_context_counts[status] += 1

    if not collection["successful_sources"]:
        pipeline_status = "failed"
    elif (
        collection["failed_sources"]
        or persistence["status"] == "failed"
        or fear_greed["status"] != "success"
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

        "fear_greed": fear_greed,

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

        "market_context": {
            "timeframe": NEWS_MARKET_TIMEFRAME,
            "coin_contexts": market_context_counts,
        },

        "persistence": persistence,
        "articles": analyzed_articles,
    }
