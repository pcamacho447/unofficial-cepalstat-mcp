"""Pydantic data models for Bitácora recipes and anti-bias auditing."""

from pydantic import BaseModel, Field


class DataQualityReport(BaseModel):
    """Statistical quality summary of the downloaded dataset."""

    total_records: int
    null_count: int = 0
    null_ratio: float = 0.0
    has_gaps: bool = False
    min_year: int | None = None
    max_year: int | None = None
    min_value: float | None = None
    max_value: float | None = None


class AntiBiasChecklist(BaseModel):
    """Methodological anti-bias checklist and warnings."""

    unit_verified: bool = True
    scale_factor_note: str = ""
    is_projection: bool = False
    base_year_split: int | None = None
    warnings: list[str] = Field(default_factory=list)


class BitacoraRecipe(BaseModel):
    """A verified, reusable query recipe in the Bitácora."""

    id: str
    indicator_id: int
    indicator_name: str
    country: str
    country_iso3: str = ""
    country_member_id: int | None = None
    theme: str = ""
    unit: str = ""
    member_ids: list[int] = Field(default_factory=list)
    python_code: str = ""
    status: str = "certified"  # certified | draft
    date_certified: str = ""
    tags: list[str] = Field(default_factory=list)
    quality_report: DataQualityReport | None = None
    antibias: AntiBiasChecklist | None = None
