
import asyncio
import calendar
import hashlib
import logging
import re

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser

import feedparser
import httpx

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip_depth += 1
        elif tag in {"p", "div", "br", "li"} and not self.skip_depth:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        elif tag in {"p", "div", "li"} and not self.skip_depth:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)

    def get_text(self):
        return re.sub(
            r"\s+",
            " ",
            unescape(" ".join(self.parts)),
        ).strip()


class RSSNewsClient:
    FEEDS = {
        "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "cointelegraph": "https://cointelegraph.com/rss",
        "the_block": "https://www.theblock.co/rss.xml",
    }

    MAX_RETRIES = 3

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                20.0,
                connect=10.0,
            ),
            follow_redirects=True,
            headers={
                "User-Agent": "AlgoTradingNewsBot/1.0",
                "Accept": "application/rss+xml, application/xml, text/xml",
            },
        )

    @staticmethod
    def _clean_html(value: str) -> str:
        if not value:
            return ""

        parser = HTMLTextExtractor()

        try:
            parser.feed(str(value))
            parser.close()
            return parser.get_text()
        except Exception:
            logger.warning("Failed to clean RSS HTML content")
            return re.sub(
                r"\s+",
                " ",
                re.sub(r"<[^>]+>", " ", str(value)),
            ).strip()

    @staticmethod
    def _parse_date(entry: dict) -> str | None:
        for field in ("published_parsed", "updated_parsed"):
            parsed_value = entry.get(field)

            if parsed_value:
                try:
                    timestamp = calendar.timegm(parsed_value)

                    return datetime.fromtimestamp(
                        timestamp,
                        timezone.utc,
                    ).isoformat()
                except (TypeError, ValueError, OverflowError):
                    pass

        for field in ("published", "updated"):
            date_value = entry.get(field)

            if not date_value:
                continue

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
                pass

            try:
                parsed_date = datetime.fromisoformat(
                    date_value.replace("Z", "+00:00")
                )

                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(
                        tzinfo=timezone.utc
                    )

                return parsed_date.astimezone(
                    timezone.utc
                ).isoformat()

            except (TypeError, ValueError, OverflowError):
                pass

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
        title = RSSNewsClient._clean_html(
            entry.get("title", "")
        )

        url = str(entry.get("link", "")).strip()

        if not title or not url:
            return None

        summary = entry.get("summary", "")

        if not summary:
            content = entry.get("content", [])

            if isinstance(content, list) and content:
                summary = content[0].get("value", "")

        summary = RSSNewsClient._clean_html(summary)

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

        for attempt in range(1, self.MAX_RETRIES + 1):
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
                    "Feed %s failed on attempt %s/%s: %s",
                    source,
                    attempt,
                    self.MAX_RETRIES,
                    repr(error),
                )

                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(attempt * 2)

        raise RuntimeError(
            f"Failed to fetch {source} after "
            f"{self.MAX_RETRIES} attempts: "
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
        successful_sources = []

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
                successful_sources.append(source)

        return {
            "articles": articles,
            "total_articles": len(articles),
            "successful_sources": successful_sources,
            "failed_sources": errors,
        }

    async def close(self):
        await self.client.aclose()
