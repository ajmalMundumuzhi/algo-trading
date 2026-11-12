from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.market_asset import MarketAsset
from app.models.market_candle import MarketCandle

def upsert_assets(db: Session, assets: list[dict]) -> int:
    if not assets:
        return 0

    records = []

    for asset in assets:
        market_cap = asset.get("market_cap")

        records.append({
            "coingecko_id": asset["coingecko_id"],
            "name": asset["name"],
            "symbol": asset["symbol"],
            "binance_pair": asset["binance_pair"],
            "market_cap_rank": asset.get("market_cap_rank"),
            "market_cap": (
                Decimal(str(market_cap))
                if market_cap is not None
                else None
            ),
            "is_active": True,
        })
    statement = insert(MarketAsset).values(records)

    statement = statement.on_conflict_do_update(
        index_elements=[MarketAsset.coingecko_id],
        set_={
            "name": statement.excluded.name,
            "symbol": statement.excluded.symbol,
            "binance_pair": statement.excluded.binance_pair,
            "market_cap_rank": statement.excluded.market_cap_rank,
            "market_cap": statement.excluded.market_cap,
            "is_active": True,
            "updated_at": func.now(),
        },
    )

    try:
        result = db.execute(statement)
        db.commit()
        return result.rowcount or 0
    except Exception:
        db.rollback()
        raise

def upsert_candles(
    db: Session,
    asset_id: UUID,
    symbol: str,
    timeframe: str,
    candles: list[dict],
) -> int:
    if not candles:
        return 0

    records = []

    for candle in candles:
        records.append({
            "asset_id": asset_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": candle["timestamp"],
            "open": Decimal(str(candle["open"])),
            "high": Decimal(str(candle["high"])),
            "low": Decimal(str(candle["low"])),
            "close": Decimal(str(candle["close"])),
            "volume": Decimal(str(candle["volume"]))
        })

    statement = insert(MarketCandle).values(records)

    statement = statement.on_conflict_do_update(
        constraint="uq_market_candle_symbol_timeframe_timestamp",
        set_={
            "open": statement.excluded.open,
            "high": statement.excluded.high,
            "low": statement.excluded.low,
            "close": statement.excluded.close,
            "volume": statement.excluded.volume,
            "updated_at": func.now()
        },
    )

    try:
        result = db.execute(statement)
        db.commit()
        return result.rowcount or 0
    except Exception:
        db.rollback()
        raise