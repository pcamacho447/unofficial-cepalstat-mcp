"""Data models for the CEPALSTAT Semantic Intent Disambiguation Engine."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ResolutionStatus(str, Enum):
    """Overall status of the semantic resolution."""

    RESOLVED = "RESOLVED"
    RESOLVED_WITH_ANCHORS = "RESOLVED_WITH_ANCHORS"
    ALTERNATIVE_PROPOSED = "ALTERNATIVE_PROPOSED"
    ABSTAINED = "ABSTAINED"


class TemporalAvailabilityStatus(str, Enum):
    """The 4 formal empirical states of temporal availability."""

    OBSERVATION_EXISTING = "OBSERVATION_EXISTING"
    OBSERVATION_MISSING = "OBSERVATION_MISSING"
    PERIOD_UNOBSERVED = "PERIOD_UNOBSERVED"
    PENDING_UPDATE = "PENDING_UPDATE"


class RelationshipType(str, Enum):
    """Typed relationship between indicators in the knowledge graph."""

    BREAKDOWN_OF = "breakdown_of"
    HARMONIZED_VERSION_OF = "harmonized_version_of"
    ALTERNATIVE_MEASURE = "alternative_measure"
    RELATED_CONCEPT = "related_concept"
    METHODOLOGICALLY_INCOMPARABLE = "methodologically_incomparable"


class SemanticQueryRequest(BaseModel):
    """User input request for semantic indicator resolution."""

    query: str
    preferred_source: str = "armonizada_cepal"
    allow_swaps: bool = True


class AppliedDimensionFilter(BaseModel):
    """A resolved dimension and member filter for an indicator."""

    dim_id: int | None = None
    dim_name: str
    member_id: int | None = None
    member_name: str


class AppliedFilters(BaseModel):
    """Filters resolved for the execution."""

    country_code: str | None = None
    country_name: str | None = None
    year: int | None = None
    facets: dict[str, str] = Field(default_factory=dict)
    dimensions: list[AppliedDimensionFilter] = Field(default_factory=list)


class TemporalAnchorInfo(BaseModel):
    """Contextual anchor years for unobserved periods."""

    requested_year: int
    temporal_status: TemporalAvailabilityStatus
    previous_anchor_year: int | None = None
    previous_anchor_value: float | None = None
    next_anchor_year: int | None = None
    next_anchor_value: float | None = None
    disclaimer: str = ""
    forbid_interpolation: bool = True


class AlternativeCandidate(BaseModel):
    """Alternative indicator proposed when ambiguity or complementary measures exist."""

    indicator_id: int
    name: str
    relationship: RelationshipType
    note: str = ""


class SelectedCandidate(BaseModel):
    """The winning or primary indicator candidate."""

    indicator_id: int
    name: str
    measure_type: str = "INCIDENCIA"
    unit: str = "%"
    relevance_score: float = 1.0
    swapped_from: int | None = None
    swap_relationship: RelationshipType | None = None
    selection_reason: str = ""


class SemanticResolutionResponse(BaseModel):
    """Complete, traceable resolution response from the semantic engine."""

    status: ResolutionStatus
    query: str
    selected_candidate: SelectedCandidate | None = None
    applied_filters: AppliedFilters = Field(default_factory=AppliedFilters)
    temporal_info: TemporalAnchorInfo | None = None
    alternatives: list[AlternativeCandidate] = Field(default_factory=list)
    abstention_reason: str | None = None
    unsupported_facet: str | None = None
    conversational_hint: str | None = None
    empirical_data: dict[str, Any] | None = Field(default=None, description="Observation payload fetched from CEPALSTAT")
    execution_trace: list[str] = Field(default_factory=list, description="Step-by-step reasoning trace")
    latency_ms: float = 0.0


class BenchmarkCase(BaseModel):
    """A ground truth test case for the semantic benchmark."""

    case_id: str
    query: str
    category: str
    expected_status: ResolutionStatus
    expected_indicator_id: int | None = None
    expected_measure: str | None = None
    required_country: str | None = None
    required_year: int | None = None
    required_facets: dict[str, str] = Field(default_factory=dict)
    swapped_from: int | None = None
    relationship_used: str | None = None
    competing_indicator_id: int | None = None
    competing_relationship: str | None = None
    allow_swap: bool = True
    must_include_suggestion: bool = False
    suggestion_contains: str | None = None
    temporal_check: dict[str, Any] = Field(default_factory=dict)
    forbid_interpolation: bool = False
    abstention_reason: str | None = None
    unsupported_facet: str | None = None
    must_ask_clarification: bool = False


class BenchmarkResult(BaseModel):
    """Evaluation result for a single benchmark test case."""

    case_id: str
    passed: bool
    status_match: bool
    indicator_match: bool
    swap_valid: bool
    facet_match: bool
    temporal_match: bool
    abstention_match: bool
    latency_ms: float
    error_message: str | None = None


class BenchmarkMetricsReport(BaseModel):
    """Aggregated report of benchmark evaluation metrics."""

    total_cases: int
    passed_cases: int
    top1_accuracy_pct: float
    recall_at_3_pct: float
    false_substitution_rate_pct: float
    facet_precision_pct: float
    temporal_status_accuracy_pct: float
    justified_abstention_rate_pct: float
    p50_latency_ms: float
    p95_latency_ms: float
    details: list[BenchmarkResult] = Field(default_factory=list)
