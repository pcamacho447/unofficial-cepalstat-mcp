"""Tests for statscepal analyze CLI subcommand."""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from unofficial_cepalstat_mcp.analysis.models import CountryPeriodMetric, DecouplingDataset
from unofficial_cepalstat_mcp.cli import main
from unofficial_cepalstat_mcp.exceptions import CepalStatError


def test_cli_analyze_help(capsys):
    """Test statscepal analyze --help outputs desacople subcommand."""
    ret = main(["analyze", "--help"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "desacople" in captured.out


def test_cli_analyze_no_subcommand(capsys):
    """Test statscepal analyze with no subcommand displays help."""
    ret = main(["analyze"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "desacople" in captured.out or "usage:" in captured.out.lower()


def test_cli_analyze_desacople_help(capsys):
    """Test statscepal analyze desacople --help displays arguments."""
    ret = main(["analyze", "desacople", "--help"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "--countries" in captured.out
    assert "--output" in captured.out
    assert "--econometrics" in captured.out


@patch("unofficial_cepalstat_mcp.cli.DecouplingAnalyzer")
@patch("unofficial_cepalstat_mcp.cli.DataExtractor")
@patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
def test_cli_analyze_desacople(mock_client, mock_extractor, mock_analyzer, capsys):
    mock_instance = MagicMock()
    mock_instance.analyze_countries.return_value = DecouplingDataset(
        records=[
            CountryPeriodMetric(
                country="Chile",
                period_label="P1",
                years_range="2015-2017",
                gdp_pc_growth_mean=0.5,
                poverty_total_change_pp=-2.5,
                poverty_extreme_change_pp=-0.3,
                real_min_wage_change_pct=5.2,
                gini_change=-0.003,
                food_inflation_mean_pct=3.4,
                food_wage_gap_pct=1.8,
                social_elasticity=-5.0,
                quadrant="Crecimiento Virtuoso",
            )
        ]
    )
    mock_analyzer.return_value = mock_instance

    exit_code = main(["analyze", "desacople", "--countries", "Chile"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Chile" in captured.out
    assert "Crecimiento Virtuoso" in captured.out
    assert "Δ PIB pc (%)" in captured.out
    assert "Infl. Alim (%)" in captured.out
    assert "Brecha Sal/Alim (%)" in captured.out
    mock_analyzer.return_value.analyze_countries.assert_called_once_with(
        countries=["Chile"],
        periods=[("P1: 2015-2019", 2015, 2019), ("P2: 2021-2023", 2021, 2023)],
    )


@patch("unofficial_cepalstat_mcp.cli.DecouplingAnalyzer")
@patch("unofficial_cepalstat_mcp.cli.DataExtractor")
@patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
def test_cli_analyze_desacople_default_countries(
    mock_client, mock_extractor, mock_analyzer, capsys
):
    mock_instance = MagicMock()
    mock_instance.analyze_countries.return_value = DecouplingDataset(
        records=[
            CountryPeriodMetric(
                country="Argentina",
                period_label="P1: 2015-2019",
                years_range="2015-2019",
                gdp_pc_growth_mean=-1.2,
                quadrant="Doble Vulnerabilidad",
            )
        ]
    )
    mock_analyzer.return_value = mock_instance

    exit_code = main(["analyze", "desacople"])
    assert exit_code == 0
    mock_analyzer.return_value.analyze_countries.assert_called_once_with(
        countries=["Argentina", "Chile", "Colombia", "México", "Perú", "Uruguay"],
        periods=[("P1: 2015-2019", 2015, 2019), ("P2: 2021-2023", 2021, 2023)],
    )
    captured = capsys.readouterr()
    assert "Argentina" in captured.out
    assert "Doble Vulnerabilidad" in captured.out


@patch("unofficial_cepalstat_mcp.cli.DecouplingAnalyzer")
@patch("unofficial_cepalstat_mcp.cli.DataExtractor")
@patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
def test_cli_analyze_desacople_output_csv(
    mock_client, mock_extractor, mock_analyzer, tmp_path, capsys
):
    mock_instance = MagicMock()
    mock_instance.analyze_countries.return_value = DecouplingDataset(
        records=[
            CountryPeriodMetric(
                country="Chile",
                period_label="P1",
                years_range="2015-2017",
                gdp_pc_growth_mean=0.5,
                poverty_total_change_pp=-2.5,
                poverty_extreme_change_pp=-0.3,
                real_min_wage_change_pct=5.2,
                gini_change=-0.003,
                social_elasticity=-5.0,
                quadrant="Crecimiento Virtuoso",
            )
        ]
    )
    mock_analyzer.return_value = mock_instance

    csv_file = tmp_path / "test_output.csv"
    exit_code = main(["analyze", "desacople", "--countries", "Chile", "--output", str(csv_file)])
    assert exit_code == 0
    assert csv_file.exists()
    content = csv_file.read_text(encoding="utf-8")
    assert "País" in content
    assert "Chile" in content
    assert "Infl. Alim (%)" in content
    assert "Brecha Sal/Alim (%)" in content
    assert "Crecimiento Virtuoso" in content
    captured = capsys.readouterr()
    assert f"Saved 1 rows to {csv_file}" in captured.out


@patch("unofficial_cepalstat_mcp.cli.DecouplingAnalyzer")
@patch("unofficial_cepalstat_mcp.cli.DataExtractor")
@patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
def test_cli_analyze_desacople_econometrics(
    mock_client, mock_extractor, mock_analyzer, capsys
):
    from unofficial_cepalstat_mcp.analysis.models import RegressionModelSummary

    mock_instance = MagicMock()
    mock_dataset = DecouplingDataset(
        records=[
            CountryPeriodMetric(
                country="Chile",
                period_label="P1",
                years_range="2015-2017",
                gdp_pc_growth_mean=0.5,
                poverty_total_change_pp=-2.5,
                poverty_extreme_change_pp=-0.3,
                real_min_wage_change_pct=5.2,
                gini_change=-0.003,
                food_inflation_mean_pct=3.4,
                food_wage_gap_pct=1.8,
                social_elasticity=-5.0,
                quadrant="Crecimiento Virtuoso",
            )
        ]
    )
    mock_instance.analyze_countries.return_value = mock_dataset
    mock_summary = RegressionModelSummary(
        r_squared=0.6543,
        r_squared_adj=0.5432,
        coefficients={
            "const": 0.1234,
            "gdp_pc_growth_mean": -0.4567,
            "real_min_wage_change_pct": -0.2100,
            "food_inflation_mean_pct": 0.3456,
        },
        p_values={
            "const": 0.0500,
            "gdp_pc_growth_mean": 0.0120,
            "real_min_wage_change_pct": 0.0340,
            "food_inflation_mean_pct": 0.0080,
        },
        std_errors={
            "const": 0.0600,
            "gdp_pc_growth_mean": 0.1200,
            "real_min_wage_change_pct": 0.0900,
            "food_inflation_mean_pct": 0.1100,
        },
        confidence_intervals={
            "const": (-0.0100, 0.2500),
            "gdp_pc_growth_mean": (-0.7100, -0.2000),
            "real_min_wage_change_pct": (-0.4000, -0.0200),
            "food_inflation_mean_pct": (0.1100, 0.5800),
        },
        n_obs=12,
        f_pvalue=0.0021,
    )
    mock_instance.run_econometric_regression.return_value = mock_summary
    mock_analyzer.return_value = mock_instance

    exit_code = main(["analyze", "desacople", "--countries", "Chile", "--econometrics"])
    assert exit_code == 0
    mock_instance.run_econometric_regression.assert_called_once_with(mock_dataset)
    captured = capsys.readouterr()
    assert "CEPALSTAT ECONOMETRIC REGRESSION SUMMARY (OLS)" in captured.out
    assert "Dep. Variable: Δ Pobreza Total (pp)" in captured.out
    assert "N = 12" in captured.out
    assert "R² = 0.6543" in captured.out
    assert "Adj. R² = 0.5432" in captured.out
    assert "F-statistic p-value: 0.0021" in captured.out
    assert "Variable" in captured.out
    assert "Coef." in captured.out
    assert "Std.Err." in captured.out
    assert "p-value" in captured.out
    assert "[95% Conf. Interval]" in captured.out
    assert "food_inflation_mean_pct" in captured.out
    assert "0.3456" in captured.out


@patch("unofficial_cepalstat_mcp.cli.DecouplingAnalyzer")
@patch("unofficial_cepalstat_mcp.cli.DataExtractor")
@patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
def test_cli_analyze_desacople_without_econometrics(
    mock_client, mock_extractor, mock_analyzer, capsys
):
    mock_instance = MagicMock()
    mock_instance.analyze_countries.return_value = DecouplingDataset(
        records=[
            CountryPeriodMetric(
                country="Chile",
                period_label="P1",
                years_range="2015-2017",
                gdp_pc_growth_mean=0.5,
                poverty_total_change_pp=-2.5,
                poverty_extreme_change_pp=-0.3,
                real_min_wage_change_pct=5.2,
                gini_change=-0.003,
                food_inflation_mean_pct=3.4,
                food_wage_gap_pct=1.8,
                social_elasticity=-5.0,
                quadrant="Crecimiento Virtuoso",
            )
        ]
    )
    mock_analyzer.return_value = mock_instance

    exit_code = main(["analyze", "desacople", "--countries", "Chile"])
    assert exit_code == 0
    mock_instance.run_econometric_regression.assert_not_called()
    captured = capsys.readouterr()
    assert "CEPALSTAT ECONOMETRIC REGRESSION SUMMARY (OLS)" not in captured.out


@patch("unofficial_cepalstat_mcp.cli.DecouplingAnalyzer")
@patch("unofficial_cepalstat_mcp.cli.DataExtractor")
@patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
def test_cli_analyze_desacople_empty(
    mock_client, mock_extractor, mock_analyzer, capsys
):
    mock_instance = MagicMock()
    mock_instance.analyze_countries.return_value = DecouplingDataset(records=[])
    mock_analyzer.return_value = mock_instance

    exit_code = main(["analyze", "desacople", "--countries", "Chile"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "No records found." in captured.out


@patch("unofficial_cepalstat_mcp.cli.DecouplingAnalyzer")
@patch("unofficial_cepalstat_mcp.cli.DataExtractor")
@patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
def test_cli_analyze_desacople_error(
    mock_client, mock_extractor, mock_analyzer, capsys
):
    mock_instance = MagicMock()
    mock_instance.analyze_countries.side_effect = CepalStatError("Network timeout")
    mock_analyzer.return_value = mock_instance

    exit_code = main(["analyze", "desacople"])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "CEPALSTAT Error: Network timeout" in captured.err
