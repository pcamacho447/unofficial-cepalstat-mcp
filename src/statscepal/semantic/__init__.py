"""CEPALSTAT Semantic Intent Disambiguation Engine and Statistical Validator."""

from statscepal.semantic.engine import SemanticResolutionEngine
from statscepal.semantic.evaluator import BenchmarkEvaluator
from statscepal.semantic.models import (
    AlternativeCandidate,
    AppliedFilters,
    BenchmarkCase,
    BenchmarkMetricsReport,
    BenchmarkResult,
    MeasureType,
    RelationshipType,
    ResolutionStatus,
    SelectedCandidate,
    SemanticQueryRequest,
    SemanticResolutionResponse,
    TemporalAnchorInfo,
    TemporalAvailabilityStatus,
)
from statscepal.semantic.fetcher import SemanticDataFetcher
from statscepal.semantic.matcher import DynamicMemberMatcher
from statscepal.semantic.parser import QueryParser
from statscepal.semantic.registry import SemanticRegistry
from statscepal.semantic.thesaurus import (
    AntonymRule,
    ExpectedSign,
    PolarityResolution,
    PolarityType,
    Synset,
    SynsetMatch,
    Thesaurus,
)

__all__ = [
    "AlternativeCandidate",
    "AntonymRule",
    "AppliedFilters",
    "BenchmarkCase",
    "BenchmarkEvaluator",
    "BenchmarkMetricsReport",
    "BenchmarkResult",
    "DynamicMemberMatcher",
    "ExpectedSign",
    "MeasureType",
    "PolarityResolution",
    "PolarityType",
    "QueryParser",
    "RelationshipType",
    "ResolutionStatus",
    "SelectedCandidate",
    "SemanticDataFetcher",
    "SemanticQueryRequest",
    "SemanticRegistry",
    "SemanticResolutionEngine",
    "SemanticResolutionResponse",
    "Synset",
    "SynsetMatch",
    "TemporalAnchorInfo",
    "TemporalAvailabilityStatus",
    "Thesaurus",
]
