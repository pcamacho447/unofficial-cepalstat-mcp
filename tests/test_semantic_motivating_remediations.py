"""Tests for motivating user queries: underlying inflation, gender gap, and tax revenues."""
import pytest
from statscepal.semantic.engine import SemanticResolutionEngine
from statscepal.semantic.models import ResolutionStatus
from statscepal.semantic.parser import QueryParser


@pytest.fixture
def engine():
    return SemanticResolutionEngine()


@pytest.fixture
def parser():
    return QueryParser()


def test_inflacion_subyacente_parser_extracts_subyacente_concept(parser):
    intent = parser.parse("inflacion subyacente en chile")
    assert intent.root_concept == "IPC_SUBYACENTE"
    assert intent.country_name == "Chile"


def test_inflacion_subyacente_routes_to_4145_and_never_2928(engine):
    res = engine.resolve("inflacion subyacente en chile")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4145
    assert res.selected_candidate.indicator_id != 2928
    assert "subyacente" in res.selected_candidate.name.lower()


def test_inflacion_core_routes_to_4145(engine):
    res = engine.resolve("inflacion core anual en mexico")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate.indicator_id == 4145


def test_inflacion_general_still_routes_to_2928(engine):
    res = engine.resolve("inflacion anual en chile")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate.indicator_id == 2928
