"""Exceptions for unofficial_cepalstat_mcp."""

from typing import Any


class CepalStatError(Exception):
    """Base exception for all unofficial_cepalstat_mcp errors."""


class CepalStatNetworkError(CepalStatError):
    """Raised when network transport fails."""


class CepalStatAPIError(CepalStatError):
    """Raised when the CEPALSTAT API returns an error status code or invalid response."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
