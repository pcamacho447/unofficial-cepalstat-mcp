import pytest
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.matcher import DynamicMemberMatcher
from statscepal.semantic.engine import SemanticResolutionEngine
from statscepal.semantic.registry import SemanticRegistry
from statscepal.semantic.models import ResolutionStatus, TemporalAvailabilityStatus


def test_dynamic_member_matcher_resolves_members():
    matcher = DynamicMemberMatcher()
    dims = [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=43054,
            name="Grupo de edad",
            members=[Member(id=43059, name="0 a 14 años"), Member(id=43058, name="15 a 24 años")],
        ),
    ]

    facets = {"sexo": "FEMENINO", "area": "RURAL", "edad": "JUVENTUD"}
    success, filters, unhandled = matcher.match_facets_to_dimensions(3341, dims, facets)

    assert success is True
    assert len(unhandled) == 0
    assert len(filters) == 3

    filter_map = {f.dim_id: (f.member_id, f.member_name) for f in filters}
    assert filter_map[144] == (266, "Mujeres")
    assert filter_map[326] == (331, "Rural")
    assert filter_map[43054] == (43058, "15 a 24 años")


def test_dynamic_member_matcher_flags_unhandled_facet():
    matcher = DynamicMemberMatcher()
    dims = [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional")],
        )
    ]
    facets = {"sexo": "FEMENINO"}
    success, filters, unhandled = matcher.match_facets_to_dimensions(3328, dims, facets)

    assert success is False
    assert "sexo" in unhandled


def test_dynamic_member_matcher_severidad_and_moneda():
    matcher = DynamicMemberMatcher()
    dims = [
        Dimension(
            id=500,
            name="Tipo de pobreza",
            members=[
                Member(id=501, name="Pobreza extrema / indigencia"),
                Member(id=502, name="Total pobreza"),
            ],
        ),
        Dimension(
            id=600,
            name="Precios y moneda",
            members=[
                Member(id=601, name="Dólares a precios constantes"),
                Member(id=602, name="Moneda nacional"),
            ],
        ),
    ]
    facets = {"severidad": "POBREZA_EXTREMA", "moneda": "DOLARES_CONSTANTES"}
    success, filters, unhandled = matcher.match_facets_to_dimensions(2203, dims, facets)

    assert success is True
    assert len(unhandled) == 0
    assert len(filters) == 2
    filter_map = {f.dim_id: f.member_id for f in filters}
    assert filter_map[500] == 501
    assert filter_map[600] == 601


def test_semantic_engine_populates_applied_dimension_filters():
    dims_3341 = [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=43054,
            name="Grupo de edad",
            members=[Member(id=43059, name="0 a 14 años"), Member(id=43058, name="15 a 24 años")],
        ),
    ]
    registry = SemanticRegistry(dimensions={3341: dims_3341})
    engine = SemanticResolutionEngine(registry=registry)

    res = engine.resolve("¿Cuál fue la pobreza de las mujeres jóvenes rurales en Brasil en 2021?")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 3341
    assert len(res.applied_filters.dimensions) == 3

    dim_map = {f.dim_id: f.member_id for f in res.applied_filters.dimensions}
    assert dim_map[144] == 266
    assert dim_map[326] == 331
    assert dim_map[43054] == 43058


def test_registry_temporal_status_normalization():
    registry = SemanticRegistry(
        temporal_availability={
            (3328, "CHL", 2021): ("period_unobserved", 2020, 2022),
            (3328, "CHL", 2022): ("OBSERVATION_EXISTING", None, None),
            (3328, "CHL", 2099): ("INVALID_STATUS_VALUE", None, None),
        }
    )
    st, prev_a, next_a = registry.check_temporal_availability(3328, "CHL", 2021)
    assert st == TemporalAvailabilityStatus.PERIOD_UNOBSERVED
    assert prev_a == 2020
    assert next_a == 2022

    st2, _, _ = registry.check_temporal_availability(3328, "CHL", 2022)
    assert st2 == TemporalAvailabilityStatus.OBSERVATION_EXISTING

    st3, _, _ = registry.check_temporal_availability(3328, "CHL", 2099)
    assert st3 == TemporalAvailabilityStatus.OBSERVATION_MISSING
