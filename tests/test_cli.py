import subprocess
import sys
from unittest.mock import MagicMock
import httpx
import pandas as pd
import pytest
import respx

from unofficial_cepalstat_mcp.cli import main
from unofficial_cepalstat_mcp.thematic_tree import IndicatorItem


@pytest.fixture(autouse=True)
def mock_catalog_not_built(mocker):
    """Ensure test_cli tests online/fallback behavior by default."""
    mocker.patch("unofficial_cepalstat_mcp.cli.CatalogStore.is_built", return_value=False)


def test_cli_help(capsys):
    """Test statscepal --help exits with 0 and prints help message."""
    ret = main(["--help"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "CEPALSTAT" in captured.out
    assert "search" in captured.out
    assert "info" in captured.out
    assert "fetch" in captured.out


def test_cli_help_subprocess():
    """Test running cli module via python -m statscepal.cli --help."""
    result = subprocess.run(
        [sys.executable, "-m", "unofficial_cepalstat_mcp.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "CEPALSTAT" in result.stdout
    assert "search" in result.stdout


def test_cli_no_args(capsys):
    """Test running without arguments prints help and returns 0."""
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "statscepal" in captured.out


def test_cli_search_invokes_thematic_tree(capsys, mocker):
    """Test search invokes ThematicTree.search and displays results."""
    mock_search = mocker.patch(
        "unofficial_cepalstat_mcp.thematic_tree.ThematicTree.search",
        return_value=[
            IndicatorItem(
                indicator_id=4788,
                name="Población total, según sexo",
                path="Demográficos y sociales > Demográficos",
            ),
            IndicatorItem(
                indicator_id=4795,
                name="Tasa de crecimiento anual",
                path="Demográficos y sociales > Demográficos",
            ),
        ],
    )

    ret = main(["search", "población", "--limit", "1"])
    assert ret == 0
    mock_search.assert_called_once_with("población")

    captured = capsys.readouterr()
    assert "Found 2 indicators" in captured.out
    assert "[4788] Población total, según sexo" in captured.out
    assert "Path: Demográficos y sociales > Demográficos" in captured.out
    # Since limit is 1, second indicator should not be printed
    assert "[4795]" not in captured.out


def test_cli_search_no_results(capsys, mocker):
    """Test search when no indicators match."""
    mocker.patch("unofficial_cepalstat_mcp.thematic_tree.ThematicTree.search", return_value=[])

    ret = main(["search", "inexistente"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "No indicators found matching 'inexistente'." in captured.out


def test_cli_info_invokes_get_metadata(capsys, mocker):
    """Test info invokes DataExtractor.get_metadata and prints metadata."""
    mock_meta = mocker.patch(
        "unofficial_cepalstat_mcp.extractor.DataExtractor.get_metadata",
        return_value={
            "indicator_name": "Población total, según sexo",
            "area": "Demografía",
            "unit": "Miles de personas",
            "definition": "Estimación y proyección de población total.",
        },
    )

    ret = main(["info", "4788"])
    assert ret == 0
    mock_meta.assert_called_once_with(4788)

    captured = capsys.readouterr()
    assert "=== Indicator 4788 ===" in captured.out
    assert "Name: Población total, según sexo" in captured.out
    assert "Area: Demografía" in captured.out
    assert "Unit: Miles de personas" in captured.out
    assert "Definition: Estimación y proyección de población total." in captured.out


def test_cli_info_not_found(capsys, mocker):
    """Test info when indicator metadata is not found."""
    mocker.patch("unofficial_cepalstat_mcp.extractor.DataExtractor.get_metadata", return_value={})

    ret = main(["info", "999999"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Indicator 999999 not found." in captured.out


def test_cli_fetch_prints_table(capsys, mocker):
    """Test fetch prints table to stdout."""
    df_mock = pd.DataFrame(
        [
            {"País__ESTANDAR": "Chile", "Años__ESTANDAR": "2020", "value": 19370.6},
            {"País__ESTANDAR": "Chile", "Años__ESTANDAR": "2021", "value": 19493.2},
        ]
    )
    mock_get_df = mocker.patch(
        "unofficial_cepalstat_mcp.extractor.DataExtractor.get_dataframe",
        return_value=df_mock,
    )

    ret = main(["fetch", "4788", "--members", "224, 29190"])
    assert ret == 0
    mock_get_df.assert_called_once_with(4788, members=[224, 29190], decode_labels=True)

    captured = capsys.readouterr()
    assert "Chile" in captured.out
    assert "19370.6" in captured.out


def test_cli_fetch_saves_csv(tmp_path, capsys, mocker):
    """Test fetch with --csv writes CSV file."""
    df_mock = pd.DataFrame(
        [
            {"País__ESTANDAR": "Chile", "value": 19370.6},
        ]
    )
    mocker.patch(
        "unofficial_cepalstat_mcp.extractor.DataExtractor.get_dataframe",
        return_value=df_mock,
    )

    csv_file = tmp_path / "output.csv"
    ret = main(["fetch", "4788", "--csv", str(csv_file)])
    assert ret == 0
    assert csv_file.exists()

    content = csv_file.read_text(encoding="utf-8")
    assert "País__ESTANDAR,value" in content
    assert "Chile,19370.6" in content

    captured = capsys.readouterr()
    assert f"Saved 1 rows to {csv_file}" in captured.out


def test_cli_fetch_empty(capsys, mocker):
    """Test fetch with no records returned."""
    mocker.patch(
        "unofficial_cepalstat_mcp.extractor.DataExtractor.get_dataframe",
        return_value=pd.DataFrame(),
    )

    ret = main(["fetch", "4788"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "No data records returned." in captured.out


@respx.mock
def test_cli_end_to_end_respx(capsys):
    """Integration test using respx mocked HTTP endpoints."""
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/metadata").mock(
        return_value=httpx.Response(
            200,
            json={
                "header": {"success": True, "code": 200},
                "body": {
                    "metadata": {
                        "indicator_id": 4788,
                        "indicator_name": "Población total",
                        "area": "Demografía",
                        "unit": "Miles",
                        "definition": "Población de prueba",
                    }
                },
            },
        )
    )

    ret = main(["info", "4788"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "=== Indicator 4788 ===" in captured.out
    assert "Name: Población total" in captured.out


def test_cli_fetch_invalid_members(capsys):
    """Test fetch with malformed members string."""
    ret = main(["fetch", "4788", "--members", "invalid_id"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Error: Invalid member IDs" in captured.err


def test_cli_cepalstat_error_handling(capsys, mocker):
    """Test handling of CepalStatError prints to stderr and returns 1."""
    from unofficial_cepalstat_mcp.exceptions import CepalStatNetworkError

    mocker.patch(
        "unofficial_cepalstat_mcp.thematic_tree.ThematicTree.search",
        side_effect=CepalStatNetworkError("Connection timed out"),
    )

    ret = main(["search", "error_test"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "CEPALSTAT Error: Connection timed out" in captured.err

