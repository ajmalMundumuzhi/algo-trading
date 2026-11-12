import httpx 
from app.core.config import settings

class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"
    def __init__(self):
        api_key = settings.coingecko_api_key

        if not api_key:
            raise ValueError("CoinGecko API key is not configured.")

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "x-cg-demo-api-key": api_key.get_secret_value()
            },
            timeout=30.0
        )
    
    async def get_top_coins(self, limit: int = 200):
        response = await self.client.get(
            "/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": min(limit, 250),
                "page": 1,
                "sparkline": "false",
            },
        )

        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()