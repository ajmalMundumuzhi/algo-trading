
import asyncio

import pytest

from app.utils.retry import retry_async


def test_retry_async_succeeds_after_transient_failures(monkeypatch):
    attempts = {"count": 0}
    delays = []

    async def operation():
        attempts["count"] += 1

        if attempts["count"] < 3:
            raise ConnectionError("Temporary network failure")

        return "success"

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = asyncio.run(
        retry_async(
            operation,
            retries=3,
            base_delay=1,
            retry_on=(ConnectionError,),
        )
    )

    assert result == "success"
    assert attempts["count"] == 3
    assert delays == [1, 2]


def test_retry_async_raises_after_all_attempts(monkeypatch):
    attempts = {"count": 0}

    async def operation():
        attempts["count"] += 1
        raise ConnectionError("Network unavailable")

    async def fake_sleep(delay):
        pass

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with pytest.raises(ConnectionError):
        asyncio.run(
            retry_async(
                operation,
                retries=3,
                base_delay=1,
                retry_on=(ConnectionError,),
            )
        )

    assert attempts["count"] == 4


def test_retry_async_does_not_retry_unlisted_exception(monkeypatch):
    attempts = {"count": 0}

    async def operation():
        attempts["count"] += 1
        raise ValueError("Invalid input")

    async def fake_sleep(delay):
        pytest.fail("Unexpected retry")

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with pytest.raises(ValueError):
        asyncio.run(
            retry_async(
                operation,
                retries=3,
                retry_on=(ConnectionError,),
            )
        )

    assert attempts["count"] == 1
