
import asyncio

from app.agents.news_sentiment.pipeline import run_news_analysis


async def main():
    result = await run_news_analysis()

    print("\n========== NEWS PIPELINE RESULTS ==========")

    print("\nPIPELINE")
    print("Status:", result["status"])
    print("Assets loaded:", result["assets_loaded"])

    print("\nRSS COLLECTION")
    print("Articles collected:", result["collection"]["total_articles"])
    print("Successful sources:", result["collection"]["successful_sources"])
    print("Failed sources:", result["collection"]["failed_sources"])

    print("\nFEAR & GREED")
    fear_greed = result["fear_greed"]
    print("Status:", fear_greed["status"])

    if fear_greed["status"] == "success":
        print("Value:", fear_greed["value"])
        print("Classification:", fear_greed["classification"])
        print("Database:", fear_greed["database"])
    else:
        print("Error:", fear_greed.get("error"))

    print("\nDEDUPLICATION")
    print("Received:", result["deduplication"]["total_received"])
    print("Unique:", result["deduplication"]["unique_articles"])
    print("Duplicates:", result["deduplication"]["duplicates_removed"])

    print("\nNEWS ANALYSIS")
    print("Analyzed:", result["analysis"]["total_analyzed"])
    print("Sentiment:", result["analysis"]["sentiment_counts"])
    print("Severity:", result["analysis"]["severity_counts"])

    print("\nNEWS DATABASE")
    print("Persistence:", result["persistence"])

    print("\n========== TEST COMPLETED ==========")


if __name__ == "__main__":
    asyncio.run(main())
