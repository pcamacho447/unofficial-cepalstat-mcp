"""HTTP client for the CEPALSTAT API."""

import asyncio
import time
from collections import OrderedDict
from typing import Any

import httpx

from unofficial_cepalstat_mcp.exceptions import CepalStatAPIError, CepalStatNetworkError

DEFAULT_BASE_URL = "https://api-cepalstat.cepal.org"
DEFAULT_TIMEOUT = 30.0
RETRY_STATUS_CODES: set[int] = {429, 502, 503, 504}


class _BoundedTTLCache:
    """Lightweight bounded in-memory LRU/TTL cache."""

    def __init__(self, ttl_seconds: float = 300.0, max_entries: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._cache: OrderedDict[Any, tuple[float, Any]] = OrderedDict()

    def get(self, key: Any) -> Any | None:
        if self.ttl_seconds <= 0 or self.max_entries <= 0:
            return None
        if key not in self._cache:
            return None
        ts, val = self._cache[key]
        if time.monotonic() - ts > self.ttl_seconds:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return val

    def set(self, key: Any, value: Any) -> None:
        if self.ttl_seconds <= 0 or self.max_entries <= 0:
            return
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self.max_entries:
            self._cache.popitem(last=False)
        self._cache[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


def _make_cache_key(
    endpoint: str, query_params: dict[str, Any]
) -> tuple[str, tuple[tuple[str, Any], ...]]:
    def _freeze(val: Any) -> Any:
        if isinstance(val, list):
            return tuple(_freeze(v) for v in val)
        if isinstance(val, dict):
            return tuple(sorted((k, _freeze(v)) for k, v in val.items()))
        return val

    return (endpoint, tuple(sorted((k, _freeze(v)) for k, v in query_params.items())))


def _calculate_backoff(
    attempt: int,
    retry_backoff_base: float,
    response: httpx.Response | None = None,
    max_backoff: float = 5.0,
) -> float:
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                seconds = float(retry_after.strip())
                if seconds >= 0:
                    return min(seconds, max_backoff)
            except (ValueError, TypeError):
                pass
    backoff = retry_backoff_base * (2**attempt)
    return float(min(float(backoff), max_backoff))


class CepalStatClient:
    """Core HTTP client for interacting with the CEPALSTAT REST API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        lang: str = "es",
        timeout: float = DEFAULT_TIMEOUT,
        cache_ttl_seconds: float = 300.0,
        max_cache_entries: int = 256,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.lang = lang
        self.timeout = timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_cache_entries = max_cache_entries
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self._cache = _BoundedTTLCache(ttl_seconds=cache_ttl_seconds, max_entries=max_cache_entries)
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        self._client.close()

    def __enter__(self) -> "CepalStatClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()

    def clear_cache(self) -> None:
        """Clear all entries from the internal TTL cache."""
        self._cache.clear()

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Make a GET request expecting JSON."""
        clean_endpoint = "/" + endpoint.lstrip("/")
        query_params: dict[str, Any] = {"lang": self.lang, "format": "json"}
        if params:
            query_params.update(params)

        cache_key = _make_cache_key(clean_endpoint, query_params)
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None and isinstance(cached, dict):
                return cached

        attempt = 0
        while True:
            response: httpx.Response | None = None
            try:
                response = self._client.get(clean_endpoint, params=query_params)
            except httpx.TransportError as exc:
                if attempt < self.max_retries:
                    delay = _calculate_backoff(attempt, self.retry_backoff_base, None)
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc
            except httpx.RequestError as exc:
                raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc

            if response.status_code in RETRY_STATUS_CODES and attempt < self.max_retries:
                delay = _calculate_backoff(attempt, self.retry_backoff_base, response)
                time.sleep(delay)
                attempt += 1
                continue

            if response.status_code >= 400:
                response_data = None
                try:
                    response_data = response.json()
                except Exception:
                    pass
                raise CepalStatAPIError(
                    f"CEPALSTAT API error {response.status_code}: {response.text}",
                    status_code=response.status_code,
                    response_data=response_data,
                )

            try:
                data = response.json()
                if not isinstance(data, dict):
                    raise CepalStatAPIError(
                        f"Expected JSON object response, got: {type(data).__name__}",
                        status_code=response.status_code,
                    )
                self._cache.set(cache_key, data)
                return data
            except CepalStatAPIError:
                raise
            except Exception as exc:
                raise CepalStatAPIError(
                    f"Invalid JSON returned: {response.text}",
                    status_code=response.status_code,
                ) from exc

    def get_raw(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        response_format: str = "csv",
        force_refresh: bool = False,
    ) -> bytes:
        """Make a GET request expecting raw bytes (CSV, Excel, etc.)."""
        clean_endpoint = "/" + endpoint.lstrip("/")
        query_params: dict[str, Any] = {"lang": self.lang, "format": response_format}
        if params:
            query_params.update(params)

        cache_key = _make_cache_key(clean_endpoint, query_params)
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None and isinstance(cached, bytes):
                return cached

        attempt = 0
        while True:
            response: httpx.Response | None = None
            try:
                response = self._client.get(clean_endpoint, params=query_params)
            except httpx.TransportError as exc:
                if attempt < self.max_retries:
                    delay = _calculate_backoff(attempt, self.retry_backoff_base, None)
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc
            except httpx.RequestError as exc:
                raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc

            if response.status_code in RETRY_STATUS_CODES and attempt < self.max_retries:
                delay = _calculate_backoff(attempt, self.retry_backoff_base, response)
                time.sleep(delay)
                attempt += 1
                continue

            if response.status_code >= 400:
                response_data = None
                try:
                    response_data = response.json()
                except Exception:
                    pass
                raise CepalStatAPIError(
                    f"CEPALSTAT API error {response.status_code}: {response.text}",
                    status_code=response.status_code,
                    response_data=response_data,
                )

            content = response.content
            self._cache.set(cache_key, content)
            return content


class AsyncCepalStatClient:
    """Async HTTP client for interacting with the CEPALSTAT REST API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        lang: str = "es",
        timeout: float = DEFAULT_TIMEOUT,
        cache_ttl_seconds: float = 300.0,
        max_cache_entries: int = 256,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.lang = lang
        self.timeout = timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_cache_entries = max_cache_entries
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self._cache = _BoundedTTLCache(ttl_seconds=cache_ttl_seconds, max_entries=max_cache_entries)
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    def clear_cache(self) -> None:
        """Clear all entries from the internal TTL cache."""
        self._cache.clear()

    async def aclose(self) -> None:
        """Close the underlying async HTTP client session."""
        await self._client.aclose()

    async def close(self) -> None:
        """Alias for aclose()."""
        await self.aclose()

    async def __aenter__(self) -> "AsyncCepalStatClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.aclose()

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Make an async GET request expecting JSON."""
        clean_endpoint = "/" + endpoint.lstrip("/")
        query_params: dict[str, Any] = {"lang": self.lang, "format": "json"}
        if params:
            query_params.update(params)

        cache_key = _make_cache_key(clean_endpoint, query_params)
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None and isinstance(cached, dict):
                return cached

        attempt = 0
        while True:
            response: httpx.Response | None = None
            try:
                response = await self._client.get(clean_endpoint, params=query_params)
            except httpx.TransportError as exc:
                if attempt < self.max_retries:
                    delay = _calculate_backoff(attempt, self.retry_backoff_base, None)
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc
            except httpx.RequestError as exc:
                raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc

            if response.status_code in RETRY_STATUS_CODES and attempt < self.max_retries:
                delay = _calculate_backoff(attempt, self.retry_backoff_base, response)
                await asyncio.sleep(delay)
                attempt += 1
                continue

            if response.status_code >= 400:
                response_data = None
                try:
                    response_data = response.json()
                except Exception:
                    pass
                raise CepalStatAPIError(
                    f"CEPALSTAT API error {response.status_code}: {response.text}",
                    status_code=response.status_code,
                    response_data=response_data,
                )

            try:
                data = response.json()
                if not isinstance(data, dict):
                    raise CepalStatAPIError(
                        f"Expected JSON object response, got: {type(data).__name__}",
                        status_code=response.status_code,
                    )
                self._cache.set(cache_key, data)
                return data
            except CepalStatAPIError:
                raise
            except Exception as exc:
                raise CepalStatAPIError(
                    f"Invalid JSON returned: {response.text}",
                    status_code=response.status_code,
                ) from exc

    async def get_raw(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        response_format: str = "csv",
        force_refresh: bool = False,
    ) -> bytes:
        """Make an async GET request expecting raw bytes (CSV, Excel, etc.)."""
        clean_endpoint = "/" + endpoint.lstrip("/")
        query_params: dict[str, Any] = {"lang": self.lang, "format": response_format}
        if params:
            query_params.update(params)

        cache_key = _make_cache_key(clean_endpoint, query_params)
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None and isinstance(cached, bytes):
                return cached

        attempt = 0
        while True:
            response: httpx.Response | None = None
            try:
                response = await self._client.get(clean_endpoint, params=query_params)
            except httpx.TransportError as exc:
                if attempt < self.max_retries:
                    delay = _calculate_backoff(attempt, self.retry_backoff_base, None)
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc
            except httpx.RequestError as exc:
                raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc

            if response.status_code in RETRY_STATUS_CODES and attempt < self.max_retries:
                delay = _calculate_backoff(attempt, self.retry_backoff_base, response)
                await asyncio.sleep(delay)
                attempt += 1
                continue

            if response.status_code >= 400:
                response_data = None
                try:
                    response_data = response.json()
                except Exception:
                    pass
                raise CepalStatAPIError(
                    f"CEPALSTAT API error {response.status_code}: {response.text}",
                    status_code=response.status_code,
                    response_data=response_data,
                )

            content = response.content
            self._cache.set(cache_key, content)
            return content
