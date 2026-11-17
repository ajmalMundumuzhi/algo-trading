
from datetime import datetime, timezone

import httpx


class FearGreedClient:
    BASE_URL = "https://api.alternative.me/fng/"

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0),
            headers={
                "Accept": "application/json",
                "User-Agent": "AlgoTradingBot/1.0",
            },
        )

    async def fetch_latest(self) -> dict:
        try:
            response = await self.client.get(
                self.BASE_URL,
                params={"limit": 1, "format": "json"},
            )
            response.raise_for_status()

            payload = response.json()

            if payload.get("metadata", {}).get("error"):
                raise ValueError(payload["metadata"]["error"])

            records = payload.get("data", [])

            if not records:
                raise ValueError("Fear & Greed API returned no data")

            record = records[0]

            value = int(record["value"])
            timestamp = int(record["timestamp"])
            classification = record["value_classification"]

            if not 0 <= value <= 100:
                raise ValueError("Fear & Greed value is outside 0-100")

            return {
                "value": value,
                "classification": classification,
                "timestamp": timestamp,
                "observed_at": datetime.fromtimestamp(
                    timestamp,
                    tz=timezone.utc,
                ),
                "source": "alternative.me",
                "status": "success",
            }

        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            return {
                "value": None,
                "classification": None,
                "timestamp": None,
                "observed_at": None,
                "source": "alternative.me",
                "status": "failed",
                "error": str(exc),
            }

    async def close(self):
        await self.client.aclose()
