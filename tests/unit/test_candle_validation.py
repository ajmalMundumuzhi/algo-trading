
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.agents.market_data.validator import validate_candle, validate_candles
from app.agents.market_data.candle_filter import filter_closed_candles
from app.agents.news_sentiment.market_context import get_market_context


def make_candle(timestamp=None, **overrides):
    candle = {
        "timestamp": timestamp or datetime.now(timezone.utc) - timedelta(hours=2),
        "open": 100,
        "high": 110,
        "low": 90,
        "close": 105,
        "volume": 1000,
    }
    candle.update(overrides)
    return candle


class FakeResult:
    def __init__(self, records):
        self.records = records

    def scalars(self):
        return self

    def all(self):
        return self.records


class FakeDatabase:
    def __init__(self, asset, candles):
        self.results = [FakeResult([asset]), FakeResult(candles)]

    def execute(self, query):
        return self.results.pop(0)


def test_valid_candle_is_accepted():
    assert validate_candle(make_candle()) is True


def test_invalid_ohlc_candle_is_rejected():
    candle = make_candle(high=95)
    assert validate_candle(candle) is False


def test_future_timestamp_is_rejected():
    candle = make_candle(
        timestamp=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    assert validate_candle(candle) is False


def test_validate_candles_removes_invalid_records():
    valid = make_candle()
    invalid = make_candle(low=120)

    result = validate_candles([valid, invalid])

    assert result == [valid]


def test_incomplete_candle_is_filtered():
    now = datetime(2026, 11, 19, 12, 30, tzinfo=timezone.utc)

    candles = [
        {"timestamp": now - timedelta(hours=2)},
        {"timestamp": now - timedelta(minutes=30)},
    ]

    result = filter_closed_candles(candles, "1h", now)

    assert len(result) == 1
    assert result[0]["timestamp"] == now - timedelta(hours=2)


def test_candle_at_closing_boundary_is_included():
    now = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)

    candles = [
        {"timestamp": now - timedelta(hours=1)}
    ]

    result = filter_closed_candles(candles, "1h", now)

    assert len(result) == 1


def test_stale_market_context_is_detected():
    asset = SimpleNamespace(
        id="asset-1",
        name="Bitcoin",
        symbol="BTC",
        is_active=True,
    )

    now = datetime.now(timezone.utc)
    latest = SimpleNamespace(
        timestamp=now - timedelta(hours=5),
        close=100,
        volume=500,
    )
    previous = SimpleNamespace(
        timestamp=now - timedelta(hours=6),
        close=95,
        volume=600,
    )

    db = FakeDatabase(asset, [latest, previous])

    result = get_market_context(
        db=db,
        symbol="BTC",
        timeframe="1h",
        asset_name="Bitcoin",
    )

    assert result["status"] == "stale"
    assert result["latest_candle_price"] == 100
    assert result["candle_age_minutes"] is not None


def test_recent_market_context_is_available():
    asset = SimpleNamespace(
        id="asset-1",
        name="Bitcoin",
        symbol="BTC",
        is_active=True,
    )

    now = datetime.now(timezone.utc)
    latest = SimpleNamespace(
        timestamp=now - timedelta(minutes=30),
        close=100,
        volume=500,
    )
    previous = SimpleNamespace(
        timestamp=now - timedelta(hours=1, minutes=30),
        close=95,
        volume=600,
    )

    db = FakeDatabase(asset, [latest, previous])

    result = get_market_context(
        db=db,
        symbol="BTC",
        timeframe="1h",
        asset_name="Bitcoin",
    )

    assert result["status"] == "available"
    assert result["latest_candle_price"] == 100
