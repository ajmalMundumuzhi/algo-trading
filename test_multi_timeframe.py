
import pandas as pd

from app.agents.technical.multi_timeframe import (
    analyze_multiple_timeframes,
)


timestamps = pd.date_range(
    start="2026-01-01",
    periods=100,
    freq="1h",
    tz="UTC",
)

candles = pd.DataFrame({
    "timestamp": timestamps,
    "open": [100 + i for i in range(100)],
    "high": [102 + i for i in range(100)],
    "low": [99 + i for i in range(100)],
    "close": [101 + i for i in range(100)],
    "volume": [1000] * 100,
})

snapshots = {
    "15m": candles.to_dict("records"),
    "1h": candles.to_dict("records"),
    "4h": [],
    "1d": [
        {
            "timestamp": "invalid",
            "open": 100,
            "high": 110,
            "low": 90,
            "close": 105,
            "volume": 1000,
        }
    ],
}

result = analyze_multiple_timeframes(
    snapshots=snapshots,
    symbol="BTC/USDT",
)

print("Successful:", result["successful_timeframes"])
print("Total:", result["total_timeframes"])
print("Failed:", result["failed_timeframes"])

assert result["timeframes"]["15m"]["status"] == "ok"
assert result["timeframes"]["1h"]["status"] == "ok"
assert result["timeframes"]["4h"]["status"] == "unavailable"
assert result["timeframes"]["1d"]["status"] == "analysis_error"

assert result["successful_timeframes"] == 2
assert result["total_timeframes"] == 4

print("\nAll multi-timeframe tests passed!")
