"""Tests for generic dimensional gating and ontology-driven facet extraction."""

import inspect
from statscepal.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY, get_default_facet_ontology
from statscepal.semantic.parser import QueryParser
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
