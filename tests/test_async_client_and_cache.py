import asyncio
import time

import httpx
import pytest
import respx

from unofficial_cepalstat_mcp.client import (
    AsyncCepalStatClient,
    CepalStatClient,
    _BoundedTTLCache,
)
from unofficial_cepalstat_mcp.exceptions import CepalStatAPIError, CepalStatNetworkError


@respx.mock
def test_sync_client_caches_ttl_and_retries_429(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda _: None)
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/127/metadata").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "rate limit"}),
            httpx.Response(200, json={"body": {"metadata": {"name": "Desocupación"}}}),
        ]
    )
    with CepalStatClient(cache_ttl_seconds=60.0, max_retries=3) as client:
        first = client.get("/cepalstat/api/v1/indicator/127/metadata")
        second = client.get("/cepalstat/api/v1/indicator/127/metadata")
    assert first == second
    assert route.call_count == 2  # 1 retry after 429 + 1 cached hit (no 3rd HTTP call)


@respx.mock
def test_async_client_fetches_and_caches_without_blocking(monkeypatch) -> None:
    async def _noop_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", _noop_sleep)
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/365/metadata").mock(
        side_effect=[
            httpx.Response(503, text="unavailable"),
            httpx.Response(200, json={"body": {"metadata": {"name": "IPC"}}}),
        ]
    )

    async def _run() -> dict:
        async with AsyncCepalStatClient(cache_ttl_seconds=60.0, max_retries=3) as client:
            await client.get("/cepalstat/api/v1/indicator/365/metadata")
            return await client.get("/cepalstat/api/v1/indicator/365/metadata")

    result = asyncio.run(_run())
    assert result["body"]["metadata"]["name"] == "IPC"
    assert route.call_count == 2


def test_bounded_ttl_cache_eviction() -> None:
    cache: _BoundedTTLCache = _BoundedTTLCache(ttl_seconds=0.1, max_entries=2)
    cache.set("k1", "v1")
    cache.set("k2", "v2")
    assert cache.get("k1") == "v1"
    assert cache.get("k2") == "v2"

    # LRU eviction: setting k3 when max_entries=2 should evict k1 (since k2 was accessed most recently)
    cache.set("k3", "v3")
    assert cache.get("k1") is None
    assert cache.get("k2") == "v2"
    assert cache.get("k3") == "v3"

    # TTL eviction
    time.sleep(0.12)
    assert cache.get("k2") is None
    assert cache.get("k3") is None


@respx.mock
def test_sync_client_exhausts_retries_and_raises(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda _: None)
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/overload").mock(
        return_value=httpx.Response(502, text="Bad Gateway")
    )
    with CepalStatClient(cache_ttl_seconds=60.0, max_retries=2) as client:
        with pytest.raises(CepalStatAPIError) as exc_info:
            client.get("/cepalstat/api/v1/overload")
        assert exc_info.value.status_code == 502


@respx.mock
def test_async_client_raw_and_network_error(monkeypatch) -> None:
    async def _noop_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", _noop_sleep)
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/export").mock(
        return_value=httpx.Response(200, content=b"col1,col2\nval1,val2\n")
    )
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/timeout").mock(
        side_effect=httpx.ConnectTimeout("Async connection timed out")
    )

    async def _run() -> None:
        async with AsyncCepalStatClient(cache_ttl_seconds=60.0, max_retries=2) as client:
            raw1 = await client.get_raw("/cepalstat/api/v1/export", response_format="csv")
            raw2 = await client.get_raw("/cepalstat/api/v1/export", response_format="csv")
            assert raw1 == raw2 == b"col1,col2\nval1,val2\n"

            with pytest.raises(CepalStatNetworkError):
                await client.get("/cepalstat/api/v1/timeout")

    asyncio.run(_run())
