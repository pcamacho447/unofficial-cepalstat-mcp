"""Tests for the CEPALSTAT Semantic Intent Disambiguation Engine and Benchmark."""

from pathlib import Path
import pytest
from statscepal.semantic import (
    BenchmarkEvaluator,
    QueryParser,
    RelationshipType,
    ResolutionStatus,
    SemanticRegistry,
    SemanticResolutionEngine,
    TemporalAvailabilityStatus,
)


@pytest.fixture
def benchmark_file() -> Path:
    return Path(__file__).parent / "benchmark" / "semantic_benchmark_cases.json"


@pytest.fixture
def engine() -> SemanticResolutionEngine:
    return SemanticResolutionEngine()


def test_benchmark_file_exists_and_loads(benchmark_file: Path):
    evaluator = BenchmarkEvaluator(cases_path=benchmark_file)
    cases = evaluator.load_cases()
    assert len(cases) == 50
    assert cases[0].case_id == "POV-01"


def test_parser_extracts_regionalisms():
    parser = QueryParser()
    intent = parser.parse("Pobreza de las pibas en el campo en Brasil 2021")
    assert intent.root_concept == "POBREZA"
    assert intent.country_code == "BRA"
    assert intent.year == 2021
    assert intent.facets.get("sexo") == "FEMENINO"
    assert intent.facets.get("area") == "RURAL"


def test_direct_canonical_resolution(engine: SemanticResolutionEngine):
    res = engine.resolve("Pobreza total en Brasil en 2021")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 3328
    assert res.selected_candidate.swapped_from is None
    assert res.temporal_info is not None
    assert res.temporal_info.temporal_status == TemporalAvailabilityStatus.OBSERVATION_EXISTING


def test_facet_driven_swap_with_breakdown_of(engine: SemanticResolutionEngine):
    res = engine.resolve("¿Cuál fue la pobreza de las mujeres jóvenes rurales en Brasil en 2021?")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 3341
    assert res.selected_candidate.swapped_from == 3328
    assert res.selected_candidate.swap_relationship == RelationshipType.BREAKDOWN_OF
    assert res.applied_filters.facets.get("sexo") == "FEMENINO"
    assert res.applied_filters.facets.get("edad") == "JUVENTUD"
    assert res.applied_filters.facets.get("area") == "RURAL"


def test_ambiguous_measure_proposal(engine: SemanticResolutionEngine):
    res = engine.resolve("Pobreza femenina en Brasil")
    assert res.status == ResolutionStatus.ALTERNATIVE_PROPOSED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 3341
    assert len(res.alternatives) == 1
    assert res.alternatives[0].indicator_id == 3330
    assert res.alternatives[0].relationship == RelationshipType.ALTERNATIVE_MEASURE


def test_temporal_unobserved_period_with_anchors(engine: SemanticResolutionEngine):
    res = engine.resolve("Tasa de pobreza de Chile en 2021")
    assert res.status == ResolutionStatus.RESOLVED_WITH_ANCHORS
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 3328
    assert res.temporal_info is not None
    assert res.temporal_info.temporal_status == TemporalAvailabilityStatus.PERIOD_UNOBSERVED
    assert res.temporal_info.previous_anchor_year == 2020
    assert res.temporal_info.next_anchor_year == 2022
    assert res.temporal_info.forbid_interpolation is True
    assert "CASEN" in res.temporal_info.disclaimer or "no se realizó" in res.temporal_info.disclaimer


def test_justified_abstention_unsupported_facet(engine: SemanticResolutionEngine):
    res = engine.resolve("Pobreza monetaria informal por quintiles en Uruguay")
    assert res.status == ResolutionStatus.ABSTAINED
    assert res.abstention_reason == "FORMALIDAD_LABORAL"
    assert res.unsupported_facet == "FORMALIDAD_LABORAL"


def test_full_benchmark_suite_execution(benchmark_file: Path):
    evaluator = BenchmarkEvaluator(cases_path=benchmark_file)
    report = evaluator.evaluate()

    # Asserting the 7 Statistical Correctness Thresholds
    assert report.total_cases == 50
    assert report.passed_cases == 50, f"Failed cases: {[d.case_id for d in report.details if not d.passed]}"
    assert report.top1_accuracy_pct == 100.0
    assert report.recall_at_3_pct == 100.0
    assert report.false_substitution_rate_pct == 0.0  # Zero false swaps
    assert report.facet_precision_pct == 100.0
    assert report.temporal_status_accuracy_pct == 100.0
    assert report.justified_abstention_rate_pct == 100.0
    assert report.p50_latency_ms < 2.0
