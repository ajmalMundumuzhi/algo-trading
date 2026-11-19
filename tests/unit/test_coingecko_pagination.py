
import asyncio

import httpx
import pytest

from app.integrations.market_data.coingecko import CoinGeckoClient


def test_get_top_coins_fetches_multiple_pages():
    client = CoinGeckoClient.__new__(CoinGeckoClient)
    requested_pages = []

    async def mock_request(endpoint, params):
        requested_pages.append(params["page"])
        return [{"id": f"coin-{params['page']}"}] * params["per_page"]

    client._get_with_retry = mock_request

    result = asyncio.run(client.get_top_coins(limit=300))

    assert len(result) == 300
    assert requested_pages == [1, 2]


def test_coingecko_retries_after_http_429(monkeypatch):
    client = CoinGeckoClient.__new__(CoinGeckoClient)
    client.MAX_ATTEMPTS = 3

    responses = [
        httpx.Response(429, request=httpx.Request("GET", "https://test.com")),
        httpx.Response(200, json={"status": "success"}, request=httpx.Request("GET", "https://test.com")),
    ]
    attempts = []
    delays = []

    class FakeHTTPClient:
        async def get(self, endpoint, params):
            attempts.append(endpoint)
            return responses.pop(0)

    async def fake_sleep(delay):
        delays.append(delay)

    client.client = FakeHTTPClient()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = asyncio.run(client._get_with_retry("/test", {}))

    assert result == {"status": "success"}
    assert len(attempts) == 2
    assert delays == [1]


def test_coingecko_retries_after_http_500(monkeypatch):
    client = CoinGeckoClient.__new__(CoinGeckoClient)
    client.MAX_ATTEMPTS = 3

    responses = [
        httpx.Response(500, request=httpx.Request("GET", "https://test.com")),
        httpx.Response(200, json={"status": "success"}, request=httpx.Request("GET", "https://test.com")),
    ]
    delays = []

    class FakeHTTPClient:
        async def get(self, endpoint, params):
            return responses.pop(0)

    async def fake_sleep(delay):
        delays.append(delay)

    client.client = FakeHTTPClient()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = asyncio.run(client._get_with_retry("/test", {}))

    assert result == {"status": "success"}
    assert delays == [1]


def test_coingecko_does_not_retry_http_400(monkeypatch):
    client = CoinGeckoClient.__new__(CoinGeckoClient)
    client.MAX_ATTEMPTS = 3
    attempts = []

    class FakeHTTPClient:
        async def get(self, endpoint, params):
            attempts.append(endpoint)
            return httpx.Response(
                400,
                request=httpx.Request("GET", "https://test.com"),
            )

    async def fake_sleep(delay):
        pytest.fail("HTTP 400 should not be retried")

    client.client = FakeHTTPClient()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(client._get_with_retry("/test", {}))

    assert len(attempts) == 1


def test_coingecko_retries_after_network_error(monkeypatch):
    client = CoinGeckoClient.__new__(CoinGeckoClient)
    client.MAX_ATTEMPTS = 3
    attempts = []
    delays = []

    class FakeHTTPClient:
        async def get(self, endpoint, params):
            attempts.append(endpoint)

            if len(attempts) == 1:
                raise httpx.ConnectError("Network unavailable")

            return httpx.Response(
                200,
                json={"status": "success"},
                request=httpx.Request("GET", "https://test.com"),
            )

    async def fake_sleep(delay):
        delays.append(delay)

    client.client = FakeHTTPClient()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = asyncio.run(client._get_with_retry("/test", {}))

    assert result == {"status": "success"}
    assert len(attempts) == 2
    assert delays == [1]
