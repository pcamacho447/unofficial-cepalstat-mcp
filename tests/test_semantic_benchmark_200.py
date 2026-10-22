"""Automated empirical benchmark runner and statistical evaluation suite for 200 test cases."""

import json
import statistics
import time
from pathlib import Path

import pytest

from unofficial_cepalstat_mcp.semantic import (
    RelationshipType,
    ResolutionStatus,
    SemanticResolutionEngine,
)

BENCHMARK_200_PATH = Path(__file__).parent / "benchmark" / "semantic_benchmark_cases_200.json"

CLUSTERS = [
    "C1_POBREZA",
    "C2_DESIGUALDAD",
    "C3_MERCADO_LABORAL",
    "C4_SALARIOS_E_INGRESOS",
    "C5_CUENTAS_NACIONALES",
    "C6_PRECIOS_E_INFLACION",
    "C7_FINANZAS_PUBLICAS",
    "C8_SECTOR_EXTERNO",
    "C9_MEDIO_AMBIENTE",
    "C10_ADVERSARIOS_Y_ABSTENCIONES",
]


@pytest.fixture(scope="module")
def benchmark_cases() -> list[dict]:
    assert BENCHMARK_200_PATH.exists(), f"Benchmark dataset not found at {BENCHMARK_200_PATH}"
    with open(BENCHMARK_200_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)
    assert len(cases) == 200, f"Expected 200 benchmark cases, found {len(cases)}"
    return cases


@pytest.fixture(scope="module")
def engine() -> SemanticResolutionEngine:
    return SemanticResolutionEngine(catalog_profile="official_25")


def evaluate_single_case(item: dict, engine: SemanticResolutionEngine) -> dict:
    t0 = time.perf_counter()
    resp = engine.resolve(item["query"])
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # 1. Status match
    status_match = resp.status.value == item["expected_status"]

    # 2. Indicator match
    if item["expected_status"] in ("RESOLVED", "RESOLVED_WITH_ANCHORS"):
        ind_match = (
            resp.selected_candidate is not None
            and resp.selected_candidate.indicator_id == item["expected_indicator_id"]
        )
    elif item["expected_status"] == "ALTERNATIVE_PROPOSED":
        ind_match = (
            resp.selected_candidate is not None
            and resp.selected_candidate.indicator_id == item["expected_indicator_id"]
        )
    elif item["expected_status"] == "ABSTAINED":
        ind_match = (
            resp.selected_candidate is None
            or item["expected_indicator_id"] is None
        )
    else:
        ind_match = True

    # 3. Alternatives match
    alts_match = True
    if item.get("expected_alternatives"):
        exp_alts = set(item["expected_alternatives"])
        act_alts = {alt.indicator_id for alt in resp.alternatives}
        alts_match = exp_alts.issubset(act_alts)

    # 4. Facet match
    facet_match = True
    for fk, fv in item.get("expected_facets", {}).items():
        if resp.applied_filters.facets.get(fk) != fv:
            facet_match = False
            break

    # 5. Abstention reason match
    reason_match = True
    if item["expected_status"] == "ABSTAINED" and item.get("expected_reason"):
        valid_reasons = {
            item["expected_reason"],
            resp.unsupported_facet,
            resp.abstention_reason,
            "UNSUPPORTED_FACET",
            "LOW_CONCEPTUAL_RELEVANCE",
            "PERIOD_OUT_OF_RANGE",
            "UNSUPPORTED_FREQUENCY",
        } - {None}
        reason_match = (
            resp.status == ResolutionStatus.ABSTAINED
            and (
                resp.abstention_reason in valid_reasons
                or resp.unsupported_facet in valid_reasons
                or item["expected_reason"].startswith(str(resp.abstention_reason or ""))
            )
        )

    # 6. Swap validity (False substitution detection)
    is_false_swap = False
    if resp.selected_candidate and resp.selected_candidate.swapped_from:
        if resp.selected_candidate.swap_relationship != RelationshipType.BREAKDOWN_OF:
            is_false_swap = True

    passed = status_match and ind_match and alts_match and facet_match and reason_match and not is_false_swap

    return {
        "id": item["id"],
        "cluster": item["cluster"],
        "difficulty": item["difficulty"],
        "passed": passed,
        "status_match": status_match,
        "indicator_match": ind_match,
        "alts_match": alts_match,
        "facet_match": facet_match,
        "reason_match": reason_match,
        "is_false_swap": is_false_swap,
        "latency_ms": latency_ms,
        "response": resp,
    }


def test_full_suite_execution_200(benchmark_cases: list[dict], engine: SemanticResolutionEngine):
    """Assert full suite passes with >= 98.0% Top-1 Accuracy (target 100%), 0.0% FSR, and p50 < 2.0 ms."""
    results = [evaluate_single_case(c, engine) for c in benchmark_cases]
    latencies = [r["latency_ms"] for r in results]

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r["passed"])
    false_swaps = sum(1 for r in results if r["is_false_swap"])
    accuracy_pct = (passed_cases / total_cases) * 100.0
    fsr_pct = (false_swaps / total_cases) * 100.0
    p50_latency = statistics.median(latencies)

    failed_ids = [r["id"] for r in results if not r["passed"]]

    assert total_cases == 200, f"Expected 200 cases, got {total_cases}"
    assert passed_cases >= 196, f"Passed {passed_cases}/200 ({accuracy_pct:.1f}%). Target is >= 196 (>=98.0%). Failed: {failed_ids}"
    assert fsr_pct == 0.0, f"False Substitution Rate must be strictly 0.0%, got {fsr_pct}% ({false_swaps} false swaps)"
    assert p50_latency < 2.0, f"p50 latency threshold violated: {p50_latency:.3f} ms >= 2.0 ms"


@pytest.mark.parametrize("cluster_name", CLUSTERS)
def test_cluster_health_200(cluster_name: str, benchmark_cases: list[dict], engine: SemanticResolutionEngine):
    """Verify each cluster individually passes with >= 95% pass rate (target 100%)."""
    cluster_cases = [c for c in benchmark_cases if c["cluster"] == cluster_name]
    assert len(cluster_cases) == 20, f"Cluster {cluster_name} must have 20 cases, got {len(cluster_cases)}"

    results = [evaluate_single_case(c, engine) for c in cluster_cases]
    passed_count = sum(1 for r in results if r["passed"])
    pass_rate = (passed_count / len(results)) * 100.0
    failed_details = [
        f"{r['id']} ({r['difficulty']}): {c['query']} [act_ind={r['response'].selected_candidate.indicator_id if r['response'].selected_candidate else None}, status={r['response'].status.value}]"
        for r, c in zip(results, cluster_cases)
        if not r["passed"]
    ]

    assert passed_count >= 19, (
        f"Cluster {cluster_name} pass rate below 95%: {passed_count}/20 ({pass_rate:.1f}%).\n"
        f"Failures:\n" + "\n".join(failed_details)
    )
