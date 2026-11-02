"""Tests for Life Expectancy at Birth Resolution (Indicator 4784)."""

import pytest

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus, TemporalAvailabilityStatus


@pytest.fixture
def engine() -> SemanticResolutionEngine:
    return SemanticResolutionEngine()


def test_life_expectancy_multi_country_multi_year_male(engine: SemanticResolutionEngine) -> None:
    """Verify resolution of life expectancy query for male population across 6 countries and 31 years."""
    query = (
        "esperanza de vida de los hombres en paises argentina, bahamas, brasil, "
        "chile, colombia y peru desde 1990 hasta el 2020"
    )
    res = engine.resolve(query)

    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4784
    assert res.selected_candidate.name == "Esperanza de vida al nacer, según sexo"
    assert res.applied_filters.facets == {"sexo": "MASCULINO"}

    # Dimension filter check
    bound_dim_map = {d.dim_id: d for d in res.applied_filters.dimensions}
    assert 88622 in bound_dim_map
    assert bound_dim_map[88622].member_id == 88626
    assert bound_dim_map[88622].member_name == "Hombres"

    # Countries & Years check
    assert len(res.applied_filters.country_codes) == 6
    assert set(res.applied_filters.country_codes) == {"ARG", "BHS", "BRA", "CHL", "COL", "PER"}
    assert len(res.applied_filters.years) == 31
    assert res.applied_filters.years[0] == 1990
    assert res.applied_filters.years[-1] == 2020

    # Temporal availability
    assert res.temporal_info is not None
    assert res.temporal_info.temporal_status == TemporalAvailabilityStatus.OBSERVATION_EXISTING


def test_life_expectancy_syntax_with_del_sexo(engine: SemanticResolutionEngine) -> None:
    """Verify resolution of life expectancy query using 'del sexo hombres' phrasing."""
    query = (
        "esperanza de vida del sexo hombres en paises argentina, bahamas, brasil, "
        "chile, colombia y peru desde 1990 hasta el 2020"
    )
    res = engine.resolve(query)

    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4784
    assert res.applied_filters.facets == {"sexo": "MASCULINO"}
