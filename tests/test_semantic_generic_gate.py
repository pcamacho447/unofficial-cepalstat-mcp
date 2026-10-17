"""Tests for generic dimensional gating and ontology-driven facet extraction."""

import inspect
from pathlib import Path
from statscepal.catalog.store import CatalogStore
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY, get_default_facet_ontology
from statscepal.semantic.models import RelationshipType
from statscepal.semantic.parser import QueryParser
from statscepal.semantic.registry import SemanticRegistry
from statscepal.semantic.thesaurus import get_default_thesaurus


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
