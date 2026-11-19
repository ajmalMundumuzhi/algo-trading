
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.market_data.pipeline import run_market_data_pipeline


def make_universe():
    return [
        {
            "coingecko_id": "bitcoin",
            "name": "Bitcoin",
            "symbol": "BTC",
            "binance_pair": "BTC/USDT",
        },
        {
            "coingecko_id": "ethereum",
            "name": "Ethereum",
            "symbol": "ETH",
            "binance_pair": "ETH/USDT",
        },
    ]


def make_snapshot():
    return {
        "candles": [
            {
                "timestamp": "2026-11-18T10:00:00+00:00",
                "open": 100,
                "high": 105,
                "low": 99,
                "close": 103,
                "volume": 1000,
            }
        ],
        "rejected_candles": 1,
        "incomplete_candles": 1,
    }


def setup_successful_pipeline():
    coingecko = MagicMock()
    coingecko.get_top_coins = AsyncMock(return_value=[{"id": "bitcoin"}])
    coingecko.get_coin_list = AsyncMock(return_value=[] )
    coingecko.close = AsyncMock()

    exchange = MagicMock()
    exchange.id = "binance"
    exchange.timeframes = {"1h": "1h"}
    exchange.load_markets = AsyncMock(return_value={"BTC/USDT": {}})
    exchange.fetch_tickers = AsyncMock(return_value={})
    exchange.close = AsyncMock()

    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = False

    saved_asset = SimpleNamespace(
        coingecko_id="bitcoin",
        id="asset-uuid-1",
    )

    session.execute.return_value.scalars.return_value.all.return_value = [
        saved_asset
    ]

    return coingecko, exchange, session


def test_market_data_pipeline_success():
    async def run_test():
        coingecko, exchange, session = setup_successful_pipeline()
        universe = make_universe()

        with (
            patch(
                "app.agents.market_data.pipeline.CoinGeckoClient",
                return_value=coingecko,
            ),
            patch(
                "app.agents.market_data.pipeline.create_exchange_client",
                return_value=exchange,
            ),
            patch(
                "app.agents.market_data.pipeline.SessionLocal",
                return_value=session,
            ),
            patch(
                "app.agents.market_data.pipeline.build_trading_universe",
                return_value=universe,
            ),
            patch(
                "app.agents.market_data.pipeline.upsert_assets",
                return_value=2,
            ) as mock_upsert_assets,
            patch(
                "app.agents.market_data.pipeline.fetch_market_snapshot",
                new=AsyncMock(return_value=make_snapshot()),
            ),
            patch(
                "app.agents.market_data.pipeline.upsert_candles",
                return_value=1,
            ) as mock_upsert_candles,
        ):
            result = await run_market_data_pipeline()

        assert result["status"] == "partial"
        assert result["coins_retrieved"] == 1
        assert result["universe_size"] == 2
        assert result["assets_saved"] == 2
        assert result["assets_processed"] == 1
        assert result["assets_failed"] == 1
        assert result["candles_saved"] == 1
        assert result["candles_rejected"] == 1
        assert result["candles_incomplete"] == 1

        mock_upsert_assets.assert_called_once()
        mock_upsert_candles.assert_called_once()

        exchange.close.assert_awaited_once()
        coingecko.close.assert_awaited_once()

    asyncio.run(run_test())


def test_market_data_pipeline_no_eligible_assets():
    async def run_test():
        coingecko, exchange, session = setup_successful_pipeline()

        with (
            patch(
                "app.agents.market_data.pipeline.CoinGeckoClient",
                return_value=coingecko,
            ),
            patch(
                "app.agents.market_data.pipeline.create_exchange_client",
                return_value=exchange,
            ),
            patch(
                "app.agents.market_data.pipeline.SessionLocal",
                return_value=session,
            ),
            patch(
                "app.agents.market_data.pipeline.build_trading_universe",
                return_value=[],
            ),
        ):
            result = await run_market_data_pipeline()

        assert result["status"] == "no_eligible_assets"
        assert result["universe_size"] == 0
        assert result["assets_saved"] == 0

        exchange.close.assert_awaited_once()
        coingecko.close.assert_awaited_once()

    asyncio.run(run_test())


def test_market_data_pipeline_unsupported_timeframe():
    async def run_test():
        coingecko, exchange, session = setup_successful_pipeline()
        exchange.timeframes = {"1h": "1h"}

        with (
            patch(
                "app.agents.market_data.pipeline.CoinGeckoClient",
                return_value=coingecko,
            ),
            patch(
                "app.agents.market_data.pipeline.create_exchange_client",
                return_value=exchange,
            ),
        ):
            result = await run_market_data_pipeline(timeframe="5m")

        assert result["status"] == "failed"
        assert "not supported" in result["errors"][0]["error"]

        exchange.close.assert_awaited_once()
        coingecko.close.assert_awaited_once()

    asyncio.run(run_test())


def test_market_data_pipeline_invalid_limits():
    async def run_test():
        result = await run_market_data_pipeline(coin_limit=0)

        assert result["status"] == "failed"
        assert "must be positive" in result["errors"][0]["error"]

    asyncio.run(run_test())


def test_market_data_pipeline_coin_collection_failure():
    async def run_test():
        coingecko = MagicMock()
        coingecko.get_top_coins = AsyncMock(
            side_effect=RuntimeError("CoinGecko API unavailable")
        )
        coingecko.close = AsyncMock()

        exchange = MagicMock()
        exchange.close = AsyncMock()

        with (
            patch(
                "app.agents.market_data.pipeline.CoinGeckoClient",
                return_value=coingecko,
            ),
            patch(
                "app.agents.market_data.pipeline.create_exchange_client",
                return_value=exchange,
            ),
        ):
            result = await run_market_data_pipeline()

        assert result["status"] == "failed"
        assert "CoinGecko API unavailable" in result["errors"][0]["error"]

        exchange.close.assert_awaited_once()
        coingecko.close.assert_awaited_once()

    asyncio.run(run_test())
