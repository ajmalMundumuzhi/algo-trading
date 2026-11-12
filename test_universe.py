import asyncio

from app.agents.market_data.universe import build_trading_universe
from app.integrations.exchange import create_exchange_client
from app.integrations.market_data.coingecko import CoinGeckoClient


async def main():
    exchange = create_exchange_client()
    coingecko = CoinGeckoClient()

    try:
        print("Loading Binance markets...")
        markets = await exchange.load_markets()

        print("Fetching CoinGecko top 200...")
        coins = await coingecko.get_top_coins(200)

        universe = build_trading_universe(coins, markets)

        print("\nTrading universe created!")
        print("Eligible USDT pairs:", len(universe))

        print("\nTop 20 eligible assets:")

        for coin in universe[:20]:
            print(
                coin["market_cap_rank"],
                coin["name"],
                coin["symbol"],
                coin["binance_pair"],
            )

    finally:
        await exchange.close()
        await coingecko.close()


if __name__ == "__main__":
    asyncio.run(main())