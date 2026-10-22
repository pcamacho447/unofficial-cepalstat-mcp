"""Tests for motivating user queries: underlying inflation, gender gap, and tax revenues."""
import pytest

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus
from unofficial_cepalstat_mcp.semantic.parser import QueryParser


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


def test_brecha_ingresos_laborales_mujeres_y_hombres_routes_to_3333_without_unilateral_filter(engine, parser):
    res = engine.resolve("brecha de ingresos laborales entre mujeres y hombres en argentina")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 3333
    # Crucial: Must NOT unilaterally filter to just Mujeres or just Hombres
    assert res.applied_filters.facets.get("sexo") is None or res.applied_filters.facets.get("sexo") in ("AMBOS", "RELACION", "BRECHA")
    # Facets from parser must not contain single-sex filter
    intent = parser.parse("brecha de ingresos laborales entre mujeres y hombres en argentina")
    assert intent.facets.get("sexo") is None or intent.facets.get("sexo") not in ("MUJERES", "HOMBRES")


def test_relacion_ingreso_medio_mujeres_y_hombres_routes_to_3333(engine):
    res = engine.resolve("relacion de ingreso medio entre mujeres y hombres en chile")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate.indicator_id == 3333


def test_brecha_salarial_de_genero_routes_to_3333(engine):
    res = engine.resolve("brecha salarial de genero en uruguay")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate.indicator_id == 3333


def test_ingreso_laboral_solo_mujeres_still_routes_to_3339_with_mujeres_facet(engine):
    res = engine.resolve("ingreso laboral de las mujeres en argentina")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate.indicator_id == 3339
    assert res.applied_filters.facets.get("sexo") in ("FEMENINO", "MUJERES")


def test_ingresos_tributarios_underspecified_generates_conversational_hint_and_alternative(engine):
    res = engine.resolve("quiero que me des los ingresos tributarios del peru en 2022")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate.indicator_id == 1242
    # Conversational hint must not be None and must mention alternative 845
    assert res.conversational_hint is not None
    assert "845" in res.conversational_hint
    # Trace must log the decision audit
    assert any("845" in log for log in res.execution_trace)


def test_ingresos_tributarios_moneda_nacional_routes_to_845(engine):
    res = engine.resolve("ingresos tributarios en moneda nacional en peru 2022")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate.indicator_id == 845


def test_ingresos_tributarios_porcentaje_pib_routes_to_1242(engine):
    res = engine.resolve("ingresos tributarios en porcentaje del pib en peru 2022")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate.indicator_id == 1242


