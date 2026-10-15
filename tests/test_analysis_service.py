"""Tests for DecouplingAnalyzer service orchestrator."""

from unittest.mock import MagicMock
import pandas as pd
import pytest

from statscepal.analysis import (
    CountryPeriodMetric,
    DecouplingAnalyzer,
    DecouplingDataset,
)
from statscepal.analysis.service import (
    COUNTRY_MEMBER_MAP,
    FOOD_INFLATION_MEMBER_MAP,
    DecouplingAnalyzer as DirectDecouplingAnalyzer,
)


def test_analyzer_exports():
    """Verify DecouplingAnalyzer is exported from statscepal.analysis."""
    assert DecouplingAnalyzer is DirectDecouplingAnalyzer


def test_country_member_map():
    """Verify country member mappings according to brief."""
    assert COUNTRY_MEMBER_MAP["argentina"] == 216
    assert COUNTRY_MEMBER_MAP["chile"] == 224
    assert COUNTRY_MEMBER_MAP["colombia"] == 225
    assert COUNTRY_MEMBER_MAP["méxico"] == 233
    assert COUNTRY_MEMBER_MAP["mexico"] == 233
    assert COUNTRY_MEMBER_MAP["perú"] == 244
    assert COUNTRY_MEMBER_MAP["peru"] == 244
    assert COUNTRY_MEMBER_MAP["uruguay"] == 258


def test_food_inflation_member_map():
    """Verify food inflation (Indicator 2929) member mappings for dimension 79565."""
    assert FOOD_INFLATION_MEMBER_MAP["argentina"] == 79568
    assert FOOD_INFLATION_MEMBER_MAP["chile"] == 79578
    assert FOOD_INFLATION_MEMBER_MAP["colombia"] == 79579
    assert FOOD_INFLATION_MEMBER_MAP["méxico"] == 79599
    assert FOOD_INFLATION_MEMBER_MAP["mexico"] == 79599
    assert FOOD_INFLATION_MEMBER_MAP["perú"] == 79604
    assert FOOD_INFLATION_MEMBER_MAP["peru"] == 79604
    assert FOOD_INFLATION_MEMBER_MAP["uruguay"] == 79612


def test_analyzer_with_mocked_extractor():
    """Verify standard decoupling analysis for Chile."""
    mock_extractor = MagicMock()
    # Mock data for PIB (3894)
    df_pib = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2016", "2017"],
        "value": [1.5, 2.0],
    })
    # Mock data for Pobreza (3328)
    df_pob = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Area geográfica_(EH)": ["Nacional", "Nacional"],
        "Pobreza extrema y pobreza": ["Pobreza", "Pobreza"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [13.2, 10.7],
    })
    # Mock data for Salario Real (340)
    df_sal = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [100.0, 105.0],
    })
    # Mock data for Gini (3289)
    df_gini = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [0.45, 0.44],
    })

    def mock_get_df(ind_id, members=None, **kwargs):
        if ind_id == 3894:
            return df_pib.copy()
        elif ind_id == 3328:
            return df_pob.copy()
        elif ind_id == 340:
            return df_sal.copy()
        elif ind_id == 3289:
            return df_gini.copy()
        return pd.DataFrame()

    mock_extractor.get_dataframe.side_effect = mock_get_df

    analyzer = DecouplingAnalyzer(extractor=mock_extractor)
    dataset = analyzer.analyze_countries(
        countries=["Chile"],
        periods=[("P1", 2015, 2017)],
    )

    assert len(dataset.records) == 1
    rec = dataset.records[0]
    assert rec.country == "Chile"
    assert rec.period_label == "P1"
    assert rec.years_range == "2015-2017"
    assert rec.gdp_pc_growth_mean == 1.75
    assert rec.poverty_total_change_pp == -2.5
    assert rec.real_min_wage_change_pct == 5.0
    assert rec.gini_change == -0.01
    assert rec.social_elasticity == -1.43
    assert rec.quadrant == "Crecimiento Virtuoso"
    assert dataset.metadata["total_records"] == 1


