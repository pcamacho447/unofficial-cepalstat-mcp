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


def test_member_matcher_resolves_ethnic_dimension():
    from statscepal.semantic.matcher import DynamicMemberMatcher
    from statscepal.semantic.registry import DEFAULT_OFFICIAL_DIMENSIONS

    matcher = DynamicMemberMatcher()
    dims_3342 = DEFAULT_OFFICIAL_DIMENSIONS[3342]

    # Test general ethnic facet -> Total etnia
    success1, filters1, unhandled1 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "ETNICO_TOTAL", "area": "NACIONAL"}
    )
    assert success1 is True
    assert len(unhandled1) == 0
    ethnic_filter1 = next((f for f in filters1 if f.dim_id == 43039), None)
    assert ethnic_filter1 is not None
    assert ethnic_filter1.member_name in ("Total", "Afrodescendiente", "Indígena", "No indígena ni afrodescendiente")

    # Test specific indigenous facet
    success2, filters2, unhandled2 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "INDIGENA"}
    )
    assert success2 is True
    assert len(unhandled2) == 0
    ethnic_filter2 = next((f for f in filters2 if f.dim_id == 43039), None)
    assert ethnic_filter2 is not None
    assert ethnic_filter2.member_name == "Indígena"

    # Test specific afrodescendant facet
    success3, filters3, unhandled3 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "AFRODESCENDIENTE"}
    )
    assert success3 is True
    assert len(unhandled3) == 0
    ethnic_filter3 = next((f for f in filters3 if f.dim_id == 43039), None)
    assert ethnic_filter3 is not None
    assert ethnic_filter3.member_name == "Afrodescendiente"

    # Test specific no-indigena facet
    success4, filters4, unhandled4 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "NO_INDIGENA"}
    )
    assert success4 is True
    assert len(unhandled4) == 0
    ethnic_filter4 = next((f for f in filters4 if f.dim_id == 43039), None)
    assert ethnic_filter4 is not None
    assert ethnic_filter4.member_name == "No indígena ni afrodescendiente"

from statscepal.semantic.engine import SemanticResolutionEngine
from statscepal.semantic.models import ResolutionStatus


def test_engine_resolves_ethnic_poverty_to_3342():
    engine = SemanticResolutionEngine()

    # Exact user query that originally failed
    resp = engine.resolve("cual es la pobreza etnica en el peru del 2020")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 3342
    assert resp.applied_filters.country_code == "PER"
    assert resp.applied_filters.year == 2020

    # Ensure dimension 43039 (Tipo de etnia) is bound
    ethnic_dim = next((f for f in resp.applied_filters.dimensions if f.dim_id == 43039), None)
    assert ethnic_dim is not None
    assert ethnic_dim.member_name in ("Total", "Indígena", "Afrodescendiente", "No indígena ni afrodescendiente")


def test_engine_resolves_indigenous_poverty_to_3342_with_member():
    engine = SemanticResolutionEngine()
    resp = engine.resolve("tasa de pobreza indigena en bolivia 2021")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 3342
    assert resp.applied_filters.country_code == "BOL"

    # Must bind specific member 'Indígena'
    ethnic_dim = next((f for f in resp.applied_filters.dimensions if f.dim_id == 43039), None)
    assert ethnic_dim is not None
    assert ethnic_dim.member_name == "Indígena"


def test_engine_resolves_afrodescendant_poverty_to_3342_with_member():
    engine = SemanticResolutionEngine()
    resp = engine.resolve("pobreza extrema en afrodescendientes en colombia 2020")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 3342
    assert resp.applied_filters.country_code == "COL"

    # Must bind specific member 'Afrodescendiente'
    ethnic_dim = next((f for f in resp.applied_filters.dimensions if f.dim_id == 43039), None)
    assert ethnic_dim is not None
    assert ethnic_dim.member_name == "Afrodescendiente"


def test_engine_abstains_on_unsupported_facet_without_false_substitution():
    engine = SemanticResolutionEngine()
    # A facet with no breakdown indicator anywhere
    resp = engine.resolve("pobreza monetaria por nivel de coeficiencia intelectual en uruguay")
    assert resp.status == ResolutionStatus.ABSTAINED
