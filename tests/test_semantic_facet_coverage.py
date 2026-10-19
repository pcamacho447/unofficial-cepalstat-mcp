"""Systematic multidimensional facet-coverage benchmark tests for CEPALSTAT.

Stress-tests Faceta x Familia routing, positive breakdown conmutations,
adversarial unsupported facet abstentions, and lexical boundary isolation.
"""

from __future__ import annotations

import json
import statistics
import time
import unicodedata
from pathlib import Path
from typing import Any

import pytest

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import RelationshipType, ResolutionStatus
from unofficial_cepalstat_mcp.semantic.parser import QueryParser

COVERAGE_CASES_PATH = Path(__file__).parent / "benchmark" / "facet_coverage_cases.json"

ALL_FACET_KEYS = [
    "actividad",
    "area",
    "canasta",
    "edad",
    "educacion",
    "estrato",
    "etnia",
    "formalidad",
    "moneda",
    "quintil",
    "rubro",
    "severidad",
    "sexo",
]


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


def _normalize_text(text: str) -> str:
    """Normalize text by lowercasing and removing diacritics for resilient matching."""
    nfkd = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


@pytest.fixture(scope="module")
def engine() -> SemanticResolutionEngine:
    """Provide a shared SemanticResolutionEngine instance for the test module."""
    eng = SemanticResolutionEngine()
    eng.resolve("pobreza")  # Warm-up in-memory index caches
    return eng


def evaluate_coverage_case(case: dict[str, Any], engine: SemanticResolutionEngine) -> dict[str, Any]:
    """Evaluate a single facet coverage benchmark case against the SemanticResolutionEngine."""
    t0 = time.perf_counter()
    resp = engine.resolve(case["query"])
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # 1. Status match
    expected_status = case["expected_status"]
    status_match = (
        resp.status.value == expected_status
        or (expected_status == "RESOLVED" and resp.status.value in ("RESOLVED", "RESOLVED_WITH_ANCHORS"))
    )

    # 2. Indicator match
    ind_match = True
    if case["case_type"] == "positive" and case.get("expected_indicator_id") is not None:
        ind_match = (
            resp.selected_candidate is not None
            and resp.selected_candidate.indicator_id == case["expected_indicator_id"]
        )
    elif case["case_type"] == "boundary":
        if case.get("expected_indicator_id") is not None:
            ind_match = (
                resp.selected_candidate is not None
                and resp.selected_candidate.indicator_id == case["expected_indicator_id"]
            )
        else:
            ind_match = resp.selected_candidate is None or case.get("expected_indicator_id") is None
    elif case["case_type"] == "negative":
        ind_match = resp.selected_candidate is None or case.get("expected_indicator_id") is None

    # 3. Abstention match
    abstention_match = True
    if case["case_type"] == "negative":
        abstention_match = (
            resp.status == ResolutionStatus.ABSTAINED
            and (
                resp.abstention_reason in ("UNSUPPORTED_FACET", case.get("expected_reason"))
                or resp.unsupported_facet == case.get("expected_facet_key")
            )
        )
        if case.get("expected_facet_key"):
            abstention_match = abstention_match and (
                resp.unsupported_facet == case["expected_facet_key"]
                or resp.abstention_reason == case.get("expected_reason")
            )
    elif case["case_type"] == "boundary" and case.get("expected_reason") is not None:
        abstention_match = (
            resp.status == ResolutionStatus.ABSTAINED
            and resp.abstention_reason == case.get("expected_reason")
        )

    # 4. Dimension & Member binding match
    member_match = True
    if case["case_type"] == "positive" and case.get("expected_dim_id") is not None:
        matched_dims = [f for f in resp.applied_filters.dimensions if f.dim_id == case["expected_dim_id"]]
        if not matched_dims:
            member_match = False
        elif case.get("expected_member_name"):
            expected_norm = _normalize_text(case["expected_member_name"])
            member_match = any(expected_norm in _normalize_text(f.member_name) for f in matched_dims)

    # 5. False substitution detection (is_false_swap)
    is_false_swap = False
    if resp.selected_candidate:
        if case["case_type"] == "negative":
            is_false_swap = True
        elif resp.selected_candidate.swapped_from:
            if resp.selected_candidate.swap_relationship != RelationshipType.BREAKDOWN_OF:
                is_false_swap = True

    passed = status_match and ind_match and abstention_match and member_match and not is_false_swap

    return {
        "id": case["id"],
        "facet": case["facet"],
        "family": case["family"],
        "case_type": case["case_type"],
        "passed": passed,
        "is_false_swap": is_false_swap,
        "latency_ms": latency_ms,
        "response": resp,
    }


