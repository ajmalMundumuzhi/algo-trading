
from app.agents.news_sentiment.deduplicator import (
    deduplicate_articles,
)


articles = [
    {
        "source": "coindesk",
        "title": "Bitcoin ETF sees major institutional inflows",
        "url": "https://example.com/bitcoin-etf?utm_source=rss",
    },
    {
        "source": "cointelegraph",
        "title": "Bitcoin ETF sees major institutional inflows",
        "url": "https://example.com/bitcoin-etf",
    },
    {
        "source": "the_block",
        "title": "Ethereum network activity reaches new high",
        "url": "https://example.com/ethereum",
    },
    {
        "source": "coindesk",
        "title": "Crypto market experiences a major recovery",
        "url": "https://example.com/market-recovery",
    },
]

result = deduplicate_articles(articles)

print("\nNEWS DEDUPLICATION REPORT")
print("=========================")

print("Total received:", result["total_received"])
print("Unique articles:", result["unique_articles"])
print("Duplicates removed:", result["duplicates_removed"])

print("\nUNIQUE ARTICLES")

for article in result["articles"]:
    print("-", article["title"])

print("\nDUPLICATES")

for article in result["duplicate_articles"]:
    print("-", article["title"])

assert result["total_received"] == 4
assert result["unique_articles"] == 3
assert result["duplicates_removed"] == 1

print("\nAll deduplication tests passed!")
