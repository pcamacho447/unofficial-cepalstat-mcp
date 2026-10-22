"""Benchmark runner and statistical metrics calculator for semantic resolution."""

import json
import statistics
import time
from pathlib import Path

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import (
    BenchmarkCase,
    BenchmarkMetricsReport,
    BenchmarkResult,
    RelationshipType,
    ResolutionStatus,
)


class BenchmarkEvaluator:
    """Evaluates the semantic engine against the benchmark dataset and calculates metrics."""

    def __init__(
        self,
        engine: SemanticResolutionEngine | None = None,
        cases_path: Path | str | None = None,
    ):
        if cases_path:
            self.cases_path = Path(cases_path)
        else:
            self.cases_path = (
                Path(__file__).parent.parent.parent.parent
                / "tests"
                / "benchmark"
                / "semantic_benchmark_cases.json"
            )
        is_legacy = "semantic_benchmark_cases_200.json" not in str(self.cases_path)
        profile = "legacy_50" if is_legacy else "official_25"
        self.engine = engine or SemanticResolutionEngine(catalog_profile=profile)

    def load_cases(self) -> list[BenchmarkCase]:
        if not self.cases_path.exists():
            raise FileNotFoundError(f"Benchmark file not found: {self.cases_path}")
        with open(self.cases_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_cases = data if isinstance(data, list) else data.get("cases", [])
        return [BenchmarkCase.model_validate(c) for c in raw_cases]

    def evaluate(self) -> BenchmarkMetricsReport:
        cases = self.load_cases()
        results: list[BenchmarkResult] = []
        latencies: list[float] = []

        top1_hits = 0
        recall3_hits = 0
        resolvable_cases = 0
        false_swaps = 0
        total_swaps = 0
        facet_hits = 0
        total_facets = 0
        temporal_hits = 0
        total_temporal = 0
        justified_abstentions = 0
        total_abstention_cases = 0

        for case in cases:
            t0 = time.perf_counter()
            response = self.engine.resolve(case.query)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(latency_ms)

            status_match = response.status == case.expected_status

            # Indicator Match
            indicator_match = True
            if case.expected_indicator_id:
                indicator_match = (
                    response.selected_candidate is not None
                    and response.selected_candidate.indicator_id == case.expected_indicator_id
                )

            # Swap Validity
            swap_valid = True
            if case.swapped_from:
                total_swaps += 1
                if (
                    response.selected_candidate is None
                    or response.selected_candidate.swapped_from != case.swapped_from
                    or response.selected_candidate.swap_relationship != RelationshipType.BREAKDOWN_OF
                ):
                    swap_valid = False
                    false_swaps += 1
            elif not case.allow_swap and response.selected_candidate and response.selected_candidate.swapped_from:
                swap_valid = False
                false_swaps += 1

            # Facet Match
            facet_match = True
            if case.required_facets:
                total_facets += len(case.required_facets)
                for f_k, f_v in case.required_facets.items():
                    if response.applied_filters.facets.get(f_k) == f_v:
                        facet_hits += 1
                    else:
                        facet_match = False

            # Temporal Match
            temporal_match = True
            if case.temporal_check:
                total_temporal += 1
                expected_temp_status = case.temporal_check.get("expected_status")
                if response.temporal_info is None or response.temporal_info.temporal_status.value != expected_temp_status:
                    temporal_match = False
                else:
                    if "expected_previous_anchor" in case.temporal_check:
                        if response.temporal_info.previous_anchor_year != case.temporal_check["expected_previous_anchor"]:
                            temporal_match = False
                    if "expected_next_anchor" in case.temporal_check:
                        if response.temporal_info.next_anchor_year != case.temporal_check["expected_next_anchor"]:
                            temporal_match = False
                if temporal_match:
                    temporal_hits += 1

            # Alternatives Match
            alt_match = True
            if case.expected_alternatives:
                exp_alts = set(case.expected_alternatives)
                act_alts = {alt.indicator_id for alt in response.alternatives}
                if not exp_alts.issubset(act_alts):
                    alt_match = False

            # Abstention Match
            abstention_match = True
            if case.expected_status == ResolutionStatus.ABSTAINED:
                total_abstention_cases += 1
                if response.status == ResolutionStatus.ABSTAINED:
                    valid_reasons = {
                        case.abstention_reason,
                        case.expected_reason,
                        case.unsupported_facet,
                        "UNSUPPORTED_FACET",
                        "LOW_CONCEPTUAL_RELEVANCE",
                        "PERIOD_OUT_OF_RANGE",
                        "UNSUPPORTED_FREQUENCY",
                        "UNRESOLVED_SPECIFICITY",
                    } - {None}
                    if case.abstention_reason and response.abstention_reason not in valid_reasons:
                        abstention_match = False
                    else:
                        justified_abstentions += 1
                else:
                    abstention_match = False

            # Scoring Top-1 & Recall@3
            if case.expected_status in [
                ResolutionStatus.RESOLVED,
                ResolutionStatus.RESOLVED_WITH_ANCHORS,
                ResolutionStatus.ALTERNATIVE_PROPOSED,
            ]:
                resolvable_cases += 1
                if indicator_match:
                    top1_hits += 1
                    recall3_hits += 1
                elif case.competing_indicator_id and any(
                    alt.indicator_id == case.competing_indicator_id for alt in response.alternatives
                ):
                    recall3_hits += 1

            passed = (
                status_match
                and indicator_match
                and swap_valid
                and facet_match
                and temporal_match
                and abstention_match
                and alt_match
            )

            error_msg = None
            if not passed:
                error_msg = (
                    f"Mismatch in case {case.case_id}: status={response.status} (exp={case.expected_status}), "
                    f"indicator={response.selected_candidate.indicator_id if response.selected_candidate else None} "
                    f"(exp={case.expected_indicator_id})"
                )

            results.append(
                BenchmarkResult(
                    case_id=case.case_id,
                    passed=passed,
                    status_match=status_match,
                    indicator_match=indicator_match,
                    swap_valid=swap_valid,
                    facet_match=facet_match,
                    temporal_match=temporal_match,
                    abstention_match=abstention_match,
                    latency_ms=latency_ms,
                    error_message=error_msg,
                )
            )

        passed_count = sum(1 for r in results if r.passed)
        top1_acc = (top1_hits / resolvable_cases * 100.0) if resolvable_cases else 100.0
        recall3 = (recall3_hits / resolvable_cases * 100.0) if resolvable_cases else 100.0
        false_swap_rate = (false_swaps / total_swaps * 100.0) if total_swaps else 0.0
        facet_prec = (facet_hits / total_facets * 100.0) if total_facets else 100.0
        temporal_acc = (temporal_hits / total_temporal * 100.0) if total_temporal else 100.0
        abstention_rate = (
            (justified_abstentions / total_abstention_cases * 100.0)
            if total_abstention_cases
            else 100.0
        )

        p50 = statistics.median(latencies) if latencies else 0.0
        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

        return BenchmarkMetricsReport(
            total_cases=len(cases),
            passed_cases=passed_count,
            top1_accuracy_pct=round(top1_acc, 2),
            recall_at_3_pct=round(recall3, 2),
            false_substitution_rate_pct=round(false_swap_rate, 2),
            facet_precision_pct=round(facet_prec, 2),
            temporal_status_accuracy_pct=round(temporal_acc, 2),
            justified_abstention_rate_pct=round(abstention_rate, 2),
            p50_latency_ms=round(p50, 3),
            p95_latency_ms=round(p95, 3),
            details=results,
        )
