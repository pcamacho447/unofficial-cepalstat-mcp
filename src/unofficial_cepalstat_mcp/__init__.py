"""statscepal: Python client for UN CEPALSTAT Open Data API."""

__version__ = "0.1.0"

from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.exceptions import (
    CepalStatAPIError,
    CepalStatError,
    CepalStatNetworkError,
)
from unofficial_cepalstat_mcp.dimensions import Dimension, DimensionManager, Member
from unofficial_cepalstat_mcp.extractor import DataExtractor
from unofficial_cepalstat_mcp.thematic_tree import IndicatorItem, ThematicTree

__all__ = [
    "__version__",
    "CepalStatClient",
    "CepalStatError",
    "CepalStatNetworkError",
    "CepalStatAPIError",
    "DataExtractor",
    "Dimension",
    "DimensionManager",
    "IndicatorItem",
    "Member",
    "ThematicTree",
]

