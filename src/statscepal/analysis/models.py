"""Data models for growth-wellbeing decoupling analysis."""

from typing import Any
from pydantic import BaseModel, Field


class CountryPeriodMetric(BaseModel):
    """Metrics for a single country across an analysis period."""

    country: str
    period_label: str
    years_range: str
    gdp_pc_growth_mean: float
    poverty_total_change_pp: float | None = None
    poverty_extreme_change_pp: float | None = None
    real_min_wage_change_pct: float | None = None
    gini_change: float | None = None
    social_elasticity: float | None = None
    quadrant: str = "Indeterminado"


class DecouplingDataset(BaseModel):
    """Consolidated dataset of decoupling analysis."""

    records: list[CountryPeriodMetric] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
