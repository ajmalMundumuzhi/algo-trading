
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def validate_candle(candle: dict) -> bool:
    required_fields = ("timestamp", "open", "high", "low", "close", "volume")

    if not all(field in candle for field in required_fields):
        return False

    timestamp = candle["timestamp"]

    if not isinstance(timestamp, datetime):
        return False

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return False

    if timestamp > datetime.now(timezone.utc):
        return False

    try:
        open_price = Decimal(str(candle["open"]))
        high = Decimal(str(candle["high"]))
        low = Decimal(str(candle["low"]))
        close = Decimal(str(candle["close"]))
        volume = Decimal(str(candle["volume"]))
    except (InvalidOperation, TypeError, ValueError):
        return False

    prices = (open_price, high, low, close)

    if not all(price.is_finite() for price in prices):
        return False

    if not volume.is_finite():
        return False

    if any(price <= 0 for price in prices):
        return False

    if volume < 0:
        return False

    if high < max(open_price, close, low):
        return False

    if low > min(open_price, close, high):
        return False

    return True


def validate_candles(candles: list[dict]) -> list[dict]:
    return [candle for candle in candles if validate_candle(candle)]
