from datetime import datetime, timedelta, timezone

from app.agents.market_data.candle_filter import filter_closed_candles

now = datetime(2026, 11, 12, 12, 30, tzinfo=timezone.utc)

candles = [
    {
        "timestamp": now - timedelta(hours=2),
        "close": 100,
    },
    {
        "timestamp": now - timedelta(minutes=30),
        "close": 105,
    },
]

closed = filter_closed_candles(
    candles,
    timeframe="1h",
    now=now,
)

print("Total candles:", len(candles))
print("Closed candles:", len(closed))
print("Closed candle close:", closed[0]["close"])