"""Automated empirical benchmark runner and statistical evaluation suite for 100 full-catalog scale queries.

Covers all 23 CEPALSTAT areas present in master_indicators:
- 80 positive queries across all 23 thematic domains
- 20 cross-domain adversarial and geographical scope traps
"""

import json
import statistics
import time
from pathlib import Path
from typing import Any

import pytest

from unofficial_cepalstat_mcp.semantic import (
    RelationshipType,
    ResolutionStatus,
    SemanticResolutionEngine,
)

BENCHMARK_100_PATH = Path(__file__).parent / "benchmark" / "catalog_scale_benchmark_cases_100.json"


def _load_scale_cases() -> list[dict[str, Any]]:
    if BENCHMARK_100_PATH.exists():
        with open(BENCHMARK_100_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


SCALE_CASES = _load_scale_cases()


@pytest.fixture(scope="module")
def scale_cases() -> list[dict[str, Any]]:
    assert BENCHMARK_100_PATH.exists(), f"Benchmark dataset not found at {BENCHMARK_100_PATH}"
    cases = SCALE_CASES
    assert len(cases) == 100, f"Expected 100 scale benchmark cases, found {len(cases)}"
    return cases


@pytest.fixture(scope="module")
def engine() -> SemanticResolutionEngine:
    return SemanticResolutionEngine(catalog_profile="full_catalog")


def evaluate_single_scale_case(item: dict[str, Any], engine: SemanticResolutionEngine) -> dict[str, Any]:
    t0 = time.perf_counter()
    resp = engine.resolve(item["query"])
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # 1. Status match
    exp_status = item["expected_status"]
    status_match = resp.status.value == exp_status

    # 2. Indicator match
    ind_match = True
    act_id = resp.selected_candidate.indicator_id if resp.selected_candidate else None

    if exp_status in ("RESOLVED", "RESOLVED_WITH_ANCHORS", "ALTERNATIVE_PROPOSED"):
        if resp.selected_candidate is None:
            ind_match = False
        elif item.get("expected_indicator_ids"):
            ind_match = act_id in item["expected_indicator_ids"]
        elif item.get("expected_indicator_id") is not None:
            ind_match = act_id == item["expected_indicator_id"]
    elif exp_status == "ABSTAINED":
        ind_match = resp.selected_candidate is None

    # 3. False substitution detection (Critical FSR Gate)
    forbidden_violation = False
    if item.get("forbidden_indicator_id") is not None and resp.selected_candidate is not None:
        if act_id == item["forbidden_indicator_id"]:
            forbidden_violation = True

    if exp_status == "ABSTAINED" and resp.status != ResolutionStatus.ABSTAINED:
        forbidden_violation = True

    is_false_swap = False
    if resp.selected_candidate and resp.selected_candidate.swapped_from:
        if resp.selected_candidate.swap_relationship != RelationshipType.BREAKDOWN_OF:
            is_false_swap = True

    # 4. Reason match if specified for ABSTAINED
    reason_match = True
    if exp_status == "ABSTAINED" and item.get("expected_reason"):
        act_reason = str(resp.abstention_reason or "")
        reason_match = item["expected_reason"] in act_reason

    passed = (
        status_match
        and ind_match
        and reason_match
        and not forbidden_violation
        and not is_false_swap
    )

    return {
        "id": item["id"],
        "area": item["area"],
        "query": item["query"],
        "passed": passed,
        "status_match": status_match,
        "indicator_match": ind_match,
        "reason_match": reason_match,
        "forbidden_violation": forbidden_violation,
        "is_false_swap": is_false_swap,
        "actual_status": resp.status.value,
        "actual_candidate": act_id,
        "actual_reason": resp.abstention_reason,
        "latency_ms": latency_ms,
    }


def test_catalog_scale_benchmark_summary(
    scale_cases: list[dict[str, Any]],
    engine: SemanticResolutionEngine,
) -> None:
    """Evaluates all 100 scale queries across all 23 areas and asserts statistical quality gates."""
    # Warm-up pass to ensure JIT/index cache hydration
    for case in scale_cases:
        engine.resolve(case["query"])

    # Timed evaluation pass
    results = [evaluate_single_scale_case(case, engine) for case in scale_cases]

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    forbidden_failures = [r for r in results if r["forbidden_violation"] or r["is_false_swap"]]
    fsr = (len(forbidden_failures) / total) * 100.0
    accuracy = (passed / total) * 100.0

    latencies = [r["latency_ms"] for r in results]
    p50_latency = statistics.median(latencies)
    p95_latency = (
        statistics.quantiles(latencies, n=100)[94]
        if len(latencies) >= 100
        else (statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies))
    )

    print("\n" + "=" * 78)
    print("CEPALSTAT FULL-CATALOG SCALE BENCHMARK REPORT (100 QUERIES - 23 AREAS)")
    print("=" * 78)
    print(f"Total Cases:                   {total}")
    print(f"Passed Cases:                  {passed}/{total} ({accuracy:.2f}%)")
    print(f"False Substitution Violations: {len(forbidden_failures)} ({fsr:.2f}%)")
    print(f"Latency p50:                   {p50_latency:.4f} ms (Target < 0.50 ms)")
    print(f"Latency p95:                   {p95_latency:.4f} ms (Target < 2.00 ms)")
    print("-" * 78)

    # Breakdown by Area
    distinct_areas = sorted({c["area"] for c in scale_cases})
    for area in distinct_areas:
        area_res = [r for r in results if r["area"] == area]
        a_passed = sum(1 for r in area_res if r["passed"])
        a_tot = len(area_res)
        a_acc = (a_passed / a_tot) * 100.0 if a_tot else 0.0
        print(f"  [{area[:48]:<48}]: {a_passed:>2}/{a_tot:<2} ({a_acc:.1f}%)")

    # Failures Detail
    failed = [r for r in results if not r["passed"]]
    if failed:
        print("\nFailures Detail:")
        for f in failed:
            print(
                f"  - {f['id']} | Area: {f['area']} | Query: '{f['query']}' | "
                f"Act: {f['actual_status']} (Cand: {f['actual_candidate']}, Reason: {f['actual_reason']}) | "
                f"Viol: {f['forbidden_violation']}"
            )
    print("=" * 78)

    # Acceptance Invariants
    assert fsr == 0.0, f"False Substitution Rate must strictly be 0.00%, got {fsr:.2f}%"
    assert accuracy >= 95.0, f"Scale Benchmark Accuracy must be >= 95.0%, got {accuracy:.2f}% ({passed}/{total})"
    assert p50_latency < 0.5, f"Scale latency p50 must be < 0.5 ms, got {p50_latency:.4f} ms"
    assert p95_latency < 2.0, f"Scale latency p95 must be < 2.0 ms, got {p95_latency:.4f} ms"


@pytest.mark.parametrize("case", SCALE_CASES, ids=[c["id"] for c in SCALE_CASES])
def test_individual_scale_case(case: dict[str, Any], engine: SemanticResolutionEngine) -> None:
    """Verifies each scale query independently for fine-grained pytest reporting."""
    result = evaluate_single_scale_case(case, engine)
    assert result["passed"], (
        f"Case {case['id']} FAILED ({case['area']}): Query='{case['query']}'. "
        f"Expected status={case['expected_status']}, indicator={case.get('expected_indicator_id') or case.get('expected_indicator_ids')}. "
        f"Got status={result['actual_status']}, candidate={result['actual_candidate']}, "
        f"reason={result['actual_reason']}. "
        f"Forbidden violation: {result['forbidden_violation']}, False swap: {result['is_false_swap']}"
    )
