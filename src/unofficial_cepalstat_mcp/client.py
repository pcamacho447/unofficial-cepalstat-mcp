"""HTTP client for the CEPALSTAT API."""

from typing import Any

import httpx

from unofficial_cepalstat_mcp.exceptions import CepalStatAPIError, CepalStatNetworkError

DEFAULT_BASE_URL = "https://api-cepalstat.cepal.org"
DEFAULT_TIMEOUT = 30.0


class CepalStatClient:
    """Core HTTP client for interacting with the CEPALSTAT REST API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        lang: str = "es",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.lang = lang
        self.timeout = timeout
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

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request expecting JSON."""
        clean_endpoint = "/" + endpoint.lstrip("/")
        query_params: dict[str, Any] = {"lang": self.lang, "format": "json"}
        if params:
            query_params.update(params)

        try:
            response = self._client.get(clean_endpoint, params=query_params)
        except httpx.RequestError as exc:
            raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc

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
            return response.json()
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
    ) -> bytes:
        """Make a GET request expecting raw bytes (CSV, Excel, etc.)."""
        clean_endpoint = "/" + endpoint.lstrip("/")
        query_params: dict[str, Any] = {"lang": self.lang, "format": response_format}
        if params:
            query_params.update(params)

        try:
            response = self._client.get(clean_endpoint, params=query_params)
        except httpx.RequestError as exc:
            raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc

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

        return response.content
