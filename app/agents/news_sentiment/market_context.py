
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.models.market_asset import MarketAsset
from app.models.market_candle import MarketCandle


TIMEFRAME_DURATIONS = {
    "1m": timedelta(minutes=1),
    "3m": timedelta(minutes=3),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "2h": timedelta(hours=2),
    "4h": timedelta(hours=4),
    "6h": timedelta(hours=6),
    "12h": timedelta(hours=12),
    "1d": timedelta(days=1),
}


def _to_float(value):
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    return float(value)


def _unavailable_context(symbol, timeframe, reason):
    return {
        "status": "unavailable",
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "reason": reason,
        "latest_candle_price": None,
        "previous_candle_price": None,
        "price_change_pct": None,
        "volume": None,
        "latest_candle_timestamp": None,
        "candle_age_minutes": None,
    }


def get_market_context(
    db,
    symbol: str,
    timeframe: str = "1h",
    asset_name: str | None = None,
) -> dict:
    symbol = symbol.strip().upper()

    if timeframe not in TIMEFRAME_DURATIONS:
        return _unavailable_context(
            symbol,
            timeframe,
            "Unsupported timeframe",
        )

    asset_query = select(MarketAsset).where(
        func.upper(MarketAsset.symbol) == symbol,
        MarketAsset.is_active.is_(True),
    )

    assets = db.execute(asset_query).scalars().all()

    if asset_name:
        matching_assets = [
            asset
            for asset in assets
            if asset.name.strip().lower() == asset_name.strip().lower()
        ]

        if matching_assets:
            assets = matching_assets

    if not assets:
        return _unavailable_context(
            symbol,
            timeframe,
            "No active matching asset found",
        )

    if len(assets) > 1:
        return {
            **_unavailable_context(
                symbol,
                timeframe,
                "Multiple active assets share this symbol",
            ),
            "status": "ambiguous",
        }

    asset = assets[0]

    candle_query = (
        select(MarketCandle)
        .where(
            MarketCandle.asset_id == asset.id,
            MarketCandle.timeframe == timeframe,
        )
        .order_by(MarketCandle.timestamp.desc())
        .limit(2)
    )

    candles = db.execute(candle_query).scalars().all()

    if not candles:
        return _unavailable_context(
            symbol,
            timeframe,
            "No stored candles found for this asset and timeframe",
        )

    latest = candles[0]
    previous = candles[1] if len(candles) > 1 else None

    latest_price = _to_float(latest.close)
    previous_price = _to_float(previous.close) if previous else None

    price_change_pct = None

    if previous_price not in (None, 0) and latest_price is not None:
        price_change_pct = (
            (latest_price - previous_price) / previous_price
        ) * 100

    now = datetime.now(timezone.utc)
    candle_timestamp = latest.timestamp

    if candle_timestamp.tzinfo is None:
        candle_timestamp = candle_timestamp.replace(tzinfo=timezone.utc)

    candle_end_time = (
        candle_timestamp + TIMEFRAME_DURATIONS[timeframe]
    )

    age_minutes = max(
        0,
        (now - candle_end_time).total_seconds() / 60,
    )

    stale_after = TIMEFRAME_DURATIONS[timeframe] * 3
    status = (
        "stale"
        if now - candle_end_time > stale_after
        else "available"
    )

    return {
        "status": status,
        "symbol": symbol,
        "asset_name": asset.name,
        "timeframe": timeframe,
        "latest_candle_price": latest_price,
        "previous_candle_price": previous_price,
        "price_change_pct": (
            round(price_change_pct, 4)
            if price_change_pct is not None
            else None
        ),
        "volume": _to_float(latest.volume),
        "latest_candle_timestamp": latest.timestamp.isoformat(),
        "candle_age_minutes": round(age_minutes, 2),
    }
