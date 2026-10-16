"""Tests for CEPALSTAT Declarative Facet Ontology."""

import pytest
from statscepal.semantic.facet_ontology import (
    DEFAULT_FACET_ONTOLOGY,
    FacetOntology,
    get_default_facet_ontology,
)


def test_default_facet_ontology_covers_core_facets():
    ontology = get_default_facet_ontology()
    expected_keys = {
        "sexo",
        "area",
        "edad",
        "etnia",
        "estrato",
        "quintil",
        "educacion",
        "formalidad",
        "severidad",
        "canasta",
        "rubro",
        "moneda",
        "actividad",
    }
    registered_keys = {f.facet_key for f in ontology.all_facets()}
    assert expected_keys.issubset(registered_keys)


def test_facet_ontology_implicit_aggregate_vs_critical_breakdown():
    ontology = DEFAULT_FACET_ONTOLOGY
    # Implicit national/total defaults do NOT force a breakdown swap if canonical indicator is aggregate
    assert not ontology.is_critical_unhandled_facet("area", "NACIONAL")
    assert not ontology.is_critical_unhandled_facet("severidad", "POBREZA_TOTAL")
    assert not ontology.is_critical_unhandled_facet("sexo", "TOTAL")
    assert not ontology.is_critical_unhandled_facet("sexo", "AMBOS_SEXOS")

    # Explicit breakdown values DO require the dimension (including ETNICO_TOTAL and QUINTIL)
    assert ontology.is_critical_unhandled_facet("etnia", "ETNICO_TOTAL")
    assert ontology.is_critical_unhandled_facet("etnia", "INDIGENA")
    assert ontology.is_critical_unhandled_facet("area", "RURAL")
    assert ontology.is_critical_unhandled_facet("sexo", "FEMENINO")
    assert ontology.is_critical_unhandled_facet("edad", "INFANCIA")
    assert ontology.is_critical_unhandled_facet("estrato", "QUINTIL")
    assert ontology.is_critical_unhandled_facet("educacion", "UNIVERSITARIA")


def test_facet_ontology_dimension_classification():
    ontology = DEFAULT_FACET_ONTOLOGY
    assert ontology.classify_dimension(208, "País__ESTANDAR") == "__structural__"
    assert ontology.classify_dimension(29117, "Años__ESTANDAR") == "__structural__"
    assert ontology.classify_dimension(144, "Sexo__ESTANDAR") == "sexo"
    assert ontology.classify_dimension(326, "Área geográfica") == "area"
    assert ontology.classify_dimension(43039, "Tipo de etnia") == "etnia"
    assert ontology.classify_dimension(999999, "Dimensión desconocida xyz") is None
