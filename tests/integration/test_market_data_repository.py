
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.agents.market_data.repository import (
    upsert_assets,
    upsert_candles,
)
from app.core.database import SessionLocal
from app.models.market_asset import MarketAsset
from app.models.market_candle import MarketCandle


def test_market_asset_and_candle_persistence():
    test_id = "integration-test-bitcoin"

    timestamp = datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc)

    asset_data = {
        "coingecko_id": test_id,
        "name": "Integration Test Bitcoin",
        "symbol": "TESTBTC",
        "binance_pair": "TESTBTC/USDT",
        "market_cap_rank": 999999,
        "market_cap": 1000000,
    }

    candle_data = [{
        "timestamp": timestamp,
        "open": 100,
        "high": 105,
        "low": 99,
        "close": 103,
        "volume": 1000,
    }]

    try:
        with SessionLocal() as db:
            upsert_assets(db, [asset_data])

            asset = db.execute(
                select(MarketAsset).where(
                    MarketAsset.coingecko_id == test_id
                )
            ).scalar_one()

            asset_id = asset.id

            assert asset.name == "Integration Test Bitcoin"
            assert asset.symbol == "TESTBTC"

            upsert_candles(
                db=db,
                asset_id=asset_id,
                symbol="TESTBTC/USDT",
                timeframe="1h",
                candles=candle_data,
            )

            candle = db.execute(
                select(MarketCandle).where(
                    MarketCandle.symbol == "TESTBTC/USDT",
                    MarketCandle.timeframe == "1h",
                    MarketCandle.timestamp == timestamp,
                )
            ).scalar_one()

            assert candle.asset_id == asset_id
            assert candle.open == Decimal("100")
            assert candle.high == Decimal("105")
            assert candle.low == Decimal("99")
            assert candle.close == Decimal("103")
            assert candle.volume == Decimal("1000")

            updated_candle = [{
                **candle_data[0],
                "close": 104,
            }]

            upsert_candles(
                db=db,
                asset_id=asset_id,
                symbol="TESTBTC/USDT",
                timeframe="1h",
                candles=updated_candle,
            )

            db.expire_all()

            updated_record = db.execute(
                select(MarketCandle).where(
                    MarketCandle.symbol == "TESTBTC/USDT",
                    MarketCandle.timeframe == "1h",
                    MarketCandle.timestamp == timestamp,
                )
            ).scalar_one()

            assert updated_record.close == Decimal("104")

    finally:
        with SessionLocal() as db:
            db.query(MarketCandle).filter(
                MarketCandle.symbol == "TESTBTC/USDT"
            ).delete()

            db.query(MarketAsset).filter(
                MarketAsset.coingecko_id == test_id
            ).delete()

            db.commit()
