import pytest
from pydantic import ValidationError

from unofficial_cepalstat_mcp.catalog.models import CatalogIndicator, CatalogStats


def test_catalog_indicator_creation():
    ind = CatalogIndicator(
        indicator_id=4788,
        name="Población total, según sexo",
        order_num=10,
        theme="Demográficos y sociales",
        area="Demográficos",
        subarea="Población",
        full_path="Demográficos y sociales > Demográficos > Población",
        updated_at="2026-10-14T00:00:00",
    )
    assert ind.indicator_id == 4788
    assert ind.name == "Población total, según sexo"
    assert ind.order_num == 10
    assert ind.theme == "Demográficos y sociales"
    assert ind.area == "Demográficos"
    assert ind.subarea == "Población"
    assert ind.full_path == "Demográficos y sociales > Demográficos > Población"
    assert ind.updated_at == "2026-10-14T00:00:00"


def test_catalog_indicator_defaults():
    ind = CatalogIndicator(
        indicator_id=123,
        name="Indicador mínimo",
    )
    assert ind.indicator_id == 123
    assert ind.name == "Indicador mínimo"
    assert ind.order_num is None
    assert ind.theme == ""
    assert ind.area == ""
    assert ind.subarea == ""
    assert ind.full_path == ""
    assert ind.updated_at == ""


def test_catalog_indicator_validation():
    with pytest.raises(ValidationError):
        # Missing required fields
        CatalogIndicator()

    with pytest.raises(ValidationError):
        # Invalid indicator_id type
        CatalogIndicator(indicator_id="not-an-int", name="Test")


def test_catalog_stats_creation():
    stats = CatalogStats(
        total_indicators=2070,
        themes_count=4,
        areas_count=20,
        by_theme={"Económicos": 500, "Demográficos": 600},
    )
    assert stats.total_indicators == 2070
    assert stats.themes_count == 4
    assert stats.areas_count == 20
    assert stats.by_theme["Económicos"] == 500
    assert stats.by_theme["Demográficos"] == 600


def test_catalog_stats_defaults():
    stats = CatalogStats(total_indicators=100)
    assert stats.total_indicators == 100
    assert stats.themes_count == 0
    assert stats.areas_count == 0
    assert stats.by_theme == {}


def test_catalog_stats_validation():
    with pytest.raises(ValidationError):
        # Missing total_indicators
        CatalogStats()
