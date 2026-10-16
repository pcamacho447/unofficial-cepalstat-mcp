"""Tests for multidimensional breakdowns and facet conmutation."""
import pytest
from statscepal.semantic.parser import QueryParser


def test_parser_extracts_ethnic_facet():
    parser = QueryParser()

    # Query with general 'etnica' (the user's motivating query)
    intent1 = parser.parse("cual es la pobreza etnica en el peru del 2020")
    assert intent1.root_concept == "POBREZA"
    assert "etnia" in intent1.facets
    assert intent1.facets["etnia"] == "ETNICO_TOTAL"

    # Query with specific 'indigena'
    intent2 = parser.parse("tasa de pobreza indigena en bolivia 2021")
    assert intent2.root_concept == "POBREZA"
    assert intent2.facets.get("etnia") == "INDIGENA"

    # Query with 'afrodescendiente'
    intent3 = parser.parse("pobreza extrema en afrodescendientes en colombia")
    assert intent3.root_concept == "POBREZA"
    assert intent3.facets.get("etnia") == "AFRODESCENDIENTE"

    # Negative check: non-ethnic query has no etnia facet
    intent4 = parser.parse("tasa de desocupacion en chile 2022")
    assert "etnia" not in intent4.facets
