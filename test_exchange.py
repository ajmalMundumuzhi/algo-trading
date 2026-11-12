
import asyncio

from app.integrations.exchange import create_exchange_client


async def main():
    exchange = create_exchange_client()

    try:
        print("Exchange:", exchange.id)

        await exchange.load_markets()

        print("Connection successful!")
        print("Exchange:", exchange.name)
        print("Total markets:", len(exchange.markets))

        spot_markets = [
            symbol
            for symbol, market in exchange.markets.items()
            if market.get("spot") and market.get("active")
        ]

        print("Active spot markets:", len(spot_markets))
        print("Sample markets:", spot_markets[:10])

    except Exception as error:
        print("Exchange connection failed!")
        print(type(error).__name__, str(error))

    finally:
        await exchange.close()


asyncio.run(main())
