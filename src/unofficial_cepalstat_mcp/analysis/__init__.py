"""Analysis and investigative module for statscepal."""

from unofficial_cepalstat_mcp.analysis.econometrics import EconometricEstimator
from unofficial_cepalstat_mcp.analysis.metrics import (
    classify_quadrant,
    compute_decoupling_score,
    compute_elasticity,
    compute_food_wage_gap,
)
from unofficial_cepalstat_mcp.analysis.models import (
    CountryPeriodMetric,
    DecouplingDataset,
    RegressionModelSummary,
)
from unofficial_cepalstat_mcp.analysis.service import (
    COUNTRY_MEMBER_MAP,
    FOOD_INFLATION_MEMBER_MAP,
    DecouplingAnalyzer,
)

__all__ = [
    "COUNTRY_MEMBER_MAP",
    "CountryPeriodMetric",
    "DecouplingAnalyzer",
    "DecouplingDataset",
    "EconometricEstimator",
    "FOOD_INFLATION_MEMBER_MAP",
    "RegressionModelSummary",
    "classify_quadrant",
    "compute_decoupling_score",
    "compute_elasticity",
    "compute_food_wage_gap",
]


