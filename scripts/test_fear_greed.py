
import asyncio

from app.core.database import SessionLocal
from app.agents.news_sentiment.fear_greed_collector import (
    collect_fear_greed,
)
from app.agents.news_sentiment.fear_greed_repository import (
    get_latest_fear_greed,
    get_fear_greed_history,
)


async def main():
    print("\n========== FEAR & GREED DATABASE TEST ==========")

    result = await collect_fear_greed()

    print("\nCOLLECTION")
    print("Status:", result["status"])

    if result["status"] != "success":
        print("Error:", result.get("error"))
        return

    print("Value:", result["value"])
    print("Classification:", result["classification"])
    print("Database:", result["database"])

    with SessionLocal() as db:
        latest = get_latest_fear_greed(db)
        history = get_fear_greed_history(db, limit=30)

    print("\nDATABASE VERIFICATION")
    print("Latest record:", latest.value if latest else None)
    print(
        "Latest classification:",
        latest.classification if latest else None,
    )
    print("Historical records retrieved:", len(history))

    print("\n========== TEST COMPLETED ==========")


if __name__ == "__main__":
    asyncio.run(main())
