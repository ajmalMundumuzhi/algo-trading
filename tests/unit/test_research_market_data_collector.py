
import asyncio
from types import SimpleNamespace

from app.agents.research import market_data_collector as collector


def make_candidate(
    coin_id="bitcoin",
    name="Bitcoin",
    symbol="btc",
):
    return {
        "id": coin_id,
        "name": name,
        "symbol": symbol,
        "market_cap_rank": 1,
        "market_cap": 1_000_000_000,
    }


def make_exchange(
    markets=None,
    tickers=None,
    load_error=None,
):
    class FakeExchange:
        async def load_markets(self):
            if load_error:
                raise load_error

            return markets or {}

        async def fetch_tickers(self):
            return tickers or {}

    return FakeExchange()


def make_market_data():
    markets = {
        "BTC/USDT": {
            "spot": True,
            "active": True,
            "base": "BTC",
            "quote": "USDT",
        }
    }

    tickers = {
        "BTC/USDT": {
            "quoteVolume": 5_000_000,
        }
    }

    return markets, tickers


class FakeSession:
    def __init__(self, results=None):
        self.results = list(results or [])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement):
        value = self.results.pop(0)

        return SimpleNamespace(
            scalar_one_or_none=lambda: value
        )


def test_research_market_data_collection_success(monkeypatch):
    candidate = make_candidate()
    markets, tickers = make_market_data()

    fake_asset = SimpleNamespace(
        id="fake-asset-id",
        coingecko_id="bitcoin",
    )

    session_calls = []

    def fake_session_local():
        session = FakeSession(
            results=[None, fake_asset]
        )
        session_calls.append(session)
        return session

    monkeypatch.setattr(
        collector,
        "SessionLocal",
        fake_session_local,
    )

    monkeypatch.setattr(
        collector,
        "upsert_assets",
        lambda db, assets: len(assets),
    )

    monkeypatch.setattr(
        collector,
        "upsert_candles",
        lambda **kwargs: len(kwargs["candles"]),
    )

    async def fake_snapshot(**kwargs):
        return {
            "candles": [
                {
                    "timestamp": "2026-11-18T10:00:00+00:00",
                    "open": 90000,
                    "high": 91000,
                    "low": 89000,
                    "close": 90500,
                    "volume": 100,
                }
            ],
            "rejected_candles": 0,
            "incomplete_candles": 1,
        }

    monkeypatch.setattr(
        collector,
        "fetch_market_snapshot",
        fake_snapshot,
    )

    result = asyncio.run(
        collector.collect_research_market_data(
            candidates=[candidate],
            exchange=make_exchange(markets, tickers),
            all_coins=[candidate],
        )
    )

    assert result["status"] == "success"
    assert result["assets_matched"] == 1
    assert result["assets_saved"] == 1
    assert result["candles_saved"] == 1
    assert result["results"][0]["status"] == "available"
    assert result["results"][0]["binance_pair"] == "BTC/USDT"


def test_rejects_ambiguous_coingecko_symbol():
    candidate = make_candidate()

    duplicate_coin = make_candidate(
        coin_id="another-bitcoin",
        name="Another Bitcoin",
        symbol="btc",
    )

    markets, tickers = make_market_data()

    result = asyncio.run(
        collector.collect_research_market_data(
            candidates=[candidate],
            exchange=make_exchange(markets, tickers),
            all_coins=[candidate, duplicate_coin],
        )
    )

    assert result["assets_matched"] == 0
    assert result["assets_unavailable"] == 1
    assert result["results"][0]["status"] == "unavailable"
    assert result["results"][0]["reason"] == (
        "CoinGecko symbol is ambiguous"
    )


def test_rejects_low_liquidity_pair():
    candidate = make_candidate()
    markets, tickers = make_market_data()

    tickers["BTC/USDT"]["quoteVolume"] = 500_000

    result = asyncio.run(
        collector.collect_research_market_data(
            candidates=[candidate],
            exchange=make_exchange(markets, tickers),
            all_coins=[candidate],
        )
    )

    assert result["assets_matched"] == 0
    assert result["assets_unavailable"] == 1
    assert result["results"][0]["status"] == "unavailable"
    assert "liquidity requirements" in result["results"][0]["reason"]


def test_rejects_pair_owned_by_another_asset(monkeypatch):
    candidate = make_candidate()
    markets, tickers = make_market_data()

    existing_owner = SimpleNamespace(
        coingecko_id="another-coin",
        binance_pair="BTC/USDT",
    )

    monkeypatch.setattr(
        collector,
        "SessionLocal",
        lambda: FakeSession(results=[existing_owner]),
    )

    monkeypatch.setattr(
        collector,
        "upsert_assets",
        lambda db, assets: 1,
    )

    result = asyncio.run(
        collector.collect_research_market_data(
            candidates=[candidate],
            exchange=make_exchange(markets, tickers),
            all_coins=[candidate],
        )
    )

    assert result["assets_matched"] == 0
    assert result["assets_unavailable"] == 1
    assert result["results"][0]["status"] == "unavailable"
    assert "already assigned" in result["results"][0]["reason"]


def test_exchange_api_failure_returns_error():
    candidate = make_candidate()

    exchange = make_exchange(
        load_error=RuntimeError("Binance API unavailable")
    )

    result = asyncio.run(
        collector.collect_research_market_data(
            candidates=[candidate],
            exchange=exchange,
            all_coins=[candidate],
        )
    )

    assert result["status"] == "failed"
    assert result["assets_failed"] == 1
    assert result["results"][0]["status"] == "error"
    assert result["results"][0]["reason"] == (
        "Failed to load exchange markets or tickers"
    )
