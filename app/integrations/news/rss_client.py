
import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

logger = logging.getLogger(__name__)


class RSSNewsClient:
    FEEDS = {
        "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "cointelegraph": "https://cointelegraph.com/rss",
        "the_block": "https://www.theblock.co/rss.xml",
    }

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={
                "User-Agent": "AlgoTradingNewsBot/1.0"
            },
        )

    @staticmethod
    def _parse_date(entry: dict) -> str | None:
        date_value = (
            entry.get("published")
            or entry.get("updated")
        )

        if not date_value:
            return None

        try:
            parsed_date = parsedate_to_datetime(date_value)

            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(
                    tzinfo=timezone.utc
                )

            return parsed_date.astimezone(
                timezone.utc
            ).isoformat()

        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _create_article_id(
        source: str,
        url: str,
        title: str,
    ) -> str:
        identity = f"{source}:{url or title}".lower()

        return hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _normalize_entry(
        source: str,
        entry: dict,
    ) -> dict | None:
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()

        if not title or not url:
            return None

        summary = entry.get("summary", "")

        return {
            "article_id": RSSNewsClient._create_article_id(
                source,
                url,
                title,
            ),
            "source": source,
            "title": title,
            "summary": summary,
            "url": url,
            "published_at": RSSNewsClient._parse_date(entry),
            "collected_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    
    async def fetch_feed(
        self,
        source: str,
        feed_url: str,
    ) -> list[dict]:
        last_error = None

        for attempt in range(1, 4):
            try:
                response = await self.client.get(feed_url)
                response.raise_for_status()

                parsed_feed = await asyncio.to_thread(
                    feedparser.parse,
                    response.content,
                )

                if parsed_feed.bozo and not parsed_feed.entries:
                    raise ValueError(
                        f"Invalid RSS feed from {source}: "
                        f"{parsed_feed.bozo_exception}"
                    )

                articles = []

                for entry in parsed_feed.entries:
                    article = self._normalize_entry(
                        source,
                        entry,
                    )

                    if article:
                        articles.append(article)

                logger.info(
                    "Fetched %s articles from %s",
                    len(articles),
                    source,
                )

                return articles

            except (
                httpx.HTTPError,
                ValueError,
                TimeoutError,
            ) as error:
                last_error = error

                logger.warning(
                    "Feed %s failed on attempt %s/3: %s",
                    source,
                    attempt,
                    repr(error),
                )

                if attempt < 3:
                    await asyncio.sleep(attempt * 2)

        raise RuntimeError(
            f"Failed to fetch {source} after 3 attempts: "
            f"{type(last_error).__name__}: {last_error}"
        ) from last_error


    async def fetch_all(self) -> dict:
        tasks = {
            source: self.fetch_feed(source, url)
            for source, url in self.FEEDS.items()
        }

        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True,
        )

        articles = []
        errors = {}

        for source, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(
                    "Failed to fetch %s: %s",
                    source,
                    result,
                )
                errors[source] = str(result)
            else:
                articles.extend(result)

        return {
            "articles": articles,
            "total_articles": len(articles),
            "successful_sources": [
                source
                for source, result in zip(tasks.keys(), results)
                if not isinstance(result, Exception)
            ],
            "failed_sources": errors,
        }

    async def close(self):
        await self.client.aclose()
