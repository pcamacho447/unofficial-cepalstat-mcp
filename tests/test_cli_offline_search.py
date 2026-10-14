"""Tests for offline search fallback in statscepal search CLI."""

from unittest.mock import MagicMock
import pytest

from statscepal.catalog.models import CatalogIndicator
from statscepal.cli import main
from statscepal.thematic_tree import IndicatorItem


@pytest.fixture
def sample_catalog_indicators() -> list[CatalogIndicator]:
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
            indicator_id=4795,
            name="Tasa de crecimiento anual",
            order_num=20,
            theme="Demográficos y sociales",
            area="Demográficos",
            subarea="",
            full_path="Demográficos y sociales > Demográficos",
            updated_at="2026-10-14T10:00:00",
        ),
    ]


def test_search_uses_local_catalog_when_built(capsys, mocker, sample_catalog_indicators):
    """When CatalogStore().is_built() is True, statscepal search queries CatalogStore.search()

    locally with zero network calls and formats output.
    """
    mock_store_cls = mocker.patch("statscepal.cli.CatalogStore")
    mock_store = MagicMock()
    mock_store.is_built.return_value = True
    mock_store.search.return_value = sample_catalog_indicators
    mock_store_cls.return_value = mock_store

    mock_client_cls = mocker.patch("statscepal.cli.CepalStatClient")
    mock_tree_cls = mocker.patch("statscepal.cli.ThematicTree")

    ret = main(["search", "población", "--limit", "5"])

    assert ret == 0
    mock_store.is_built.assert_called_once()
    mock_store.search.assert_called_once_with("población", limit=5)
    mock_client_cls.assert_not_called()
    mock_tree_cls.assert_not_called()

    captured = capsys.readouterr()
    assert "Found 2 indicators" in captured.out
    assert "[4788] Población total, según sexo" in captured.out
    assert "Path: Demográficos y sociales > Demográficos" in captured.out
    assert "[4795] Tasa de crecimiento anual" in captured.out


def test_search_uses_local_catalog_no_results(capsys, mocker):
    """When CatalogStore().is_built() is True and no results match."""
    mock_store_cls = mocker.patch("statscepal.cli.CatalogStore")
    mock_store = MagicMock()
    mock_store.is_built.return_value = True
    mock_store.search.return_value = []
    mock_store_cls.return_value = mock_store

    mock_client_cls = mocker.patch("statscepal.cli.CepalStatClient")
    mock_tree_cls = mocker.patch("statscepal.cli.ThematicTree")

    ret = main(["search", "inexistente"])

    assert ret == 0
    mock_store.is_built.assert_called_once()
    mock_store.search.assert_called_once_with("inexistente", limit=10)
    mock_client_cls.assert_not_called()
    mock_tree_cls.assert_not_called()

    captured = capsys.readouterr()
    assert "No indicators found matching 'inexistente'." in captured.out


def test_search_falls_back_to_tree_when_not_built(capsys, mocker):
    """When CatalogStore().is_built() is False, falls back to ThematicTree(client).search(query)

    as before and optionally includes a helpful tip to run statscepal catalog build.
    """
    mock_store_cls = mocker.patch("statscepal.cli.CatalogStore")
    mock_store = MagicMock()
    mock_store.is_built.return_value = False
    mock_store_cls.return_value = mock_store

    mock_tree_cls = mocker.patch("statscepal.cli.ThematicTree")
    mock_tree = MagicMock()
    mock_tree.search.return_value = [
        IndicatorItem(
            indicator_id=4788,
            name="Población total, según sexo",
            path="Demográficos y sociales > Demográficos",
        )
    ]
    mock_tree_cls.return_value = mock_tree

    mocker.patch("statscepal.cli.CepalStatClient")

    ret = main(["search", "población"])

    assert ret == 0
    mock_store.is_built.assert_called_once()
    mock_store.search.assert_not_called()
    mock_tree.search.assert_called_once_with("población")

    captured = capsys.readouterr()
    assert "Found 1 indicators" in captured.out
    assert "[4788] Población total, según sexo" in captured.out
    assert "Path: Demográficos y sociales > Demográficos" in captured.out
    assert "statscepal catalog build" in (captured.err + captured.out)
