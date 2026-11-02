"""Tests for Employed Population and Economic Activity Sector Resolution (Indicators 417 & 122)."""

import pytest

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus, TemporalAvailabilityStatus


@pytest.fixture
def engine() -> SemanticResolutionEngine:
    return SemanticResolutionEngine()


def test_employed_population_by_large_sectors_and_area(engine: SemanticResolutionEngine) -> None:
    """Certify resolution of user query with multi-country, multi-year, area, sex and sector breakdown."""
    query = (
        "distribucion de la poblacion ocupada de chile, colombia y peru "
        "sexo hombre area geografica urbana del sector de actividad economica "
        "en el año 2022, 2023 y 2024"
    )
    res = engine.resolve(query)

    assert res.status in (ResolutionStatus.RESOLVED, ResolutionStatus.RESOLVED_WITH_ANCHORS)
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 417
    assert res.selected_candidate.name == (
        "Distribución de la población ocupada por sexo, grandes sectores de actividad económica y área"
    )

    # Check facets
    assert res.applied_filters.facets == {
        "area": "URBANO",
        "sexo": "MASCULINO",
        "actividad": "ACTIVIDAD_DESGLOSE",
    }

    # Check bound dimensions
    bound_dim_map = {d.dim_id: d for d in res.applied_filters.dimensions}
    assert 144 in bound_dim_map  # Sexo
    assert bound_dim_map[144].member_id == 265  # Hombres
    assert 326 in bound_dim_map  # Area
    assert bound_dim_map[326].member_id == 330  # Urbano / Urbana
    assert 1435 in bound_dim_map  # Grandes sectores economicos
    assert bound_dim_map[1435].is_breakdown is True
    assert set(bound_dim_map[1435].member_ids) == {1436, 1437, 1438}  # Agricultura, Industria, Servicios

    # Check temporal audit: Chile has gap in 2023
    assert res.temporal_info is not None
    assert "CHL" in res.temporal_info.country_anchors
    chl_anchor = res.temporal_info.country_anchors["CHL"]
    assert chl_anchor.unobserved_years == [2023]
    assert chl_anchor.previous_anchor_year == 2022
    assert chl_anchor.next_anchor_year == 2024
    assert res.temporal_info.temporal_status == TemporalAvailabilityStatus.PERIOD_UNOBSERVED


def test_employed_population_detailed_sector_swaps_to_122(engine: SemanticResolutionEngine) -> None:
    """When query specifies detailed sector breakdown or 122 indicator title, swap cleanly."""
    query = "distribucion de la poblacion ocupada por sexo sector de actividad economica y area en colombia 2022"
    res = engine.resolve(query)

    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id in (417, 122)


def test_prison_overcrowding_does_not_hijack_labor_occupation(engine: SemanticResolutionEngine) -> None:
    """Prison or hospital occupancy must abstain and never resolve to labor employment 417."""
    query = "tasa de ocupacion carcelaria y hacinamiento en el salvador"
    res = engine.resolve(query)
    assert res.status == ResolutionStatus.ABSTAINED
    assert res.selected_candidate is None


def test_economic_activity_labor_does_not_hijack_gdp(engine: SemanticResolutionEngine) -> None:
    """Queries mentioning 'sector de actividad economica' in labor contexts must not resolve to GDP 2204."""
    query = "ocupacion segun sector de actividad economica en chile 2022"
    res = engine.resolve(query)
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 417
    assert res.selected_candidate.indicator_id != 2204