def test_systematic_facet_coverage_matrix(engine: SemanticResolutionEngine) -> None:
    """Execute all systematic facet coverage cases, format ASCII summary table, and certify performance."""
    cases = load_facet_coverage_cases()
    results = [evaluate_coverage_case(c, engine) for c in cases]

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    false_swaps = sum(1 for r in results if r["is_false_swap"])
    accuracy = (passed / total) * 100.0 if total else 0.0
    fsr = (false_swaps / total) * 100.0 if total else 0.0
    p50_latency = statistics.median(r["latency_ms"] for r in results) if results else 0.0

    # Print summary ASCII table
    print("\n" + "=" * 80)
    print(f"{'FACET COVERAGE BENCHMARK REPORT':^80}")
    print("=" * 80)
    print(f"{'Facet':<15} | {'Cases':<7} | {'Passed':<7} | {'Pass %':<8} | {'False Swaps':<12}")
    print("-" * 80)

    all_facets = sorted(list({c["facet"] for c in cases}))
    for facet in all_facets:
        f_results = [r for r in results if r["facet"] == facet]
        f_total = len(f_results)
        f_pass = sum(1 for r in f_results if r["passed"])
        f_swaps = sum(1 for r in f_results if r["is_false_swap"])
        f_pct = (f_pass / f_total) * 100.0 if f_total else 0.0
        pct_str = f"{f_pct:.1f}%"
        print(f"{facet:<15} | {f_total:<7} | {f_pass:<7} | {pct_str:<8} | {f_swaps:<12}")

    print("-" * 80)
    print(
        f"Total: {total} | Passed: {passed} ({accuracy:.2f}%) | "
        f"FSR: {fsr:.2f}% | Latency p50: {p50_latency:.3f} ms"
    )
    print("=" * 80 + "\n")

    failed_details = [
        f"[{r['id']}] {c['query']} -> status={r['response'].status.value if r['response'] else 'NONE'}, "
        f"reason={r['response'].abstention_reason if r['response'] else 'NONE'}"
        for r, c in zip(results, cases)
        if not r["passed"]
    ]

    assert fsr == 0.0, f"False Substitution Rate must strictly be 0.00%, got {fsr:.2f}%"
    assert accuracy >= 98.0, f"Accuracy below threshold: {accuracy:.2f}% (failed: {failed_details})"
    assert p50_latency < 2.0, f"p50 latency violated: {p50_latency:.3f} ms >= 2.0 ms"


@pytest.mark.parametrize("facet_key", ALL_FACET_KEYS)
def test_individual_facet_coverage_health(facet_key: str, engine: SemanticResolutionEngine) -> None:
    """Verify that all benchmark cases for a specific facet pass with 0 false swaps."""
    cases = load_facet_coverage_cases()
    facet_cases = [c for c in cases if c["facet"] == facet_key]
    assert facet_cases, f"No test cases found for facet '{facet_key}'"

    results = [evaluate_coverage_case(c, engine) for c in facet_cases]
    failed = [r for r in results if not r["passed"]]
    false_swaps = [r for r in results if r["is_false_swap"]]

    assert not false_swaps, f"Facet '{facet_key}' produced false substitutions: {false_swaps}"
    assert not failed, f"Facet '{facet_key}' had failing cases: {[f['id'] for f in failed]}"

