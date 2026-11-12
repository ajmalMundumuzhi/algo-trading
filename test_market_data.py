import asyncio

from app.integrations.exchange import create_exchange_client
from app.agents.market_data.collector import fetch_market_snapshot


async def main():
    exchange = create_exchange_client()

    try:
        await exchange.load_markets()

        data = await fetch_market_snapshot(
            exchange,
            symbol="BTC/USDT",
            timeframe="1h",
            limit=100,
        )

        print("\nTicker:")
        print(data["ticker"])

        print("\nCandles retrieved:", len(data["candles"]))

        print("\nLatest 5 candles:")

        for candle in data["candles"][-5:]:
            print(candle)

    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(main())