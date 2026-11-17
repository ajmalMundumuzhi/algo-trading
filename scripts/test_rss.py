
import asyncio

from app.integrations.news.rss_client import RSSNewsClient


async def main():
    client = RSSNewsClient()

    try:
        result = await client.fetch_all()

        print("\n========== RSS TEST RESULTS ==========")
        print("Total articles:", result["total_articles"])
        print("Successful sources:", result["successful_sources"])
        print("Failed sources:", result["failed_sources"])

        if result["articles"]:
            print("\nSample article:")
            print(result["articles"][0])

        print("\n========== TEST COMPLETED ==========")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
