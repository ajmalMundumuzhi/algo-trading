
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


TRACKING_PARAMETERS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
}


def normalize_url(url: str) -> str:
    if not url:
        return ""

    parsed = urlsplit(url.strip())

    query_parameters = [
        (key, value)
        for key, value in parse_qsl(parsed.query)
        if key.lower() not in TRACKING_PARAMETERS
    ]

    normalized = urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/"),
        urlencode(query_parameters),
        "",
    ))

    return normalized


def normalize_title(title: str) -> str:
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", " ", title)
    title = re.sub(r"\s+", " ", title)

    return title.strip()


def create_title_hash(title: str) -> str:
    normalized_title = normalize_title(title)

    return hashlib.sha256(
        normalized_title.encode("utf-8")
    ).hexdigest()


def deduplicate_articles(articles: list[dict]) -> dict:
    seen_urls = set()
    seen_titles = set()

    unique_articles = []
    duplicates = []

    for article in articles:
        url = normalize_url(article.get("url", ""))
        title = create_title_hash(article.get("title", ""))

        if not url and not article.get("title"):
            duplicates.append(article)
            continue

        if url in seen_urls or title in seen_titles:
            duplicates.append(article)
            continue

        if url:
            seen_urls.add(url)

        seen_titles.add(title)

        unique_articles.append(article)

    return {
        "articles": unique_articles,
        "total_received": len(articles),
        "unique_articles": len(unique_articles),
        "duplicates_removed": len(duplicates),
        "duplicate_articles": duplicates,
    }
