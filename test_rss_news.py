
import asyncio
import logging

from app.integrations.news.rss_client import RSSNewsClient


logging.basicConfig(level=logging.INFO)


async def main():
    client = RSSNewsClient()

    try:
        result = await client.fetch_all()

        print("\nNEWS COLLECTION REPORT")
        print("======================")

        print("Total articles:", result["total_articles"])

        print("\nSuccessful sources:")
        for source in result["successful_sources"]:
            print("-", source)

        print("\nFailed sources:")
        for source, error in result["failed_sources"].items():
            print("-", source, ":", error)

        print("\nLATEST ARTICLES")

        for article in result["articles"][:10]:
            print("\nSource:", article["source"])
            print("Title:", article["title"])
            print("Published:", article["published_at"])
            print("URL:", article["url"])
            print("Article ID:", article["article_id"])

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
