"""Automated empirical benchmark runner and statistical evaluation suite for 40 adversarial cases.

Curated by the Anti-Consensus Club to stress-test the SemanticResolutionEngine against:
- Sectoral and microeconomic granularity traps
- Institutional, accounting perimeter, and nominal vs. real traps
- Social, demographic, and ODS boundary traps
- Temporal dynamics, seasonal adjustment, and frequency traps
"""

import json
from pathlib import Path
import statistics
import time
import pytest
from statscepal.semantic import (
    ResolutionStatus,
    SemanticResolutionEngine,
)

BENCHMARK_40_PATH = Path(__file__).parent / "benchmark" / "adversarial_benchmark_cases_40.json"

CLUSTERS = [
    "FAMILIA_A_SECTORIAL_MICRO",
    "FAMILIA_B_ALCANCE_INSTITUCIONAL",
    "FAMILIA_C_FRONTERAS_SOCIALES_ODS",
    "FAMILIA_D_DINAMICA_TEMPORAL_FILTROS",
]


def _load_adversarial_cases() -> list[dict]:
    if BENCHMARK_40_PATH.exists():
        with open(BENCHMARK_40_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


ADVERSARIAL_CASES = _load_adversarial_cases()


@pytest.fixture(scope="module")
def adversarial_cases() -> list[dict]:
    assert BENCHMARK_40_PATH.exists(), f"Adversarial benchmark dataset not found at {BENCHMARK_40_PATH}"
    cases = ADVERSARIAL_CASES
    assert len(cases) == 40, f"Expected 40 adversarial cases, found {len(cases)}"
    return cases


@pytest.fixture(scope="module")
def engine() -> SemanticResolutionEngine:
    return SemanticResolutionEngine(catalog_profile="official_25")


def evaluate_single_adversarial_case(item: dict, engine: SemanticResolutionEngine) -> dict:
    t0 = time.perf_counter()
    resp = engine.resolve(item["query"])
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # 1. Status match
    status_match = resp.status.value == item["expected_status"]

    # 2. Indicator match & score constraint
    ind_match = True
    score_ok = True
    hint_ok = True

    if item["expected_status"] == "ALTERNATIVE_PROPOSED":
        if resp.selected_candidate is None:
            ind_match = False
        else:
            if item.get("expected_indicator_id") is not None:
                ind_match = resp.selected_candidate.indicator_id == item["expected_indicator_id"]
            if item.get("max_score") is not None:
                score_ok = resp.selected_candidate.relevance_score <= item["max_score"] + 1e-4
            hint_ok = bool(resp.conversational_hint)
    elif item["expected_status"] == "ABSTAINED":
        ind_match = resp.selected_candidate is None

    # 3. Forbidden indicator substitution check (Critical FSR Gate)
    forbidden_violation = False
    if item.get("forbidden_indicator_id") is not None and resp.selected_candidate is not None:
        if resp.selected_candidate.indicator_id == item["forbidden_indicator_id"]:
            forbidden_violation = True

    # 4. Reason match if expected
    reason_match = True
    if item["expected_status"] == "ABSTAINED" and item.get("expected_reason"):
        act_reason = str(resp.abstention_reason or "")
        reason_match = item["expected_reason"] in act_reason

    passed = (
        status_match
        and ind_match
        and score_ok
        and hint_ok
        and reason_match
        and not forbidden_violation
    )

    return {
        "id": item["id"],
        "cluster": item["cluster"],
        "query": item["query"],
        "passed": passed,
        "status_match": status_match,
        "indicator_match": ind_match,
        "score_ok": score_ok,
        "hint_ok": hint_ok,
        "reason_match": reason_match,
        "forbidden_violation": forbidden_violation,
        "actual_status": resp.status.value,
        "actual_candidate": resp.selected_candidate.indicator_id if resp.selected_candidate else None,
        "actual_score": resp.selected_candidate.relevance_score if resp.selected_candidate else None,
        "actual_reason": resp.abstention_reason,
        "actual_hint": resp.conversational_hint,
        "latency_ms": latency_ms,
    }


def test_adversarial_suite_summary(adversarial_cases: list[dict], engine: SemanticResolutionEngine) -> None:
    """Evaluates all 40 adversarial benchmark cases and asserts statistical quality gates."""
    results = [evaluate_single_adversarial_case(case, engine) for case in adversarial_cases]

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    forbidden_failures = [r for r in results if r["forbidden_violation"]]
    fsr = (len(forbidden_failures) / total) * 100.0
    accuracy = (passed / total) * 100.0

    latencies = [r["latency_ms"] for r in results]
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

    print("\n" + "=" * 78)
    print("CEPALSTAT ADVERSARIAL BENCHMARK REPORT (40 CASES - ANTI-CONSENSUS CLUB)")
    print("=" * 78)
    print(f"Total Cases:                 {total}")
    print(f"Passed Cases:                {passed}/{total} ({accuracy:.1f}%)")
    print(f"False Substitution Violations: {len(forbidden_failures)} ({fsr:.2f}%)")
    print(f"Latency p50:                 {p50_latency:.3f} ms")
    print(f"Latency p95:                 {p95_latency:.3f} ms")
    print("-" * 78)

    # Breakdown by cluster
    for cluster in CLUSTERS:
        cluster_results = [r for r in results if r["cluster"] == cluster]
        c_passed = sum(1 for r in cluster_results if r["passed"])
        c_tot = len(cluster_results)
        c_acc = (c_passed / c_tot) * 100.0 if c_tot else 0.0
        print(f"  [{cluster}]: {c_passed}/{c_tot} passed ({c_acc:.1f}%)")

    # Print failed cases for immediate debugging
    case_map = {c["id"]: c for c in adversarial_cases}
    failed = [r for r in results if not r["passed"]]
    if failed:
        print("\nFailures Detail:")
        for f in failed:
            exp_status = case_map.get(f["id"], {}).get("expected_status")
            print(
                f"  - {f['id']} | Query: '{f['query']}' | "
                f"Exp: {exp_status} | "
                f"Act: {f['actual_status']} (Cand: {f['actual_candidate']}, Score: {f['actual_score']}) | "
                f"Forbidden: {f['forbidden_violation']}"
            )
    print("=" * 78)

    # Strict Acceptance Gates
    assert fsr == 0.0, f"False Substitution Rate must strictly be 0.00%, got {fsr:.2f}%"
    assert accuracy == 100.0, f"Adversarial Benchmark Accuracy must be 100.0%, got {accuracy:.1f}% ({passed}/{total})"
    assert p50_latency < 1.0, f"Adversarial latency p50 must be < 1.0ms, got {p50_latency:.3f}ms"


@pytest.mark.parametrize("case", ADVERSARIAL_CASES, ids=[c["id"] for c in ADVERSARIAL_CASES])
def test_individual_adversarial_case(case: dict, engine: SemanticResolutionEngine) -> None:
    """Verifies each adversarial query independently for clear granular pytest reporting."""
    result = evaluate_single_adversarial_case(case, engine)
    assert result["passed"], (
        f"Case {case['id']} FAILED: Query='{case['query']}'. "
        f"Expected status={case['expected_status']}, indicator={case.get('expected_indicator_id')}. "
        f"Got status={result['actual_status']}, candidate={result['actual_candidate']}, "
        f"score={result['actual_score']}, reason={result['actual_reason']}, hint={result['actual_hint']}. "
        f"Forbidden violation: {result['forbidden_violation']}"
    )
