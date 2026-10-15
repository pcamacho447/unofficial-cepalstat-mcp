"""Analysis and investigative module for statscepal."""

from statscepal.analysis.econometrics import EconometricEstimator
from statscepal.analysis.metrics import (
    classify_quadrant,
    compute_decoupling_score,
    compute_elasticity,
    compute_food_wage_gap,
)
from statscepal.analysis.models import (
    CountryPeriodMetric,
    DecouplingDataset,
    RegressionModelSummary,
)
from statscepal.analysis.service import (
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


