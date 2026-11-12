
from datetime import datetime, timezone

from app.agents.market_data.validator import (
    validate_candle,
    validate_candles,
)

valid_candle = {
    "timestamp": datetime.now(timezone.utc),
    "open": 100,
    "high": 110,
    "low": 95,
    "close": 105,
    "volume": 500,
}

invalid_candle = {
    "timestamp": datetime.now(timezone.utc),
    "open": 100,
    "high": 90,
    "low": 95,
    "close": 105,
    "volume": 500,
}

print("Valid candle:", validate_candle(valid_candle))
print("Invalid candle:", validate_candle(invalid_candle))

results = validate_candles([valid_candle, invalid_candle])
print("Valid candles:", len(results))

print(
    "Invalid timestamp:",
    validate_candle({
        "timestamp": "not-a-date",
        "open": 100,
        "high": 110,
        "low": 95,
        "close": 105,
        "volume": 500,
    })
)
from datetime import datetime, timezone, timedelta

naive_timestamp_candle = {
    **valid_candle,
    "timestamp": datetime.now(),
}

future_timestamp_candle = {
    **valid_candle,
    "timestamp": datetime.now(timezone.utc) + timedelta(hours=1),
}

print("Naive timestamp:", validate_candle(naive_timestamp_candle))
print("Future timestamp:", validate_candle(future_timestamp_candle))