def test_analyzer_argentina_area_filtering():
    """Verify Argentina filters by 'Total del área urbana' instead of 'Nacional'."""
    mock_extractor = MagicMock()

    df_pib = pd.DataFrame({
        "País__ESTANDAR": ["Argentina", "Argentina"],
        "Años__ESTANDAR": [2021, 2022],
        "value": [4.0, 5.2],
    })
    # Both Nacional and Total del área urbana present; only Urbana should be matched for Argentina
    df_pob = pd.DataFrame({
        "País__ESTANDAR": ["Argentina", "Argentina", "Argentina", "Argentina"],
        "Area geográfica_(EH)": [
            "Nacional",
            "Nacional",
            "Total del área urbana",
            "Total del área urbana",
        ],
        "Pobreza extrema y pobreza": ["Pobreza", "Pobreza", "Pobreza", "Pobreza"],
        "Años__ESTANDAR": [2021, 2023, 2021, 2023],
        "value": [99.0, 99.0, 37.0, 41.7],
    })
    df_sal = pd.DataFrame({
        "País__ESTANDAR": ["Argentina", "Argentina"],
        "Años__ESTANDAR": [2021, 2023],
        "value": [100.0, 90.0],
    })
    df_gini = pd.DataFrame({
        "País__ESTANDAR": ["Argentina", "Argentina"],
        "Años__ESTANDAR": [2021, 2023],
        "value": [0.42, 0.43],
    })

    def mock_get_df(ind_id, members=None, **kwargs):
        if ind_id == 3894:
            return df_pib.copy()
        elif ind_id == 3328:
            return df_pob.copy()
        elif ind_id == 340:
            return df_sal.copy()
        elif ind_id == 3289:
            return df_gini.copy()
        return pd.DataFrame()

    mock_extractor.get_dataframe.side_effect = mock_get_df

    analyzer = DecouplingAnalyzer(extractor=mock_extractor)
    dataset = analyzer.analyze_countries(
        countries=["Argentina"],
        periods=[("P2", 2021, 2023)],
    )

    assert len(dataset.records) == 1
    rec = dataset.records[0]
    assert rec.country == "Argentina"
    # Should use the Urbana values: 41.7 - 37.0 = 4.7 pp
    assert rec.poverty_total_change_pp == 4.7
    assert rec.gdp_pc_growth_mean == 4.6
    assert rec.quadrant == "Crecimiento Excluyente"


def test_analyzer_empty_data_handling():
    """Verify analyzer handles empty indicators gracefully without crashing."""
    mock_extractor = MagicMock()
    mock_extractor.get_dataframe.return_value = pd.DataFrame()

    analyzer = DecouplingAnalyzer(extractor=mock_extractor)
    dataset = analyzer.analyze_countries(
        countries=["Uruguay"],
        periods=[("P1", 2015, 2019)],
    )

    assert len(dataset.records) == 1
    rec = dataset.records[0]
    assert rec.country == "Uruguay"
    assert rec.gdp_pc_growth_mean == 0.0
    assert rec.poverty_total_change_pp is None
    assert rec.poverty_extreme_change_pp is None
    assert rec.real_min_wage_change_pct is None
    assert rec.gini_change is None
    assert rec.social_elasticity is None
    assert rec.quadrant == "Indeterminado"
    assert rec.years_range == "2015-2019"


