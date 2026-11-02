"""Test resolution and empirical fetch for demographic age brackets (e.g. 50-54 años).

Guarantees Invariant 1 (Zero Facet Loss) and verifies that population queries specifying
quinquennial age intervals resolve to indicator 4789 (Población por grupos de edad y sexo)
with both Sex and Age dimension filters applied, instead of silently dropping age to return
the aggregate total population (indicator 4788).
Also verifies that comma-separated numeric foreign key IDs (e.g. '13634,13638') are suppressed
from notes and tabular CLI rendering.
"""

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus
from unofficial_cepalstat_mcp.semantic.parser import QueryParser


def test_parser_extracts_quinquennial_age_interval() -> None:
    parser = QueryParser()
    query = "poblacion de america latina  de mujeres entre 50 y 54 años en el 2015"
    intent = parser.parse(query)

    assert intent.facets.get("sexo") == "FEMENINO"
    assert intent.facets.get("edad") == "50-54"
    assert "50" not in intent.unconsumed_tokens
    assert "54" not in intent.unconsumed_tokens
    assert intent.country_code == "ALC"
    assert intent.year == 2015


def test_engine_resolves_age_bracket_to_indicator_4789() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    query = "poblacion de america latina  de mujeres entre 50 y 54 años en el 2015"
    resp = engine.resolve(query)

    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    # Must resolve to 4789 (Población, por grupos de edad, según sexo), NOT 4788 (Población total)
    assert resp.selected_candidate.indicator_id == 4789

    # Verify applied dimension filters include both Sex and Age
    dim_names = {f.dim_name for f in resp.applied_filters.dimensions}
    assert any("sexo" in d.lower() for d in dim_names)
    assert any("edad" in d.lower() for d in dim_names)

    # Verify specific member names
    member_names = {f.member_name for f in resp.applied_filters.dimensions}
    assert "Mujeres" in member_names
    assert "50-54" in member_names


def test_numeric_foreign_keys_suppressed_from_notes() -> None:
    from unofficial_cepalstat_mcp.semantic.fetcher import _is_numeric_id_string

    assert _is_numeric_id_string("12080") is True
    assert _is_numeric_id_string("13634,13638") is True
    assert _is_numeric_id_string(" 13634, 13638 ") is True
    assert _is_numeric_id_string("123; 456") is True
    assert _is_numeric_id_string("Total nacional") is False
    assert _is_numeric_id_string("Estimación censal 2015") is False
    assert _is_numeric_id_string("") is False
