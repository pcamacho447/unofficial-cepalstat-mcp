"""Unit tests for the EconometricEstimator engine."""

import pytest

from unofficial_cepalstat_mcp.analysis.econometrics import EconometricEstimator
from unofficial_cepalstat_mcp.analysis.models import (
    CountryPeriodMetric,
    DecouplingDataset,
    RegressionModelSummary,
)


def _build_synthetic_dataset(n_samples: int = 12) -> DecouplingDataset:
    """Generate synthetic DecouplingDataset for econometric testing."""
    records = []
    countries = ["Argentina", "Chile", "Colombia", "México", "Perú", "Uruguay"]
    periods = [("2015-2019", "2015-2019"), ("2021-2023", "2021-2023")]

    count = 0
    for p_label, p_range in periods:
        for c in countries:
            if count >= n_samples:
                break
            # Deterministic synthetic values exhibiting economic logic:
            # higher GDP growth & wage reduce poverty; food inflation increases poverty
            gdp = 1.0 + (count % 4) * 0.8
            wage = -2.0 + (count % 3) * 3.0
            food = 3.0 + (count % 5) * 2.5
            poverty_chg = round(-0.4 * gdp - 0.2 * wage + 0.3 * food, 2)

            records.append(
                CountryPeriodMetric(
                    country=c,
                    period_label=p_label,
                    years_range=p_range,
                    gdp_pc_growth_mean=round(gdp, 2),
                    poverty_total_change_pp=poverty_chg,
                    real_min_wage_change_pct=round(wage, 2),
                    food_inflation_mean_pct=round(food, 2),
                    social_elasticity=-0.5,
                    quadrant="Crecimiento Virtuoso" if poverty_chg < 0 else "Crecimiento Excluyente",
                )
            )
            count += 1

    return DecouplingDataset(records=records, metadata={"source": "synthetic_test"})


def test_fit_poverty_growth_model_normal_dataset():
    """Verify OLS model estimation with a valid synthetic dataset."""
    dataset = _build_synthetic_dataset(12)
    summary = EconometricEstimator.fit_poverty_growth_model(dataset)

    assert isinstance(summary, RegressionModelSummary)
    assert summary.n_obs == 12
    assert 0.0 <= summary.r_squared <= 1.0
    assert 0.0 <= summary.r_squared_adj <= 1.0

    expected_params = {
        "const",
        "gdp_pc_growth_mean",
        "real_min_wage_change_pct",
        "food_inflation_mean_pct",
    }
    assert set(summary.coefficients.keys()) == expected_params
    assert set(summary.p_values.keys()) == expected_params
    assert set(summary.std_errors.keys()) == expected_params
    assert set(summary.confidence_intervals.keys()) == expected_params

    for param, pval in summary.p_values.items():
        assert 0.0 <= pval <= 1.0

    for param, (low, high) in summary.confidence_intervals.items():
        assert low <= high


def test_fit_poverty_growth_model_small_dataset():
    """Verify graceful minimal summary returned when N < 4."""
    dataset = _build_synthetic_dataset(3)
    summary = EconometricEstimator.fit_poverty_growth_model(dataset)

    assert isinstance(summary, RegressionModelSummary)
    assert summary.n_obs == 3
    assert summary.r_squared == 0.0
    assert summary.r_squared_adj == 0.0
    assert summary.coefficients == {}
    assert summary.p_values == {}
    assert summary.std_errors == {}
    assert summary.confidence_intervals == {}
    assert summary.f_pvalue == 1.0


def test_fit_poverty_growth_model_empty_dataset():
    """Verify graceful handling of empty dataset."""
    dataset = DecouplingDataset(records=[])
    summary = EconometricEstimator.fit_poverty_growth_model(dataset)

    assert isinstance(summary, RegressionModelSummary)
    assert summary.n_obs == 0
    assert summary.r_squared == 0.0
    assert summary.coefficients == {}


def test_fit_poverty_growth_model_missing_values():
    """Verify handling of missing dependent and independent variables."""
    base_dataset = _build_synthetic_dataset(12)
    records = list(base_dataset.records)

    # Make 2 records have missing dependent variable (poverty)
    records[0].poverty_total_change_pp = None
    records[1].poverty_total_change_pp = None

    # Make 2 records have missing wage or food inflation
    records[2].real_min_wage_change_pct = None
    records[3].food_inflation_mean_pct = None

    dataset = DecouplingDataset(records=records)

    # 1. Default / impute_missing=False: drops all rows with any missing regression variable
    # Total 12 - 2 (poverty None) - 2 (predictors None) = 8 usable rows
    summary_drop = EconometricEstimator.fit_poverty_growth_model(dataset, impute_missing=False)
    assert summary_drop.n_obs == 8
    assert summary_drop.r_squared > 0.0
    assert "food_inflation_mean_pct" in summary_drop.coefficients

    # 2. impute_missing=True: imputes 0.0 for wage and food inflation
    # Total 12 - 2 (poverty None) = 10 usable rows
    summary_impute = EconometricEstimator.fit_poverty_growth_model(dataset, impute_missing=True)
    assert summary_impute.n_obs == 10
    assert summary_impute.r_squared > 0.0
    assert "real_min_wage_change_pct" in summary_impute.coefficients


def test_fit_poverty_growth_model_instance_call():
    """Verify that EconometricEstimator can be used as an instance or class."""
    estimator = EconometricEstimator()
    dataset = _build_synthetic_dataset(12)
    summary = estimator.fit_poverty_growth_model(dataset)

    assert isinstance(summary, RegressionModelSummary)
    assert summary.n_obs == 12
