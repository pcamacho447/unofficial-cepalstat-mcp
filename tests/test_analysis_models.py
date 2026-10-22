from unofficial_cepalstat_mcp.analysis import (
    CountryPeriodMetric,
    DecouplingDataset,
    RegressionModelSummary,
)


def test_country_period_metric_creation():
    metric = CountryPeriodMetric(
        country="Argentina",
        period_label="P2: 2021-2023",
        years_range="2021-2023",
        gdp_pc_growth_mean=4.60,
        poverty_total_change_pp=1.8,
        poverty_extreme_change_pp=0.2,
        real_min_wage_change_pct=-10.7,
        gini_change=0.011,
        social_elasticity=0.39,
        quadrant="Crecimiento Excluyente",
    )
    assert metric.country == "Argentina"
    assert metric.gdp_pc_growth_mean == 4.60
    assert metric.quadrant == "Crecimiento Excluyente"
    assert metric.food_inflation_mean_pct is None
    assert metric.food_wage_gap_pct is None


def test_country_period_metric_food_inflation_fields():
    metric = CountryPeriodMetric(
        country="Colombia",
        period_label="P2: 2021-2023",
        years_range="2021-2023",
        gdp_pc_growth_mean=5.10,
        food_inflation_mean_pct=15.4,
        food_wage_gap_pct=11.2,
    )
    assert metric.food_inflation_mean_pct == 15.4
    assert metric.food_wage_gap_pct == 11.2


def test_decoupling_dataset_creation():
    metric = CountryPeriodMetric(
        country="Chile",
        period_label="P1: 2015-2019",
        years_range="2015-2017",
        gdp_pc_growth_mean=0.50,
        poverty_total_change_pp=-2.5,
        poverty_extreme_change_pp=-0.3,
        real_min_wage_change_pct=5.2,
        gini_change=-0.003,
        social_elasticity=-5.0,
        quadrant="Crecimiento Virtuoso",
    )
    dataset = DecouplingDataset(records=[metric], metadata={"total_countries": 1})
    assert len(dataset.records) == 1
    assert dataset.records[0].country == "Chile"


def test_regression_model_summary_defaults():
    summary = RegressionModelSummary(r_squared=0.68)
    assert summary.r_squared == 0.68
    assert summary.r_squared_adj == 0.0
    assert summary.coefficients == {}
    assert summary.p_values == {}
    assert summary.std_errors == {}
    assert summary.confidence_intervals == {}
    assert summary.n_obs == 0
    assert summary.f_pvalue == 1.0


def test_regression_model_summary_full():
    summary = RegressionModelSummary(
        r_squared=0.75,
        r_squared_adj=0.71,
        coefficients={"const": 1.25, "food_inflation_mean_pct": 0.42},
        p_values={"const": 0.04, "food_inflation_mean_pct": 0.002},
        std_errors={"const": 0.55, "food_inflation_mean_pct": 0.11},
        confidence_intervals={
            "const": (0.1, 2.4),
            "food_inflation_mean_pct": (0.19, 0.65),
        },
        n_obs=18,
        f_pvalue=0.001,
    )
    assert summary.r_squared == 0.75
    assert summary.coefficients["food_inflation_mean_pct"] == 0.42
    assert summary.confidence_intervals["const"] == (0.1, 2.4)
    assert summary.n_obs == 18

