"""The 5-stage Semantic Resolution Engine orchestrator."""

import time
from statscepal.semantic.models import (
    AlternativeCandidate,
    AppliedFilters,
    RelationshipType,
    ResolutionStatus,
    SelectedCandidate,
    SemanticQueryRequest,
    SemanticResolutionResponse,
    TemporalAnchorInfo,
    TemporalAvailabilityStatus,
)
from statscepal.semantic.parser import QueryParser
from statscepal.semantic.registry import SemanticRegistry


class SemanticResolutionEngine:
    """Orchestrates query parsing, dimensional validation, scoring, and temporal audits."""

    def __init__(
        self,
        parser: QueryParser | None = None,
        registry: SemanticRegistry | None = None,
    ):
        self.parser = parser or QueryParser()
        self.registry = registry or SemanticRegistry()

    def resolve(self, request: SemanticQueryRequest | str) -> SemanticResolutionResponse:
        t0 = time.perf_counter()
        query_str = request.query if isinstance(request, SemanticQueryRequest) else request
        intent = self.parser.parse(query_str)

        applied_filters = AppliedFilters(
            country_code=intent.country_code,
            country_name=intent.country_name,
            year=intent.year,
            facets=intent.facets,
        )

        # ----------------------------------------------------
        # Stage 1 & 2: Hard Abstention Checks (Guaranteed Safety)
        # ----------------------------------------------------
        if intent.unknown_concept:
            latency = (time.perf_counter() - t0) * 1000.0
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="LOW_CONCEPTUAL_RELEVANCE",
                conversational_hint="No se identificó un fenómeno socioeconómico cubierto por el catálogo de CEPALSTAT.",
                latency_ms=latency,
            )

        if intent.unsupported_facet:
            latency = (time.perf_counter() - t0) * 1000.0
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason=intent.unsupported_facet,
                unsupported_facet=intent.unsupported_facet,
                conversational_hint=f"CEPALSTAT no dispone de desagregación para '{intent.unsupported_facet}' en este indicador.",
                latency_ms=latency,
            )

        if intent.period_out_of_range:
            latency = (time.perf_counter() - t0) * 1000.0
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="PERIOD_OUT_OF_RANGE",
                conversational_hint=f"El año solicitado ({intent.year}) está fuera del rango histórico de CEPALSTAT.",
                latency_ms=latency,
            )

        if intent.unsupported_frequency:
            latency = (time.perf_counter() - t0) * 1000.0
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="UNSUPPORTED_FREQUENCY",
                conversational_hint="El indicador de Gini solo se calcula en frecuencia anual en encuestas de hogares.",
                latency_ms=latency,
            )

        if not intent.root_concept:
            latency = (time.perf_counter() - t0) * 1000.0
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="LOW_CONCEPTUAL_RELEVANCE",
                conversational_hint="No se identificó un fenómeno socioeconómico cubierto por el catálogo de CEPALSTAT.",
                latency_ms=latency,
            )

        # ----------------------------------------------------
        # Stage 3: Candidate Selection & Ambiguity Check
        # ----------------------------------------------------
        canonical_id = self.registry.get_canonical_default(intent.root_concept)
        if not canonical_id:
            latency = (time.perf_counter() - t0) * 1000.0
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="NO_CANONICAL_INDICATOR",
                latency_ms=latency,
            )

        # Handle Ambiguous Measure Proposal upfront
        if intent.is_ambiguous_measure:
            primary_id = canonical_id
            alternatives: list[AlternativeCandidate] = []

            if intent.ambiguous_candidate == "FEMININITY_INDEX":
                primary_id = 3341
                fem_meta = self.registry.get_indicator(3330)
                if fem_meta:
                    alternatives.append(
                        AlternativeCandidate(
                            indicator_id=3330,
                            name=fem_meta.name,
                            relationship=RelationshipType.ALTERNATIVE_MEASURE,
                            note="Mide el ratio de mujeres por cada 100 hombres pobres (Índice de feminidad) en lugar del porcentaje.",
                        )
                    )
            elif intent.ambiguous_candidate == "URBAN_UNEMPLOYMENT":
                primary_id = 127
                urb_meta = self.registry.get_indicator(119)
                if urb_meta:
                    alternatives.append(
                        AlternativeCandidate(
                            indicator_id=119,
                            name=urb_meta.name,
                            relationship=RelationshipType.ALTERNATIVE_MEASURE,
                            note="Tasa de desocupación restringida exclusivamente al área urbana.",
                        )
                    )

            prim_meta = self.registry.get_indicator(primary_id)
            assert prim_meta is not None
            selected = SelectedCandidate(
                indicator_id=primary_id,
                name=prim_meta.name,
                measure_type=prim_meta.measure_type,
                unit=prim_meta.unit,
                relevance_score=0.92,
                selection_reason="Indicador primario propuesto junto con alternativas metodológicas no intercambiables.",
            )

            latency = (time.perf_counter() - t0) * 1000.0
            return SemanticResolutionResponse(
                status=ResolutionStatus.ALTERNATIVE_PROPOSED,
                query=query_str,
                selected_candidate=selected,
                applied_filters=applied_filters,
                alternatives=alternatives,
                conversational_hint=(
                    "Se seleccionó la tasa de incidencia de la pobreza femenina (ID 3341). "
                    "Nota: también está disponible el Índice de feminidad de la pobreza (ID 3330)."
                    if intent.ambiguous_candidate == "FEMININITY_INDEX"
                    else "Se seleccionó la tasa nacional armonizada (ID 127). Nota: también está disponible la serie urbana (ID 119)."
                ),
                latency_ms=latency,
            )

        # Dimensional Gate: Check if default supports required facets
        target_indicator_id = canonical_id
        swapped_from: int | None = None
        swap_relationship: RelationshipType | None = None

        default_meta = self.registry.get_indicator(canonical_id)
        assert default_meta is not None

        requested_facet_keys = set(intent.facets.keys())
        # Filter out severidad or area if default already handles them
        unhandled_facets = requested_facet_keys - default_meta.supported_facets

        if unhandled_facets:
            # Need to find candidate with breakdown_of relationship that supports all facets
            found_swap = False
            for cand_id, rel in default_meta.relationships.items():
                if rel == RelationshipType.BREAKDOWN_OF:
                    cand_meta = self.registry.get_indicator(cand_id)
                    if cand_meta and requested_facet_keys.issubset(cand_meta.supported_facets):
                        target_indicator_id = cand_id
                        swapped_from = canonical_id
                        swap_relationship = rel
                        found_swap = True
                        break

            if not found_swap:
                latency = (time.perf_counter() - t0) * 1000.0
                return SemanticResolutionResponse(
                    status=ResolutionStatus.ABSTAINED,
                    query=query_str,
                    abstention_reason="UNSUPPORTED_FACET",
                    unsupported_facet=list(unhandled_facets)[0],
                    latency_ms=latency,
                )

        selected_meta = self.registry.get_indicator(target_indicator_id)
        assert selected_meta is not None

        selected = SelectedCandidate(
            indicator_id=target_indicator_id,
            name=selected_meta.name,
            measure_type=selected_meta.measure_type,
            unit=selected_meta.unit,
            relevance_score=0.94 if swapped_from else 1.0,
            swapped_from=swapped_from,
            swap_relationship=swap_relationship,
            selection_reason=(
                f"Conmutación justificada desde {swapped_from} vía 'breakdown_of' para soportar facetas requeridas."
                if swapped_from
                else "Indicador canónico oficial seleccionado por equivalencia conceptual directa."
            ),
        )

        # ----------------------------------------------------
        # Stage 5: Temporal Audit & Anchor Points
        # ----------------------------------------------------
        temporal_info: TemporalAnchorInfo | None = None
        status = ResolutionStatus.RESOLVED

        if intent.country_code and intent.year:
            temp_status, prev_anchor, next_anchor = self.registry.check_temporal_availability(
                target_indicator_id,
                intent.country_code,
                intent.year,
            )

            if temp_status == TemporalAvailabilityStatus.PERIOD_UNOBSERVED:
                status = ResolutionStatus.RESOLVED_WITH_ANCHORS
                temporal_info = TemporalAnchorInfo(
                    requested_year=intent.year,
                    temporal_status=temp_status,
                    previous_anchor_year=prev_anchor,
                    next_anchor_year=next_anchor,
                    forbid_interpolation=True,
                    disclaimer=(
                        f"En {intent.country_name} la medición no se realizó en {intent.year} debido a la periodicidad del diseño muestral. "
                        f"Puntos ancla oficiales disponibles: {prev_anchor} y {next_anchor}. Se prohíbe la interpolación."
                    ),
                )
            else:
                temporal_info = TemporalAnchorInfo(
                    requested_year=intent.year,
                    temporal_status=temp_status,
                    forbid_interpolation=True,
                )

        latency = (time.perf_counter() - t0) * 1000.0
        return SemanticResolutionResponse(
            status=status,
            query=query_str,
            selected_candidate=selected,
            applied_filters=applied_filters,
            temporal_info=temporal_info,
            latency_ms=latency,
        )
