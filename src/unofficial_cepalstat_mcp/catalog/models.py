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


class HarvestRecord(BaseModel):
    """Record of an indicator dimension harvest."""

    indicator_id: int
    dimension_count: int
    member_count: int
    content_hash: str | None = None
    harvested_at: str | None = None


class HarvestSummary(BaseModel):
    """Summary of a catalog dimension harvesting run."""

    total_target: int = 0
    already_harvested: int = 0
    newly_harvested: int = 0
    failed_ids: list[int] = Field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def failed_count(self) -> int:
        return len(self.failed_ids)

