"""Automated independent hold-out benchmark evaluation suite for 50 queries across 23 domains.

Evaluates semantic resolution on 50 independently formulated queries:
- 35 positive queries across all 23 CEPALSTAT areas
- 15 adversarial traps (geographical non-LAC, high-frequency tickers, pseudoscientific, measure specificity)
"""

import json
import statistics
import time
from pathlib import Path

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus


def test_independent_holdout_benchmark_50() -> None:
    path = Path(__file__).parent / "benchmark" / "independent_holdout_benchmark_50.json"
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) == 50, f"Expected exactly 50 hold-out cases, got {len(cases)}"
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")

    # Warm-up pass to hydrate token indexes and caches
    for item in cases:
        engine.resolve(item["query"])

    passed_count = 0
    false_substitutions = 0
    latencies: list[float] = []

    for item in cases:
        t0 = time.perf_counter()
        resp = engine.resolve(item["query"])
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        exp_status = item["expected_status"]
        status_ok = resp.status.value == exp_status

        # FSR Check: if ABSTAINED was expected, returning RESOLVED is a false substitution
        if exp_status == "ABSTAINED" and resp.status == ResolutionStatus.RESOLVED:
            false_substitutions += 1

        # Check forbidden indicator
        if item.get("forbidden_indicator_id") and resp.selected_candidate:
            if resp.selected_candidate.indicator_id == item["forbidden_indicator_id"]:
                false_substitutions += 1
                status_ok = False

        # Indicator match for positive queries
        ind_ok = True
        if exp_status == "RESOLVED" and item.get("expected_indicator_id"):
            actual_id = resp.selected_candidate.indicator_id if resp.selected_candidate else None
            expected_ids = item.get("allowed_indicator_ids") or [item["expected_indicator_id"]]
            ind_ok = actual_id in expected_ids

        # Reason match for abstentions if specified
        reason_ok = True
        if exp_status == "ABSTAINED" and item.get("expected_reason"):
            actual_reason = str(resp.abstention_reason or "")
            reason_ok = item["expected_reason"] in actual_reason

        if status_ok and ind_ok and reason_ok:
            passed_count += 1
        else:
            cand = resp.selected_candidate.indicator_id if resp.selected_candidate else None
            print(
                f"FAILED: {item['id']} | Query: '{item['query']}' | "
                f"Expected: {exp_status} (ind={item.get('expected_indicator_id')}) | "
                f"Got: {resp.status.value} (cand={cand}, reason={resp.abstention_reason})"
            )

    accuracy = passed_count / len(cases)
    p50_ms = statistics.median(latencies)
    fsr = false_substitutions / len(cases)

    print("\n" + "=" * 70)
    print("INDEPENDENT 50-CASE HOLDOUT BENCHMARK REPORT (23 DOMAINS)")
    print("=" * 70)
    print(f"Total Cases:                   {len(cases)}")
    print(f"Passed Cases:                  {passed_count}/{len(cases)} ({accuracy:.1%})")
    print(f"False Substitutions (FSR):     {false_substitutions} ({fsr:.2%})")
    print(f"Latency p50:                   {p50_ms:.3f} ms")
    print("=" * 70)

    assert fsr == 0.0, f"False Substitution Rate must be 0.00%, got {fsr:.2%} ({false_substitutions} violations)"
    assert accuracy >= 0.95, f"Hold-out accuracy must be >= 95.0%, got {accuracy:.1%} ({passed_count}/50)"
    assert p50_ms < 0.5, f"p50 latency must be < 0.5 ms, got {p50_ms:.3f} ms"
