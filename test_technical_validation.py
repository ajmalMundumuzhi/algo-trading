
import pandas as pd
from datetime import datetime, timezone, timedelta

from app.agents.technical.data_validation import (
    validate_technical_candles,
)


timestamps = pd.date_range(
    start="2026-01-01",
    periods=60,
    freq="1h",
    tz="UTC",
)

candles = pd.DataFrame({
    "timestamp": timestamps,
    "open": [100.0] * 60,
    "high": [110.0] * 60,
    "low": [95.0] * 60,
    "close": [105.0] * 60,
    "volume": [1000.0] * 60,
})

valid = validate_technical_candles(candles)
print("Valid candles:", len(valid))

invalid_price = candles.copy()
invalid_price.loc[10, "high"] = 90

try:
    validate_technical_candles(invalid_price)
    raise AssertionError("Invalid OHLC candle was accepted")
except ValueError:
    print("Invalid OHLC: rejected")

duplicate = candles.copy()
duplicate.loc[10, "timestamp"] = duplicate.loc[9, "timestamp"]

try:
    validate_technical_candles(duplicate)
    raise AssertionError("Duplicate timestamp was accepted")
except ValueError:
    print("Duplicate timestamp: rejected")

unsorted = candles.copy()
unsorted.loc[10, "timestamp"], unsorted.loc[11, "timestamp"] = (
    unsorted.loc[11, "timestamp"],
    unsorted.loc[10, "timestamp"],
)

try:
    validate_technical_candles(unsorted)
    raise AssertionError("Unsorted candles were accepted")
except ValueError:
    print("Unsorted candles: rejected")

invalid_volume = candles.copy()
invalid_volume.loc[10, "volume"] = -100

try:
    validate_technical_candles(invalid_volume)
    raise AssertionError("Negative volume was accepted")
except ValueError:
    print("Negative volume: rejected")

invalid_number = candles.copy()
invalid_number.loc[10, "close"] = float("nan")

try:
    validate_technical_candles(invalid_number)
    raise AssertionError("NaN price was accepted")
except ValueError:
    print("NaN price: rejected")

naive_timestamp = candles.copy()

naive_timestamp["timestamp"] = naive_timestamp[
    "timestamp"
].astype(object)

naive_timestamp.loc[10, "timestamp"] = datetime.now()

try:
    validate_technical_candles(naive_timestamp)
    raise AssertionError("Naive timestamp was accepted")
except ValueError:
    print("Naive timestamp: rejected")

print("\nAll technical validation tests passed!")
