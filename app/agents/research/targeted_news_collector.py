
import asyncio
import logging
import re

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlencode

from app.agents.news_sentiment.classifier import (
    classify_sentiment,
    classify_severity,
)
from app.agents.research.news_collector import (
    build_news_result,
    get_candidate_key,
    matches_candidate_text,
)
from app.integrations.news.rss_client import RSSNewsClient


logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"

AMBIGUOUS_NAMES = {
    "bedrock",
    "coco",
}

MAX_CONCURRENT_SEARCHES = 5


def get_candidate_aliases(candidate: dict) -> list[str]:
    candidate_id = str(candidate.get("id") or "").lower()
    candidate_name = str(candidate.get("name") or "").lower()

    if candidate_id == "eigenlayer" or "eigencloud" in candidate_name:
        return ["EigenLayer"]

    return []


def build_candidate_query(candidate: dict, days: int) -> str:
    name = str(candidate.get("name") or "").strip()
    symbol = str(candidate.get("symbol") or "").strip().upper()

    terms = []

    if name and name.lower() not in AMBIGUOUS_NAMES:
        terms.append(f'"{name}"')

    for alias in get_candidate_aliases(candidate):
        terms.append(f'"{alias}"')

    if symbol:
        terms.append(f'"${symbol}"')
        terms.append(f'"{symbol}/USDT"')

    if not terms:
        return ""

    return f"({' OR '.join(dict.fromkeys(terms))}) when:{days}d"


def build_candidate_feed_url(candidate: dict, days: int) -> str:
    query = build_candidate_query(candidate, days)

    if not query:
        return ""

    params = {
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }

    return f"{GOOGLE_NEWS_RSS_URL}?{urlencode(params)}"


def parse_article_date(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except (TypeError, ValueError):
        return None


def article_is_recent(
    article: dict,
    cutoff: datetime,
) -> bool:
    published_at = parse_article_date(
        article.get("published_at")
    )

    return published_at is not None and published_at >= cutoff


def matches_targeted_candidate(
    candidate: dict,
    article: dict,
) -> bool:
    title = article.get("title") or ""
    summary = article.get("summary") or ""
    article_text = f"{title} {summary}"

    candidate_for_matching = dict(candidate)

    name = str(candidate.get("name") or "").strip().lower()

    if name in AMBIGUOUS_NAMES:
        candidate_for_matching["name"] = ""

    if matches_candidate_text(
        candidate_for_matching,
        SimpleNamespace(
            title=title,
            summary=summary,
        ),
    ):
        return True

    for alias in get_candidate_aliases(candidate):
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"

        if re.search(pattern, article_text, re.IGNORECASE):
            return True

    return False


def create_analysis_record(article: dict) -> SimpleNamespace:
    sentiment = classify_sentiment(article)
    severity = classify_severity(article)

    published_at = parse_article_date(
        article.get("published_at")
    )

    return SimpleNamespace(
        title=article.get("title"),
        source=article.get("source"),
        url=article.get("url"),
        published_at=published_at,
        sentiment=sentiment["sentiment"],
        severity=severity["severity"],
    )


async def fetch_candidate_articles(
    client: RSSNewsClient,
    candidate: dict,
    days: int,
) -> dict:
    candidate_key = get_candidate_key(candidate)
    feed_url = build_candidate_feed_url(candidate, days)

    if not feed_url:
        return {
            "candidate_key": candidate_key,
            "articles": [],
            "status": "unavailable",
            "error": "Candidate has no searchable name or symbol",
        }

    source_slug = re.sub(
        r"[^a-z0-9]+",
        "_",
        candidate_key.lower(),
    ).strip("_")[:50]

    source = f"google_news_{source_slug}"

    try:
        articles = await client.fetch_feed(
            source=source,
            feed_url=feed_url,
        )

        return {
            "candidate_key": candidate_key,
            "articles": articles,
            "status": "success",
            "error": None,
        }

    except Exception as exc:
        logger.exception(
            "Targeted news search failed for %s",
            candidate.get("name", candidate_key),
        )

        return {
            "candidate_key": candidate_key,
            "articles": [],
            "status": "error",
            "error": str(exc),
        }


async def collect_targeted_coin_news(
    candidates: list[dict],
    days: int = 7,
) -> dict[str, dict]:
    if not candidates:
        return {}

    client = RSSNewsClient()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)

    async def fetch_with_limit(candidate: dict) -> dict:
        async with semaphore:
            return await fetch_candidate_articles(
                client=client,
                candidate=candidate,
                days=days,
            )

    try:
        fetched_results = await asyncio.gather(
            *[
                fetch_with_limit(candidate)
                for candidate in candidates
            ]
        )
    finally:
        await client.close()

    fetched_by_key = {
        result["candidate_key"]: result
        for result in fetched_results
    }

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    final_results = {}

    for candidate in candidates:
        key = get_candidate_key(candidate)
        fetched = fetched_by_key.get(key)

        if not fetched:
            final_results[key] = {
                "status": "error",
                "data": None,
                "reason": "Targeted news result was missing",
            }
            continue

        if fetched["status"] == "error":
            final_results[key] = {
                "status": "error",
                "data": None,
                "reason": fetched["error"],
            }
            continue

        matched_articles = []
        seen_articles = set()

        for article in fetched["articles"]:
            if not article_is_recent(article, cutoff):
                continue

            article_identity = (
                article.get("article_id")
                or article.get("url")
                or article.get("title")
            )

            if not article_identity or article_identity in seen_articles:
                continue

            if not matches_targeted_candidate(candidate, article):
                continue

            seen_articles.add(article_identity)

            matched_articles.append(
                create_analysis_record(article)
            )

        result = build_news_result(
            candidate=candidate,
            matched_articles=matched_articles,
            days=days,
        )

        if result.get("data") is not None:
            result["data"]["discovery_source"] = "Google News RSS"
            result["data"]["discovered_articles"] = len(
                fetched["articles"]
            )
        else:
            result["discovery_source"] = "Google News RSS"
            result["discovered_articles"] = len(
                fetched["articles"]
            )

        final_results[key] = result

        logger.info(
            "Targeted news completed for %s: fetched=%s matched=%s",
            candidate.get("name", key),
            len(fetched["articles"]),
            len(matched_articles),
        )

    return final_results
