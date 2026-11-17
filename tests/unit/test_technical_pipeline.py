
import asyncio

from datetime import datetime, timedelta, timezone

from app.agents.technical.pipeline import run_technical_analysis


class MockExchange:
    async def fetch_ticker(self, symbol):
        return {
            "last": 100,
            "bid": 99.9,
            "ask": 100.1,
            "high": 105,
            "low": 95,
            "baseVolume": 1000,
            "quoteVolume": 100000,
        }

    async def fetch_ohlcv(self, symbol, timeframe, limit):
        now = datetime.now(timezone.utc)
        candles = []

        for i in range(limit):
            timestamp = int(
                (
                    now - timedelta(hours=limit - i + 1)
                ).timestamp() * 1000
            )

            close = 100 + i * 0.2

            candles.append([
                timestamp,
                close - 0.1,
                close + 0.5,
                close - 0.5,
                close,
                1000 + i * 10,
            ])

        return candles


def test_market_data_connects_to_technical_analysis():
    async def run_test():
        exchange = MockExchange()

        result = await run_technical_analysis(
            exchange=exchange,
            symbol="BTC/USDT",
            timeframe="1h",
            limit=100,
        )

        assert result["status"] == "ok"
        assert result["symbol"] == "BTC/USDT"

        assert result["market_data"]["candles_received"] >= 51

        technical = result["technical_analysis"]

        assert technical["status"] == "ok"
        assert technical["indicators"]["ema_fast"] is not None
        assert technical["indicators"]["ema_slow"] is not None
        assert technical["indicators"]["rsi"] is not None

        assert technical["technical_score"]["status"] == "ok"

    asyncio.run(run_test())
