
import math
from datetime import datetime


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def validate_technical_candles(candles):
    if candles is None or candles.empty:
        raise ValueError("Candle data is empty")

    missing = REQUIRED_COLUMNS - set(candles.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    data = candles.copy()

    for column in ("open", "high", "low", "close", "volume"):
        data[column] = __import__("pandas").to_numeric(
            data[column],
            errors="coerce",
        )

        if not data[column].map(
            lambda value: math.isfinite(float(value))
        ).all():
            raise ValueError(
                f"Invalid numeric values in {column}"
            )

    for timestamp in data["timestamp"]:
        if not isinstance(timestamp, datetime):
            raise ValueError("Invalid candle timestamp")

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Candle timestamps must be timezone-aware")

    if data["timestamp"].duplicated().any():
        raise ValueError("Duplicate candle timestamps detected")

    if not data["timestamp"].is_monotonic_increasing:
        raise ValueError("Candles must be sorted by timestamp")

    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Candle prices must be positive")

    if (data["volume"] < 0).any():
        raise ValueError("Candle volume cannot be negative")

    invalid_high = data["high"] < data[
        ["open", "close", "low"]
    ].max(axis=1)

    invalid_low = data["low"] > data[
        ["open", "close", "high"]
    ].min(axis=1)

    if invalid_high.any() or invalid_low.any():
        raise ValueError("Invalid OHLC candle relationships")

    return data.reset_index(drop=True)
