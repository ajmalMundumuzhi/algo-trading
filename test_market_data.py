
import asyncio

from app.integrations.exchange import create_exchange_client
from app.integrations.market_data.coingecko import CoinGeckoClient
from app.agents.market_data.universe import build_trading_universe
from app.agents.market_data.collector import fetch_market_snapshot


async def main():
    exchange = create_exchange_client()
    coingecko = CoinGeckoClient()

    try:
        print("Loading Binance markets...")
        markets = await exchange.load_markets()

        print("Fetching Binance ticker data...")
        tickers = await exchange.fetch_tickers()

        print("Fetching CoinGecko top 200...")
        coins = await coingecko.get_top_coins(200)

        print("Fetching complete CoinGecko coin list...")
        all_coins = await coingecko.get_coin_list()

        print("Building trading universe...")

        universe = build_trading_universe(
            coins,
            markets,
            tickers,
            all_coins,
        )

        print("\nEligible assets:", len(universe))

        print("\nTop 10 eligible assets:")

        for asset in universe[:10]:
            print(
                asset["name"],
                asset["symbol"],
                asset["binance_pair"],
                asset["quote_volume_24h"],
            )

        print("\nFetching BTC/USDT market snapshot...")

        data = await fetch_market_snapshot(
            exchange,
            symbol="BTC/USDT",
            timeframe="1h",
            limit=100,
        )

        print("\nTicker:")
        print(data["ticker"])

        print("\nCandles retrieved:", len(data["candles"]))
        print("Rejected candles:", data["rejected_candles"])
        print("Incomplete candles:", data["incomplete_candles"])

        print("\nLatest 5 candles:")

        for candle in data["candles"][-5:]:
            print(candle)

    finally:
        await exchange.close()
        await coingecko.close()


if __name__ == "__main__":
    asyncio.run(main())
