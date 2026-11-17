
import logging
import re

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.news_article import NewsArticle


logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {
    "low": 1.0,
    "medium": 1.5,
    "high": 2.0,
    "critical": 3.0,
}

SENTIMENT_VALUES = {
    "positive": 1,
    "negative": -1,
    "neutral": 0,
}


def normalize(value: str) -> str:
    return "".join(
        character.lower()
        for character in str(value or "")
        if character.isalnum()
    )


def extract_coin_identifiers(value) -> set[str]:
    identifiers = set()

    if isinstance(value, str):
        normalized = normalize(value)

        if normalized:
            identifiers.add(normalized)

    elif isinstance(value, dict):
        for key in (
            "symbol",
            "name",
            "coin",
            "ticker",
            "id",
        ):
            item = value.get(key)

            if isinstance(item, str):
                normalized = normalize(item)

                if normalized:
                    identifiers.add(normalized)

    elif isinstance(value, list):
        for item in value:
            identifiers.update(
                extract_coin_identifiers(item)
            )

    return identifiers


def get_candidate_key(candidate: dict) -> str:
    return (
        str(candidate.get("id") or "").strip()
        or normalize(candidate.get("symbol", ""))
        or normalize(candidate.get("name", ""))
    )


def get_candidate_identifiers(candidate: dict) -> set[str]:
    identifiers = {
        normalize(candidate.get("id", "")),
        normalize(candidate.get("symbol", "")),
        normalize(candidate.get("name", "")),
    }

    identifiers.discard("")

    return identifiers



AMBIGUOUS_COIN_IDENTIFIERS = {"cash"}


def matches_candidate_text(
    candidate: dict,
    article: NewsArticle,
) -> bool:
    text = " ".join([
        str(article.title or ""),
        str(article.summary or ""),
    ])

    normalized_text = text.lower()

    name = str(candidate.get("name") or "").strip()
    symbol = str(candidate.get("symbol") or "").strip()

    normalized_name = normalize(name)
    normalized_symbol = normalize(symbol)

    is_ambiguous = (
        normalized_name in AMBIGUOUS_COIN_IDENTIFIERS
        or normalized_symbol in AMBIGUOUS_COIN_IDENTIFIERS
    )

    if name and not is_ambiguous:
        name_pattern = (
            r"(?<!\w)"
            + re.escape(name)
            + r"(?!\w)"
        )

        if re.search(
            name_pattern,
            normalized_text,
            re.IGNORECASE,
        ):
            return True

    if symbol:
        escaped_symbol = re.escape(symbol)

        symbol_patterns = (
            rf"\${escaped_symbol}(?!\w)",
            rf"(?<!\w){escaped_symbol}"
            rf"\s*[/\-]\s*(?:USDT|USD|USDC|BTC)(?!\w)",
        )

        if any(
            re.search(
                pattern,
                text,
                re.IGNORECASE,
            )
            for pattern in symbol_patterns
        ):
            return True

    return False


def article_matches_candidate(
    candidate: dict,
    article: NewsArticle,
) -> bool:
    candidate_identifiers = get_candidate_identifiers(
        candidate
    )

    article_identifiers = extract_coin_identifiers(
        article.affected_coins
    )

    if candidate_identifiers.intersection(
        article_identifiers
    ):
        return True

    return matches_candidate_text(
        candidate,
        article,
    )


def build_news_result(
    candidate: dict,
    matched_articles: list,
    days: int,
) -> dict:
    symbol = candidate.get("symbol", "")

    if not matched_articles:
        return {
            "status": "unavailable",
            "data": {
                "symbol": symbol,
                "period_days": days,
                "article_count": 0,
            },
            "reason": (
                "No analyzed articles explicitly associated "
                "with this coin"
            ),
        }

    sentiment_counts = {
        "positive": 0,
        "negative": 0,
        "neutral": 0,
    }

    severity_counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }

    weighted_sentiment = 0.0
    maximum_weight = 0.0
    article_evidence = []

    for article in matched_articles:
        sentiment = (article.sentiment or "neutral").lower()
        severity = (article.severity or "low").lower()

        if sentiment not in SENTIMENT_VALUES:
            continue

        severity_weight = SEVERITY_WEIGHTS.get(
            severity,
            1.0,
        )

        sentiment_counts[sentiment] += 1

        if severity in severity_counts:
            severity_counts[severity] += 1

        weighted_sentiment += (
            SENTIMENT_VALUES[sentiment] * severity_weight
        )

        maximum_weight += severity_weight

        article_evidence.append({
            "title": article.title,
            "source": article.source,
            "url": article.url,
            "published_at": (
                article.published_at.isoformat()
                if article.published_at
                else None
            ),
            "sentiment": sentiment,
            "severity": severity,
        })

    valid_count = sum(sentiment_counts.values())

    if valid_count == 0 or maximum_weight == 0:
        return {
            "status": "unavailable",
            "data": None,
            "reason": "No valid analyzed sentiment records",
        }

    news_score = round(
        50 + (
            50 * weighted_sentiment / maximum_weight
        ),
        2,
    )

    return {
        "status": "available",
        "data": {
            "symbol": symbol,
            "period_days": days,
            "article_count": valid_count,
            "sentiment_counts": sentiment_counts,
            "severity_counts": severity_counts,
            "score": news_score,
            "scoring_method": (
                "Severity-weighted sentiment heuristic: "
                "positive=+1, neutral=0, negative=-1"
            ),
            "articles": article_evidence[:20],
        },
    }


def collect_coin_news_batch(
    candidates: list[dict],
    days: int = 7,
) -> dict[str, dict]:
    if not candidates:
        return {}

    candidate_data = {}

    for candidate in candidates:
        key = get_candidate_key(candidate)

        if not key:
            continue

        candidate_data[key] = {
            "candidate": candidate,
            "matched_articles": [],
        }

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    )

    article_time = func.coalesce(
        NewsArticle.published_at,
        NewsArticle.collected_at,
    )

    statement = (
        select(NewsArticle)
        .where(
            NewsArticle.analysis_status == "completed",
            article_time >= cutoff,
        )
        .order_by(article_time.desc())
        .limit(2000)
    )

    try:
        with SessionLocal() as db:
            articles = db.execute(
                statement
            ).scalars().all()

            logger.info(
                "Loaded %s recent news articles for %s candidates",
                len(articles),
                len(candidate_data),
            )

            for article in articles:
                for data in candidate_data.values():
                    if article_matches_candidate(
                        data["candidate"],
                        article,
                    ):
                        data["matched_articles"].append(
                            article
                        )

    except Exception:
        logger.exception(
            "Failed to load news articles for research candidates"
        )

        return {
            key: {
                "status": "error",
                "data": None,
                "reason": "News database query failed",
            }
            for key in candidate_data
        }

    results = {}

    for key, data in candidate_data.items():
        results[key] = build_news_result(
            candidate=data["candidate"],
            matched_articles=data["matched_articles"],
            days=days,
        )

        logger.info(
            "News matching completed for %s: %s articles",
            data["candidate"].get("name", key),
            len(data["matched_articles"]),
        )

    return results


def collect_coin_news(
    candidate: dict,
    days: int = 7,
) -> dict:
    key = get_candidate_key(candidate)

    results = collect_coin_news_batch(
        candidates=[candidate],
        days=days,
    )

    return results.get(
        key,
        {
            "status": "unavailable",
            "data": None,
            "reason": "Candidate could not be identified",
        },
    )
