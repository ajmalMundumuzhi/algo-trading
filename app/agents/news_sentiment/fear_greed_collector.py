
from app.core.database import SessionLocal
from app.integrations.market_data.fear_greed_client import (
    FearGreedClient,
)
from app.agents.news_sentiment.fear_greed_repository import (
    save_fear_greed_observation,
)


async def collect_fear_greed():
    client = FearGreedClient()

    try:
        observation = await client.fetch_latest()

        if observation["status"] != "success":
            return {
                "status": "failed",
                "error": observation.get("error"),
            }

        with SessionLocal() as db:
            inserted = save_fear_greed_observation(
                db,
                observation,
            )

        return {
            "status": "success",
            "value": observation["value"],
            "classification": observation["classification"],
            "observed_at": observation["observed_at"],
            "database": (
                "inserted" if inserted else "already_exists"
            ),
        }

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
        }

    finally:
        await client.close()
