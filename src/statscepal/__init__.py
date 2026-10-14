"""statscepal: Python client for UN CEPALSTAT Open Data API."""

__version__ = "0.1.0"

from statscepal.client import CepalStatClient
from statscepal.exceptions import (
    CepalStatAPIError,
    CepalStatError,
    CepalStatNetworkError,
)

__all__ = [
    "__version__",
    "CepalStatClient",
    "CepalStatError",
    "CepalStatNetworkError",
    "CepalStatAPIError",
]
