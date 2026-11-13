
import asyncio
import logging

from app.agents.news_sentiment.pipeline import run_news_analysis


logging.basicConfig(level=logging.INFO)


ASSETS = [
    {"name": "Bitcoin", "symbol": "BTC", "aliases": []},
    {"name": "Ethereum", "symbol": "ETH", "aliases": []},
    {"name": "Solana", "symbol": "SOL", "aliases": []},
    {
        "name": "BNB",
        "symbol": "BNB",
        "aliases": ["BNB Chain", "BNB token"],
    },
    {"name": "XRP", "symbol": "XRP", "aliases": []},
    {"name": "Cardano", "symbol": "ADA", "aliases": []},
    {"name": "Dogecoin", "symbol": "DOGE", "aliases": []},
    {"name": "Chainlink", "symbol": "LINK", "aliases": []},
    {"name": "Avalanche", "symbol": "AVAX", "aliases": []},
    {"name": "Polkadot", "symbol": "DOT", "aliases": []},
]


async def main():
    result = await run_news_analysis(ASSETS)

    print("\nNEWS & SENTIMENT PIPELINE REPORT")
    print("================================")

    print("Status:", result["status"])

    print("\nCOLLECTION")
    print("Total articles:", result["collection"]["total_articles"])
    print("Successful sources:", result["collection"]["successful_sources"])
    print("Failed sources:", result["collection"]["failed_sources"])

    print("\nDEDUPLICATION")
    print("Received:", result["deduplication"]["total_received"])
    print("Unique:", result["deduplication"]["unique_articles"])
    print("Duplicates:", result["deduplication"]["duplicates_removed"])

    print("\nANALYSIS")
    print("Analyzed:", result["analysis"]["total_analyzed"])
    print("Sentiment:", result["analysis"]["sentiment_counts"])
    print("Severity:", result["analysis"]["severity_counts"])

    print("\nCRITICAL AND HIGH-SEVERITY NEWS")

    important_articles = [
        article
        for article in result["articles"]
        if article["severity"]["severity"] in ("critical", "high")
    ]

    for article in important_articles:
        print("\nTitle:", article["title"])
        print("Sentiment:", article["sentiment"]["sentiment"])
        print("Severity:", article["severity"]["severity"])
        print("Affected coins:", article["affected_coins"])
        print("URL:", article["url"])

    print("\nPIPELINE TEST COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())
