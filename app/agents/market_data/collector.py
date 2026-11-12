import ccxt.async_support as ccxt
from datetime import datetime, timezone

from app.agents.market_data.validator import validate_candles
from app.agents.market_data.candle_filter import filter_closed_candles
from app.utils.retry import retry_async


RETRYABLE_EXCHANGE_ERRORS = (
    ccxt.NetworkError,
    ccxt.ExchangeNotAvailable,
    ccxt.RequestTimeout,
    ccxt.DDoSProtection,
    ccxt.RateLimitExceeded,
)


async def fetch_market_snapshot(
    exchange,
    symbol: str,
    timeframe: str = "1h",
    limit: int = 100,
):
    ticker = await retry_async(
        lambda: exchange.fetch_ticker(symbol),
        retry_on=RETRYABLE_EXCHANGE_ERRORS,
    )

    raw_candles = await retry_async(
        lambda: exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit,
        ),
        retry_on=RETRYABLE_EXCHANGE_ERRORS,
    )

    candles = []

    for candle in raw_candles:
        timestamp, open_price, high, low, close, volume = candle

        candles.append({
            "timestamp": datetime.fromtimestamp(
                timestamp / 1000,
                tz=timezone.utc,
            ),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })

    valid_candles = validate_candles(candles)
    closed_candles = filter_closed_candles(valid_candles, timeframe)

    return {
        "symbol": symbol,
        "ticker": {
            "last": ticker.get("last"),
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
            "high": ticker.get("high"),
            "low": ticker.get("low"),
            "base_volume": ticker.get("baseVolume"),
            "quote_volume": ticker.get("quoteVolume"),
        },
        "candles": closed_candles,
        "rejected_candles": len(candles) - len(valid_candles),
        "incomplete_candles": len(valid_candles) - len(closed_candles),
    }