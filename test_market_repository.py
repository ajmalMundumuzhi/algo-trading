
import asyncio

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.market_asset import MarketAsset
from app.models.market_candle import MarketCandle

from app.integrations.exchange import create_exchange_client
from app.integrations.market_data.coingecko import CoinGeckoClient

from app.agents.market_data.universe import build_trading_universe
from app.agents.market_data.collector import fetch_market_snapshot
from app.agents.market_data.repository import upsert_assets, upsert_candles


async def main():
    exchange = create_exchange_client()
    coingecko = CoinGeckoClient()
    db = SessionLocal()

    try:
        print("Loading Binance markets...")
        markets = await exchange.load_markets()

        print("Fetching Binance ticker data...")
        tickers = await exchange.fetch_tickers()

        print("Fetching CoinGecko top 200...")
        coins = await coingecko.get_top_coins(200)

        universe = build_trading_universe(coins, markets, tickers)

        print("Eligible assets:", len(universe))

        print("\nSaving assets...")
        upsert_assets(db, universe)

        bitcoin = db.scalar(
            select(MarketAsset).where(
                MarketAsset.coingecko_id == "bitcoin"
            )
        )

        if bitcoin is None:
            raise RuntimeError("Bitcoin asset was not saved")

        print("Bitcoin saved:", bitcoin.binance_pair)
        print("Bitcoin database ID:", bitcoin.id)

        print("\nFetching BTC/USDT candles...")

        snapshot = await fetch_market_snapshot(
            exchange,
            symbol="BTC/USDT",
            timeframe="1h",
            limit=100,
        )

        candles = snapshot["candles"]
        
        print("Closed candles:", len(candles))
        print("Rejected candles:", snapshot["rejected_candles"])
        print("Incomplete candles:", snapshot["incomplete_candles"])

        print("Valid candles:", len(candles))
        print("Rejected candles:", snapshot["rejected_candles"])

        print("\nFirst database insertion...")

        first_insert = upsert_candles(
            db,
            bitcoin.id,
            "BTC/USDT",
            "1h",
            candles,
        )

        print("Rows processed:", first_insert)

        count_after_first = db.scalar(
            select(func.count())
            .select_from(MarketCandle)
            .where(
                MarketCandle.symbol == "BTC/USDT",
                MarketCandle.timeframe == "1h",
            )
        )

        print("Database candle count:", count_after_first)

        print("\nSecond insertion of the same candles...")

        second_insert = upsert_candles(
            db,
            bitcoin.id,
            "BTC/USDT",
            "1h",
            candles,
        )

        print("Rows processed:", second_insert)

        count_after_second = db.scalar(
            select(func.count())
            .select_from(MarketCandle)
            .where(
                MarketCandle.symbol == "BTC/USDT",
                MarketCandle.timeframe == "1h",
            )
        )

        print("Database candle count:", count_after_second)

        if count_after_first == count_after_second:
            print("\nSUCCESS: No duplicate candles created!")
        else:
            print("\nERROR: Candle count changed unexpectedly!")

    finally:
        db.close()
        await exchange.close()
        await coingecko.close()


if __name__ == "__main__":
    asyncio.run(main())
