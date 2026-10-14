"""Data models for Master Indicator Catalog."""

from pydantic import BaseModel, Field


class CatalogIndicator(BaseModel):
    """An indicator indexed in the master catalog."""

    indicator_id: int
    name: str
    order_num: int | None = None
    theme: str = ""
    area: str = ""
    subarea: str = ""
    full_path: str = ""
    updated_at: str = ""


class CatalogStats(BaseModel):
    """Statistical summary of the master catalog."""

    total_indicators: int
    themes_count: int = 0
    areas_count: int = 0
    by_theme: dict[str, int] = Field(default_factory=dict)
