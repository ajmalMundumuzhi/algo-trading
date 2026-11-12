
import asyncio

from app.integrations.market_data.coingecko import CoinGeckoClient


async def main():
    client = CoinGeckoClient()

    try:
        coins = await client.get_top_coins(200)

        print("CoinGecko connection successful!")
        print("Coins retrieved:", len(coins))

        for coin in coins[:10]:
            print(
                coin["market_cap_rank"],
                coin["name"],
                coin["symbol"].upper(),
                coin["market_cap"],
                coin["total_volume"],
            )

    except Exception as error:
        print("CoinGecko request failed!")
        print(type(error).__name__, str(error))

    finally:
        await client.close()


asyncio.run(main())