def test_analyzer_accented_countries_and_extreme_poverty():
    """Verify handling of accented country names (México, Perú) and extreme poverty metrics."""
    mock_extractor = MagicMock()

    df_pib = pd.DataFrame({
        "País__ESTANDAR": ["México", "México"],
        "Años__ESTANDAR": [2016, 2018],
        "value": [2.0, 1.0],
    })
    df_pob = pd.DataFrame({
        "País__ESTANDAR": ["México", "México", "México", "México"],
        "Area geográfica_(EH)": ["Nacional", "Nacional", "Nacional", "Nacional"],
        "Pobreza extrema y pobreza": [
            "Pobreza",
            "Pobreza",
            "Pobreza extrema",
            "Pobreza extrema",
        ],
        "Años__ESTANDAR": [2016, 2018, 2016, 2018],
        "value": [43.2, 41.9, 7.6, 7.4],
    })
    df_sal = pd.DataFrame({
        "País__ESTANDAR": ["México", "México"],
        "Años__ESTANDAR": [2016, 2018],
        "value": [100.0, 108.5],
    })
    df_gini = pd.DataFrame({
        "País__ESTANDAR": ["México", "México"],
        "Años__ESTANDAR": [2016, 2018],
        "value": [0.485, 0.470],
    })

    def mock_get_df(ind_id, members=None, **kwargs):
        if ind_id == 3894:
            return df_pib.copy()
        elif ind_id == 3328:
            return df_pob.copy()
        elif ind_id == 340:
            return df_sal.copy()
        elif ind_id == 3289:
            return df_gini.copy()
        return pd.DataFrame()

    mock_extractor.get_dataframe.side_effect = mock_get_df

    # Pass unaccented "Mexico" to test accent-insensitivity
    analyzer = DecouplingAnalyzer(extractor=mock_extractor)
    dataset = analyzer.analyze_countries(
        countries=["Mexico"],
        periods=[("P1", 2016, 2018)],
    )

    assert len(dataset.records) == 1
    rec = dataset.records[0]
    assert rec.country == "Mexico"
    assert rec.gdp_pc_growth_mean == 1.5
    assert rec.poverty_total_change_pp == -1.3
    assert rec.poverty_extreme_change_pp == -0.2
    assert rec.real_min_wage_change_pct == 8.5
    assert rec.gini_change == -0.015
    assert rec.quadrant == "Crecimiento Virtuoso"
    # Extractor was called for 5 indicators (3894, 3328, 340, 3289 with member 233, and 2929 with member 79599)
    call_args_list = mock_extractor.get_dataframe.call_args_list
    assert len(call_args_list) == 5
    for call in call_args_list[:4]:
        assert call.kwargs["members"] == [233]
    assert call_args_list[4].kwargs["members"] == [79599]
    assert call_args_list[4].kwargs["decode_labels"] is True


def test_analyzer_wage_zero_start_and_single_obs_poverty():
    """Verify that wage with zero or negative initial value returns None, and single obs poverty returns None."""
    mock_extractor = MagicMock()

    df_pib = pd.DataFrame({
        "País__ESTANDAR": ["Colombia"],
        "Años__ESTANDAR": [2018],
        "value": [2.5],
    })
    # Only 1 poverty observation year
    df_pob = pd.DataFrame({
        "País__ESTANDAR": ["Colombia"],
        "Area geográfica_(EH)": ["Nacional"],
        "Pobreza extrema y pobreza": ["Pobreza"],
        "Años__ESTANDAR": [2018],
        "value": [30.0],
    })
    # Initial wage is 0.0 -> division by zero safeguard
    df_sal = pd.DataFrame({
        "País__ESTANDAR": ["Colombia", "Colombia"],
        "Años__ESTANDAR": [2018, 2019],
        "value": [0.0, 110.0],
    })
    df_gini = pd.DataFrame()

    def mock_get_df(ind_id, members=None, **kwargs):
        if ind_id == 3894:
            return df_pib.copy()
        elif ind_id == 3328:
            return df_pob.copy()
        elif ind_id == 340:
            return df_sal.copy()
        return pd.DataFrame()

    mock_extractor.get_dataframe.side_effect = mock_get_df

    analyzer = DecouplingAnalyzer(extractor=mock_extractor)
    dataset = analyzer.analyze_countries(
        countries=["Colombia"],
        periods=[("P1", 2017, 2019)],
    )

    rec = dataset.records[0]
    assert rec.poverty_total_change_pp is None
    assert rec.years_range == "2017-2019"
    assert rec.real_min_wage_change_pct is None
    assert rec.gini_change is None
    assert rec.social_elasticity is None


