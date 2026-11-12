from datetime import datetime, timezone

async def fetch_market_snapshot(
        exchange,
        symbol: str,
        timeframe: str = "1hr",
        limit: int = 100,
):
    ticker = await exchange.fetch_ticker(symbol)

    raw_candles = await exchange.fetch_ohlcv(
        symbol, 
        timeframe=timeframe,
        limit=limit,
    )

    candles = []
    for candle in raw_candles:
        timestamp,open_price, high, low, close, volume = candle

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
        "candles": candles,
    }