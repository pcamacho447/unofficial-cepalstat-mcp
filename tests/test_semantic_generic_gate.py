"""Tests for generic dimensional gating and ontology-driven facet extraction."""

import inspect
from pathlib import Path

from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.dimensions import Dimension, Member
from unofficial_cepalstat_mcp.semantic.facet_ontology import (
    get_default_facet_ontology,
)
from unofficial_cepalstat_mcp.semantic.models import RelationshipType
from unofficial_cepalstat_mcp.semantic.parser import QueryParser
from unofficial_cepalstat_mcp.semantic.registry import SemanticRegistry
from unofficial_cepalstat_mcp.semantic.thesaurus import get_default_thesaurus


def test_facet_ontology_extracts_facets_from_query_generically():
    ontology = get_default_facet_ontology()
    thesaurus = get_default_thesaurus()

    # 1. Direct FacetOntology.extract_facets_from_query test
    assert hasattr(ontology, "extract_facets_from_query"), "FacetOntology must implement extract_facets_from_query"

    # Test etnia triggers
    facets_indigena = ontology.extract_facets_from_query("pueblos indigenas en colombia", thesaurus)
    assert facets_indigena.get("etnia") == "INDIGENA"

    facets_afro = ontology.extract_facets_from_query("afrodescendientes en brasil", thesaurus)
    assert facets_afro.get("etnia") == "AFRODESCENDIENTE"

    facets_etnico = ontology.extract_facets_from_query("pobreza segun etnia", thesaurus)
    assert facets_etnico.get("etnia") == "ETNICO_TOTAL"

    # Test educacion triggers
    facets_edu = ontology.extract_facets_from_query("educacion universitaria en chile", thesaurus)
    assert facets_edu.get("educacion") == "UNIVERSITARIA"

    # 2. QueryParser integration and source code inspection
    parser = QueryParser()
    assert hasattr(parser, "ontology"), "QueryParser must have an injected ontology attribute"

    # Parsing queries with etnia
    intent_indigena = parser.parse("pobreza en pueblos indigenas de colombia 2020")
    assert intent_indigena.facets.get("etnia") == "INDIGENA"

    intent_afro = parser.parse("desempleo afrodescendientes en brasil 2021")
    assert intent_afro.facets.get("etnia") == "AFRODESCENDIENTE"

    intent_etnia = parser.parse("pobreza por etnia en bolivia 2019")
    assert intent_etnia.facets.get("etnia") == "ETNICO_TOTAL"

    # Parsing queries with educacion
    intent_edu = parser.parse("desempleo segun educacion universitaria en chile 2020")
    assert intent_edu.facets.get("educacion") == "UNIVERSITARIA"

    # Guardrail: Gasto público en educación should not produce spurious 'educacion' facet
    intent_gasto = parser.parse("gasto publico en educacion de chile 2020")
    assert intent_gasto.root_concept == "GASTO_EDUCACION"
    assert "educacion" not in intent_gasto.facets

    # Inspect QueryParser.parse to ensure no hardcoded facets["etnia"]
    source = inspect.getsource(QueryParser.parse)
    assert 'facets["etnia"]' not in source, "QueryParser.parse must not contain hardcoded facets[\"etnia\"]"
    assert "facets['etnia']" not in source, "QueryParser.parse must not contain hardcoded facets['etnia']"


def test_semantic_registry_builds_in_memory_index_from_sqlite_and_synthesizes_metadata(tmp_path: Path):
    db_path = tmp_path / "test_semantic_in_memory.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    # Insert uncurated indicator 90001 into master_indicators
    with store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO master_indicators (indicator_id, name, order_num, theme, area, subarea, full_path, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                90001,
                "Pobreza por nivel de instrucción y área geográfica",
                1,
                "Social",
                "Pobreza",
                "Educación y Pobreza",
                "Social > Pobreza > Educación y Pobreza",
                "2026-10-16",
            ),
        )

    # Store dimensions for 90001 (including 326: Área geográfica, 500: Tipo de pobreza, and 88001: Nivel de educación)
    dims_90001 = [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=500,
            name="Tipo de pobreza",
            members=[Member(id=501, name="Pobreza extrema"), Member(id=502, name="Pobreza")],
        ),
        Dimension(
            id=88001,
            name="Nivel de educación",
            members=[
                Member(id=88010, name="Primaria"),
                Member(id=88020, name="Secundaria"),
                Member(id=88030, name="Universitaria"),
            ],
        ),
    ]
    store.store_indicator_dimensions(90001, dims_90001)

    # Store bidirectional inferred breakdown_of edge between 3328 and 90001
    store.store_relationship(3328, 90001, "breakdown_of", provenance="inferred")
    store.store_relationship(90001, 3328, "breakdown_of", provenance="inferred")

    # Creates SemanticRegistry(store=store)
    registry = SemanticRegistry(store=store)

    # Asserts registry.get_indicator(90001) exists and registry.get_supported_facets(90001) contains {"educacion", "area", "severidad"}
    ind = registry.get_indicator(90001)
    assert ind is not None
    assert ind.indicator_id == 90001
    assert ind.name == "Pobreza por nivel de instrucción y área geográfica"
    facets = registry.get_supported_facets(90001)
    assert {"educacion", "area", "severidad"}.issubset(facets)

    # Asserts registry.get_relationships(3328) contains 90001: RelationshipType.BREAKDOWN_OF alongside existing curated relationships (3342, 3341, etc.)
    rels_3328 = registry.get_relationships(3328)
    assert rels_3328.get(90001) == RelationshipType.BREAKDOWN_OF
    assert rels_3328.get(3342) == RelationshipType.BREAKDOWN_OF
    assert rels_3328.get(3341) == RelationshipType.BREAKDOWN_OF