def test_analyzer_with_indicator_2929_food_inflation():
    """Verify Indicator 2929 extraction, food inflation mean, and purchasing power gap."""
    mock_extractor = MagicMock()
    df_pib = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2016", "2017"],
        "value": [1.5, 2.0],
    })
    df_pob = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Area geográfica_(EH)": ["Nacional", "Nacional"],
        "Pobreza extrema y pobreza": ["Pobreza", "Pobreza"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [13.2, 10.7],
    })
    df_sal = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [100.0, 105.0],
    })
    df_gini = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [0.45, 0.44],
    })
    # Indicator 2929 with special dimension column name
    df_food = pd.DataFrame({
        "Países_agregados regionales especiales VAR IPC": ["Chile", "Chile", "Chile"],
        "Años__ESTANDAR": ["2015", "2016", "2017"],
        "value": [4.5, 3.2, 2.8],
    })

    def mock_get_df(ind_id, members=None, **kwargs):
        if ind_id == 3894:
            return df_pib.copy()
        elif ind_id == 3328:
            return df_pob.copy()
        elif ind_id == 340:
            return df_sal.copy()
        elif ind_id == 3289:
            return df_gini.copy()
        elif ind_id == 2929:
            return df_food.copy()
        return pd.DataFrame()

    mock_extractor.get_dataframe.side_effect = mock_get_df

    analyzer = DecouplingAnalyzer(extractor=mock_extractor)
    dataset = analyzer.analyze_countries(
        countries=["Chile"],
        periods=[("P1", 2015, 2017)],
    )

    assert len(dataset.records) == 1
    rec = dataset.records[0]
    assert rec.country == "Chile"
    # Mean of [4.5, 3.2, 2.8] = 10.5 / 3 = 3.5
    assert rec.food_inflation_mean_pct == 3.5
    # Real wage change = +5.0%, Gap = 5.0 - 3.5 = 1.5
    assert rec.real_min_wage_change_pct == 5.0
    assert rec.food_wage_gap_pct == 1.5

    # Check 2929 was queried with correct member and decode_labels=True
    call_args_list = mock_extractor.get_dataframe.call_args_list
    assert len(call_args_list) == 5
    call_2929 = [c for c in call_args_list if c.args[0] == 2929][0]
    assert call_2929.kwargs["members"] == [79578]
    assert call_2929.kwargs["decode_labels"] is True


def test_analyzer_indicator_2929_empty_handling():
    """Verify that when Indicator 2929 has no data for a period, fields are None."""
    mock_extractor = MagicMock()
    df_pib = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2016", "2017"],
        "value": [1.5, 2.0],
    })
    df_sal = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [100.0, 105.0],
    })

    def mock_get_df(ind_id, members=None, **kwargs):
        if ind_id == 3894:
            return df_pib.copy()
        elif ind_id == 340:
            return df_sal.copy()
        return pd.DataFrame()

    mock_extractor.get_dataframe.side_effect = mock_get_df

    analyzer = DecouplingAnalyzer(extractor=mock_extractor)
    dataset = analyzer.analyze_countries(
        countries=["Chile"],
        periods=[("P1", 2015, 2017)],
    )

    rec = dataset.records[0]
    assert rec.food_inflation_mean_pct is None
    assert rec.food_wage_gap_pct is None


def test_analyzer_run_econometric_regression():
    """Verify DecouplingAnalyzer.run_econometric_regression delegates to EconometricEstimator."""
    mock_extractor = MagicMock()
    analyzer = DecouplingAnalyzer(extractor=mock_extractor)

    # 1. Calling without dataset when no analysis was done returns empty summary
    summary_empty = analyzer.run_econometric_regression()
    assert summary_empty.n_obs == 0
    assert summary_empty.r_squared == 0.0

    # 2. Calling with an explicit dataset
    records = [
        CountryPeriodMetric(
            country=f"Country_{i}",
            period_label="P1",
            years_range="2015-2019",
            gdp_pc_growth_mean=float(i % 5 + 1),
            poverty_total_change_pp=float(-2.0 + (i % 3)),
            real_min_wage_change_pct=float(3.0 + i),
            food_inflation_mean_pct=float(4.0 + (i % 4)),
        )
        for i in range(12)
    ]
    ds = DecouplingDataset(records=records)
    summary = analyzer.run_econometric_regression(ds)
    assert summary.n_obs == 12
    assert "gdp_pc_growth_mean" in summary.coefficients

    # 3. Calling without argument after setting _last_dataset
    analyzer._last_dataset = ds
    summary_cached = analyzer.run_econometric_regression()
    assert summary_cached.n_obs == 12
    assert summary_cached.r_squared == summary.r_squared


