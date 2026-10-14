"""Tests for statscepal analyze CLI subcommand."""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from statscepal.analysis.models import CountryPeriodMetric, DecouplingDataset
from statscepal.cli import main
from statscepal.exceptions import CepalStatError


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


@patch("statscepal.cli.DecouplingAnalyzer")
@patch("statscepal.cli.DataExtractor")
@patch("statscepal.cli.CepalStatClient")
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
    mock_analyzer.return_value.analyze_countries.assert_called_once_with(
        countries=["Chile"],
        periods=[("P1: 2015-2019", 2015, 2019), ("P2: 2021-2023", 2021, 2023)],
    )


@patch("statscepal.cli.DecouplingAnalyzer")
@patch("statscepal.cli.DataExtractor")
@patch("statscepal.cli.CepalStatClient")
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


@patch("statscepal.cli.DecouplingAnalyzer")
@patch("statscepal.cli.DataExtractor")
@patch("statscepal.cli.CepalStatClient")
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
    assert "Crecimiento Virtuoso" in content
    captured = capsys.readouterr()
    assert f"Saved 1 rows to {csv_file}" in captured.out


@patch("statscepal.cli.DecouplingAnalyzer")
@patch("statscepal.cli.DataExtractor")
@patch("statscepal.cli.CepalStatClient")
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


@patch("statscepal.cli.DecouplingAnalyzer")
@patch("statscepal.cli.DataExtractor")
@patch("statscepal.cli.CepalStatClient")
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