def test_engine_stage4_has_zero_hardcoded_facet_or_indicator_literals():
    from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine

    source = inspect.getsource(SemanticResolutionEngine.resolve)
    assert '"etnia"' not in source, "SemanticResolutionEngine.resolve must not contain hardcoded \"etnia\""
    assert "'etnia'" not in source, "SemanticResolutionEngine.resolve must not contain hardcoded 'etnia'"
    assert "POBREZA_TOTAL" not in source, "SemanticResolutionEngine.resolve must not contain hardcoded POBREZA_TOTAL"
    assert "3342" not in source, "SemanticResolutionEngine.resolve must not contain hardcoded 3342"
    assert "DEFAULT_OFFICIAL_DIMENSIONS" not in source, "SemanticResolutionEngine.resolve must not contain hardcoded DEFAULT_OFFICIAL_DIMENSIONS"


def test_engine_routes_generically_to_sqlite_inferred_breakdown_indicator(tmp_path: Path):
    from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
    from unofficial_cepalstat_mcp.semantic.graph_builder import GraphBuilder
    from unofficial_cepalstat_mcp.semantic.models import RelationshipType, ResolutionStatus

    db_path = tmp_path / "test_engine_sqlite_inferred.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    # Insert 3328 and uncurated 90001 (poverty by education and area) into master_indicators
    with store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO master_indicators (indicator_id, name, theme, area, subarea, full_path)
            VALUES
            (3328, 'Población en situación de pobreza extrema y pobreza, por área', 'Sociales', 'Pobreza', '', 'Sociales > Pobreza'),
            (90001, 'Población en situación de pobreza extrema y pobreza, por nivel de educación y área geográfica', 'Sociales', 'Pobreza', '', 'Sociales > Pobreza')
            """
        )

    # Store dimensions for 3328 and 90001
    dims_3328 = [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=500,
            name="Tipo de pobreza",
            members=[Member(id=501, name="Pobreza extrema"), Member(id=502, name="Total pobreza")],
        ),
    ]
    dims_90001 = [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=500,
            name="Tipo de pobreza",
            members=[Member(id=501, name="Pobreza extrema"), Member(id=502, name="Total pobreza")],
        ),
        Dimension(
            id=88001,
            name="Nivel de educación",
            members=[
                Member(id=88010, name="Primaria"),
                Member(id=88020, name="Secundaria"),
                Member(id=88012, name="Universitaria"),
            ],
        ),
    ]
    store.store_indicator_dimensions(3328, dims_3328)
    store.store_indicator_dimensions(90001, dims_90001)

    # Run GraphBuilder.build_breakdown_graph() to infer (3328, 90001) as breakdown_of
    builder = GraphBuilder(store=store)
    report = builder.build_breakdown_graph(persist=True, seed_curated=False)
    assert any((e.parent_id == 3328 and e.child_id == 90001) for e in report.inferred_edges)

    # Resolve "pobreza segun educacion universitaria en colombia 2021" via engine
    registry = SemanticRegistry(store=store)
    engine = SemanticResolutionEngine(registry=registry)
    resp = engine.resolve("pobreza segun educacion universitaria en colombia 2021")

    # Assertions
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 90001
    assert resp.selected_candidate.swapped_from == 3328
    assert resp.selected_candidate.swap_relationship == RelationshipType.BREAKDOWN_OF

    # Assert dim_id == 88001 is bound to member 88012: Universitaria
    edu_filter = next((f for f in resp.applied_filters.dimensions if f.dim_id == 88001), None)
    assert edu_filter is not None
    assert edu_filter.member_id == 88012
    assert edu_filter.member_name == "Universitaria"


def test_stage3_ambiguity_conversational_hint_matches_selected_and_alternative_indicators():
    """Verify Stage 3 ambiguity conversational_hint describes the actual selected indicator and its alternatives, never hardcoding ID 127 for non-labor queries."""
    from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
    from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus

    engine = SemanticResolutionEngine()

    for query, expected_primary_id, expected_alt_id in [
        ("cuentas fiscales en colombia 2022", 1240, 1241),
        ("economia de chile en 2022", 729, 730),
        ("inflacion sectorial en peru 2022", 2928, 2929),
        ("sector externo en mexico 2022", 1243, 1244),
        ("emisiones de gases de efecto invernadero en brasil 2021", 5681, 5682),
    ]:
        res = engine.resolve(query)
        assert res.status == ResolutionStatus.ALTERNATIVE_PROPOSED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id == expected_primary_id
        assert res.conversational_hint is not None
        assert str(expected_primary_id) in res.conversational_hint
        assert str(expected_alt_id) in res.conversational_hint
        assert "127" not in res.conversational_hint
        assert "119" not in res.conversational_hint


