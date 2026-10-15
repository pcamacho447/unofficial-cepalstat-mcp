"""Analysis and investigative module for statscepal."""

from statscepal.analysis.econometrics import EconometricEstimator
from statscepal.analysis.metrics import (
    classify_quadrant,
    compute_decoupling_score,
    compute_elasticity,
)
from statscepal.analysis.models import (
    CountryPeriodMetric,
    DecouplingDataset,
    RegressionModelSummary,
)
from statscepal.analysis.service import DecouplingAnalyzer

__all__ = [
    "CountryPeriodMetric",
    "DecouplingAnalyzer",
    "DecouplingDataset",
    "EconometricEstimator",
    "RegressionModelSummary",
    "classify_quadrant",
    "compute_decoupling_score",
    "compute_elasticity",
]

