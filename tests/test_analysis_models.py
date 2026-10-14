import pytest
from statscepal.analysis.models import CountryPeriodMetric, DecouplingDataset


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
