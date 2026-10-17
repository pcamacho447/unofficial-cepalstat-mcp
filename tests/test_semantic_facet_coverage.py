"""Systematic multidimensional facet-coverage benchmark tests for CEPALSTAT.

Stress-tests Faceta x Familia routing, positive breakdown conmutations,
adversarial unsupported facet abstentions, and lexical boundary isolation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from statscepal.semantic.engine import SemanticResolutionEngine
from statscepal.semantic.models import ResolutionStatus
from statscepal.semantic.parser import QueryParser

COVERAGE_CASES_PATH = Path(__file__).parent / "benchmark" / "facet_coverage_cases.json"


def load_facet_coverage_cases() -> list[dict[str, Any]]:
    """Load and return the curated facet coverage benchmark test cases."""
    if not COVERAGE_CASES_PATH.exists():
        raise FileNotFoundError(f"Coverage cases file not found at {COVERAGE_CASES_PATH}")
    with open(COVERAGE_CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)
    if not isinstance(cases, list):
        raise TypeError(f"Expected list of cases, got {type(cases).__name__}")
    return cases


def test_facet_coverage_cases_file_exists_and_covers_all_13_facets():
    """Verify that the benchmark file exists, conforms to schema, and covers all 13 canonical facets."""
    assert COVERAGE_CASES_PATH.exists(), f"Coverage cases file not found at {COVERAGE_CASES_PATH}"
    cases = load_facet_coverage_cases()

    assert len(cases) >= 65, f"Expected at least 65 coverage cases, found {len(cases)}"

    # Verify all 13 canonical facets are represented
    expected_facets = {
        "etnia",
        "sexo",
        "area",
        "severidad",
        "edad",
        "quintil",
        "estrato",
        "educacion",
        "formalidad",
        "canasta",
        "rubro",
        "moneda",
        "actividad",
    }
    covered_facets = {c["facet"] for c in cases}
    missing = expected_facets - covered_facets
    assert not missing, f"Missing coverage for canonical facets: {missing}"

    # Verify each case has required schema fields
    required_fields = {
        "id",
        "facet",
        "family",
        "query",
        "case_type",
        "expected_status",
    }
    for case in cases:
        missing_fields = required_fields - set(case.keys())
        assert not missing_fields, f"Case {case.get('id')} missing fields: {missing_fields}"
        assert case["case_type"] in ("positive", "negative", "boundary"), (
            f"Case {case.get('id')} has invalid case_type: {case.get('case_type')}"
        )


def test_lexical_boundary_isolation_substrings() -> None:
    """Verify substring words do NOT trigger spurious facet activations."""
    parser = QueryParser()

    # 1. "razon" must not trigger "etnia" (from "raza")
    intent1 = parser.parse("razon de mortalidad materna en bolivia")
    assert "etnia" not in intent1.facets, f"Spurious etnia facet triggered by 'razon': {intent1.facets}"

    # 2. "panorama" and "programa" must not trigger "actividad" (from "rama")
    intent2 = parser.parse("panorama economico de america latina 2022")
    assert "actividad" not in intent2.facets, f"Spurious actividad facet triggered by 'panorama': {intent2.facets}"

    intent2b = parser.parse("programa de transferencias condicionadas en mexico")
    assert "actividad" not in intent2b.facets, f"Spurious actividad facet triggered by 'programa': {intent2b.facets}"

    # 3. "sociedad", "variedad", "novedad" must not trigger "edad"
    intent3 = parser.parse("indicadores de la sociedad de la informacion en chile")
    assert "edad" not in intent3.facets, f"Spurious edad facet triggered by 'sociedad': {intent3.facets}"

    intent3b = parser.parse("variedad de productos exportados")
    assert "edad" not in intent3b.facets, f"Spurious edad facet triggered by 'variedad': {intent3b.facets}"

    intent3c = parser.parse("novedades tributarias en la region")
    assert "edad" not in intent3c.facets, f"Spurious edad facet triggered by 'novedades': {intent3c.facets}"

    # 4. "linea aerea" must not trigger "area"
    intent4 = parser.parse("transporte en linea aerea comercial")
    assert "area" not in intent4.facets, f"Spurious area facet triggered by 'aerea': {intent4.facets}"

    # 5. "anexo" / "nexo" must not trigger "sexo"
    intent5 = parser.parse("nexo entre empleo e inversion en uruguay")
    assert "sexo" not in intent5.facets, f"Spurious sexo facet triggered by 'nexo': {intent5.facets}"

    intent5b = parser.parse("anexo estadistico del informe macroeconomico")
    assert "sexo" not in intent5b.facets, f"Spurious sexo facet triggered by 'anexo': {intent5b.facets}"


def test_root_concept_protection_against_spurious_breakdowns() -> None:
    """Verify that composite domain queries preserve their specialized root concept without spurious breakdown facets."""
    engine = SemanticResolutionEngine()

    # 1. "gasto publico en educacion" must resolve to GASTO_EDUCACION, not GASTO_PUBLICO with educacion breakdown
    resp1 = engine.resolve("gasto publico en educacion como porcentaje del pib en colombia")
    assert resp1.status in (ResolutionStatus.RESOLVED, ResolutionStatus.RESOLVED_WITH_ANCHORS), (
        f"Expected RESOLVED status, got {resp1.status}"
    )
    assert resp1.selected_candidate is not None, "Expected candidate to be selected"
    # Gasto público en educación: ID 4406 in official CEPALSTAT catalog (also accepting 2942, 3338)
    assert resp1.selected_candidate.indicator_id in {2942, 3338, 4406}, (
        f"Unexpected indicator_id {resp1.selected_candidate.indicator_id}"
    )
    assert "educacion" not in resp1.applied_filters.facets, (
        f"Spurious 'educacion' facet emitted: {resp1.applied_filters.facets}"
    )

    # 2. "gasto social publico total" must resolve to GASTO_SOCIAL without spurious rubro breakdown facet
    resp2 = engine.resolve("gasto social publico total en chile 2020")
    assert resp2.status in (ResolutionStatus.RESOLVED, ResolutionStatus.RESOLVED_WITH_ANCHORS), (
        f"Expected RESOLVED status, got {resp2.status}"
    )
    assert resp2.selected_candidate is not None, "Expected candidate to be selected"
    assert resp2.selected_candidate.indicator_id in {2943, 4405}, (
        f"Unexpected indicator_id {resp2.selected_candidate.indicator_id}"
    )
    assert "rubro" not in resp2.applied_filters.facets, (
        f"Spurious 'rubro' facet emitted: {resp2.applied_filters.facets}"
    )

    # 3. "sector real de la economia en peru" resolves without spurious rural area facet
    resp3 = engine.resolve("sector real de la economia en peru")
    assert "area" not in resp3.applied_filters.facets, (
        f"Spurious 'area' facet emitted: {resp3.applied_filters.facets}"
    )
    assert resp3.applied_filters.facets.get("area") != "RURAL"

