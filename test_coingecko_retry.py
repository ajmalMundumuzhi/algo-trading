import asyncio
import httpx

from app.integrations.market_data.coingecko import CoinGeckoClient


attempts = 0


async def mock_api(request):
    global attempts
    attempts += 1

    if attempts == 1:
        return httpx.Response(
            429,
            headers={"Retry-After": "1"},
            json={"error": "Rate limit exceeded"},
        )

    return httpx.Response(
        200,
        json=[
            {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
            {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
        ],
    )


async def main():
    global attempts

    client = object.__new__(CoinGeckoClient)

    client.client = httpx.AsyncClient(
        base_url=CoinGeckoClient.BASE_URL,
        transport=httpx.MockTransport(mock_api),
    )

    try:
        coins = await client.get_top_coins(limit=2)

        print("Total attempts:", attempts)
        print("Coins retrieved:", len(coins))
        print("First coin:", coins[0]["name"])

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())