from datetime import datetime, timedelta, timezone

TIMEFRAME_DURATIONS = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
}


def filter_closed_candles(
    candles: list[dict],
    timeframe: str,
    now: datetime | None = None,
) -> list[dict]:

    duration = TIMEFRAME_DURATIONS.get(timeframe)

    if duration is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    current_time = now or datetime.now(timezone.utc)

    if current_time.tzinfo is None:
        raise ValueError("Current time must be timezone-aware")

    return [
        candle
        for candle in candles
        if candle["timestamp"] + duration <= current_time
    ]