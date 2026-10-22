"""Tests for catalog CLI subcommands."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from unofficial_cepalstat_mcp.catalog.models import CatalogIndicator, CatalogStats
from unofficial_cepalstat_mcp.cli import main
from unofficial_cepalstat_mcp.exceptions import CepalStatNetworkError


@pytest.fixture
def sample_indicators() -> list[CatalogIndicator]:
    return [
        CatalogIndicator(
            indicator_id=4788,
            name="Población total, según sexo",
            order_num=10,
            theme="Demográficos y sociales",
            area="Demográficos",
            subarea="",
            full_path="Demográficos y sociales > Demográficos",
            updated_at="2026-10-14T10:00:00",
        ),
        CatalogIndicator(
            indicator_id=415,
            name="PIB Anual a precios constantes",
            order_num=100,
            theme="Económicos",
            area="PIB y Cuentas Nacionales",
            subarea="",
            full_path="Económicos > PIB y Cuentas Nacionales",
            updated_at="2026-10-14T10:00:00",
        ),
    ]


@pytest.fixture
def sample_stats() -> CatalogStats:
    return CatalogStats(
        total_indicators=150,
        themes_count=5,
        areas_count=20,
        by_theme={
            "Demográficos y sociales": 100,
            "Económicos": 50,
        },
    )


def test_cli_catalog_help(capsys):
    """Test statscepal catalog --help exits with 0 and prints catalog subcommands."""
    ret = main(["catalog", "--help"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "build" in captured.out
    assert "search" in captured.out
    assert "stats" in captured.out
    assert "export" in captured.out


def test_cli_catalog_no_subcommand(capsys):
    """Test statscepal catalog without subcommands prints help and exits with 0."""
    ret = main(["catalog"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "catalog" in captured.out.lower()


def test_cli_catalog_stats(capsys, mocker, sample_stats):
    """Test statscepal catalog stats outputs summary statistics."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.CatalogStore")
    mock_store = MagicMock()
    mock_store.get_stats.return_value = sample_stats
    mock_store_cls.return_value = mock_store

    ret = main(["catalog", "stats"])
    assert ret == 0
    mock_store.get_stats.assert_called_once()

    captured = capsys.readouterr()
    assert "150" in captured.out
    assert "Demográficos y sociales" in captured.out
    assert "100" in captured.out
    assert "Económicos" in captured.out
    assert "50" in captured.out


def test_cli_catalog_search(capsys, mocker, sample_indicators):
    """Test statscepal catalog search <query> with optional --theme and --limit."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.CatalogStore")
    mock_store = MagicMock()
    mock_store.search.return_value = [sample_indicators[0]]
    mock_store_cls.return_value = mock_store

    ret = main([
        "catalog",
        "search",
        "poblacion",
        "--theme",
        "Demográficos y sociales",
        "--limit",
        "5",
    ])
    assert ret == 0
    mock_store.search.assert_called_once_with(
        query="poblacion",
        theme="Demográficos y sociales",
        limit=5,
    )

    captured = capsys.readouterr()
    assert "4788" in captured.out
    assert "Población total, según sexo" in captured.out
    assert "Demográficos y sociales" in captured.out


def test_cli_catalog_search_no_results(capsys, mocker):
    """Test statscepal catalog search with no matches."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.CatalogStore")
    mock_store = MagicMock()
    mock_store.search.return_value = []
    mock_store_cls.return_value = mock_store

    ret = main(["catalog", "search", "nonexistent"])
    assert ret == 0
    mock_store.search.assert_called_once_with(
        query="nonexistent",
        theme=None,
        limit=20,
    )

    captured = capsys.readouterr()
    assert "No indicators found" in captured.out


def test_cli_catalog_export(capsys, mocker, tmp_path: Path):
    """Test exporting catalog to JSON or CSV."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.CatalogStore")
    mock_store = MagicMock()
    out_json = tmp_path / "catalog_dump.json"
    mock_store.export.return_value = out_json
    mock_store_cls.return_value = mock_store

    # Test export with inferred JSON
    ret = main(["catalog", "export", str(out_json)])
    assert ret == 0
    mock_store.export.assert_called_once_with(str(out_json), format="json")

    captured = capsys.readouterr()
    assert "exported successfully" in captured.out.lower() or str(out_json) in captured.out

    # Test export with explicit CSV format
    out_csv = tmp_path / "catalog_dump.csv"
    mock_store.export.return_value = out_csv
    ret = main(["catalog", "export", str(out_csv), "--format", "csv"])
    assert ret == 0
    mock_store.export.assert_called_with(str(out_csv), format="csv")


def test_cli_catalog_export_missing_file(capsys):
    """Test export without output filepath returns error."""
    ret = main(["catalog", "export"])
    assert ret != 0
    captured = capsys.readouterr()
    assert "required" in (captured.err + captured.out).lower() or "error" in (captured.err + captured.out).lower()


def test_cli_catalog_build(capsys, mocker):
    """Test running statscepal catalog build [--force] using mocked CatalogStore.build."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.CatalogStore")
    mock_store = MagicMock()
    mock_store.build.return_value = 142
    mock_store_cls.return_value = mock_store

    # Build without force
    ret = main(["catalog", "build"])
    assert ret == 0
    mock_store.build.assert_called_once_with(force=False)

    captured = capsys.readouterr()
    assert "142" in captured.out
    assert "built" in captured.out.lower()

    # Build with --force
    mock_store.build.reset_mock()
    mock_store.build.return_value = 142
    ret = main(["catalog", "build", "--force"])
    assert ret == 0
    mock_store.build.assert_called_once_with(force=True)


def test_cli_catalog_build_error(capsys, mocker):
    """Test catalog build handles CepalStatError cleanly."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.CatalogStore")
    mock_store = MagicMock()
    mock_store.build.side_effect = CepalStatNetworkError("Connection timed out")
    mock_store_cls.return_value = mock_store

    ret = main(["catalog", "build"])
    assert ret == 1

    captured = capsys.readouterr()
    assert "CEPALSTAT Error: Connection timed out" in captured.err
