"""The 5-stage Semantic Resolution Engine orchestrator."""

import time
from typing import Any
from statscepal.semantic.models import (
    AlternativeCandidate,
    AppliedFilters,
    CountryTemporalAnchor,
    RelationshipType,
    ResolutionStatus,
    SelectedCandidate,
    SemanticQueryRequest,
    SemanticResolutionResponse,
    TemporalAnchorInfo,
    TemporalAvailabilityStatus,
)
from statscepal.dimensions import Dimension
from statscepal.semantic.facet_ontology import (
    DEFAULT_FACET_ONTOLOGY,
    FacetOntology,
    strip_accents,
)
from statscepal.semantic.matcher import DynamicMemberMatcher
from statscepal.semantic.parser import QueryParser
from statscepal.semantic.registry import SemanticRegistry

CRITICAL_SPECIFICITY_TOKENS: frozenset[str] = frozenset({
    "manufacturero", "manufactura", "industrial", "industria",
    "agricola", "agricolas", "agropecuario", "agropecuaria",
    "minero", "minera", "mineria", "turismo", "comercial",
    "componente", "componentes", "gasto", "gastos",
    "cobre", "petroleo", "soja", "trigo", "cafe", "carne",
    "multidimensional", "organica", "boscosa", "cientificas",
    "corrupcion", "emigrar", "captura",
})

GENERAL_AGGREGATE_FALLBACKS: dict[int, set[str]] = {
    3337: {
        "agricola", "agricolas", "agropecuario", "agropecuaria",
        "industrial", "industria", "manufacturero", "manufactura",
        "minero", "minera",
    },
    128: {
        "agricola", "agricolas", "agropecuario", "agropecuaria",
        "industrial", "industria", "manufacturero", "manufactura",
        "minero", "minera",
    },
}


def _is_token_covered_by_indicator(
    token: str,
    indicator_meta: Any,
    dims: list[Dimension] | None,
) -> bool:
    """Check if token is covered by the indicator's name, concept, unit, or dimensions."""
    token_norm = strip_accents(token).lower().strip()
    if not token_norm:
        return True

    texts: list[str] = [indicator_meta.name, str(indicator_meta.concept)]
    if hasattr(indicator_meta, "unit") and indicator_meta.unit:
        texts.append(str(indicator_meta.unit))
    if hasattr(indicator_meta, "supported_facets") and indicator_meta.supported_facets:
        texts.extend(str(f) for f in indicator_meta.supported_facets)
    if dims:
        for d in dims:
            texts.append(str(d.name))
            if hasattr(d, "members") and d.members:
                for m in d.members:
                    texts.append(str(m.name))

    combined = strip_accents(" ".join(texts)).lower()

    if token_norm in combined:
        return True

    # Stem check for Spanish plurals / gender
    stem = token_norm
    if stem.endswith("es"):
        stem = stem[:-2]
    elif stem.endswith("s"):
        stem = stem[:-1]
    if len(stem) >= 4 and stem in combined:
        return True

    return False


class SemanticResolutionEngine:
    """Orchestrates query parsing, dimensional validation, scoring, and temporal audits."""

    def __init__(
        self,
        parser: QueryParser | None = None,
        registry: SemanticRegistry | None = None,
        matcher: DynamicMemberMatcher | None = None,
        catalog_profile: str = "official_25",
        ontology: FacetOntology | None = None,
    ):
        self.catalog_profile = catalog_profile
        self.ontology = ontology or DEFAULT_FACET_ONTOLOGY
        self.parser = parser or QueryParser(catalog_profile=catalog_profile, ontology=self.ontology)
        self.registry = registry or SemanticRegistry(catalog_profile=catalog_profile, ontology=self.ontology)
        self.matcher = matcher or DynamicMemberMatcher(ontology=self.ontology)

    @staticmethod
    def _route_population_indicator(facets: dict[str, str]) -> int:
        """Route demographic population queries to specialized breakdown indicators based on facets."""
        has_etnia = "etnia" in facets
        has_estrato = "estrato" in facets or "quintil" in facets
        area_val = facets.get("area")
        has_area = "area" in facets and area_val not in (None, "NACIONAL", "TOTAL", "AMBOS")

        # 1. Quintiles and ethnicity -> 4639 (highest specificity)
        if has_estrato and has_etnia:
            return 4639
        # 2. Specific ethnicity breakdowns:
        if facets.get("etnia") == "AFRODESCENDIENTE":
            return 4969
        if has_etnia:
            return 4968
        # 3. Area breakdown without ethnicity -> 4992
        if has_area:
            return 4992
        # 4. Canonical total population -> 4788
        return 4788

    def _has_dimension_for_facet(self, dims: list[Dimension], facet_key: str) -> bool:
        """Check whether any of the indicator's dimensions physically corresponds to facet_key."""
        facet_def = self.ontology.get_facet(facet_key)
        key_norm = strip_accents(facet_key)
        if facet_def and facet_def.dimension_name_patterns:
            key_patterns = list(facet_def.dimension_name_patterns)
        else:
            key_patterns = [key_norm]

        for d in dims:
            if self.ontology.classify_dimension(d.id, d.name) == facet_key:
                return True
            d_name_norm = strip_accents(d.name)
            if facet_def is not None:
                if d.id in facet_def.known_dimension_ids or any(kp in d_name_norm for kp in key_patterns):
                    return True
            else:
                if any(kp in d_name_norm for kp in key_patterns):
                    return True
        return False

    def resolve_query(self, query: str) -> SemanticResolutionResponse:
        """Resolve a natural language query string."""
        return self.resolve(query)

    def resolve(self, request: SemanticQueryRequest | str) -> SemanticResolutionResponse:
        t0 = time.perf_counter()
        query_str = request.query if isinstance(request, SemanticQueryRequest) else request
        intent = self.parser.parse(query_str)

        applied_filters = AppliedFilters(
            country_code=intent.country_code,
            country_name=intent.country_name,
            country_codes=list(intent.country_codes),
            country_names=list(intent.country_names),
            year=intent.year,
            years=intent.years,
            time_mode=intent.time_mode,
            relative_window_size=intent.relative_window_size,
            facets=intent.facets,
        )

        if intent.time_mode == "RANGE" and len(intent.years) > 1:
            time_trace_str = f"Years: {intent.years[0]}-{intent.years[-1]} ({intent.years}, Mode: RANGE)"
        elif intent.time_mode == "LIST" and len(intent.years) > 1:
            time_trace_str = f"Years: {intent.years} (Mode: LIST)"
        elif intent.time_mode == "RELATIVE_WINDOW" and intent.relative_window_size:
            time_trace_str = f"Window: últimos {intent.relative_window_size} años (Mode: RELATIVE_WINDOW)"
        else:
            time_trace_str = f"Year: {intent.year or 'N/A'}"

        if len(intent.country_codes) > 1:
            geo_trace_str = ", ".join(
                f"{n} ({c})" for n, c in zip(intent.country_names, intent.country_codes)
            )
        else:
            geo_trace_str = f"{intent.country_name or 'N/A'} ({intent.country_code or 'N/A'})"

        trace: list[str] = [
            f"[Stage 1: Intent Parsing] Query: '{query_str}'",
            f"  - Geography: {geo_trace_str}, {time_trace_str}, Freq: {getattr(intent, 'frequency', 'ANUAL')}",
            f"  - Root Concept: '{intent.root_concept or 'None'}'",
            f"  - Normalized Facets: {intent.facets if intent.facets else 'None'}",
        ]
        if intent.polarity_info:
            trace.append(
                f"  - Polarity: {intent.polarity_info.polarity_type.value} ('{intent.polarity_info.term_detected}', Expected Sign: {intent.polarity_info.expected_sign.value})"
            )

        # ----------------------------------------------------
        # Stage 1 & 2: Hard Abstention Checks (Guaranteed Safety)
        # ----------------------------------------------------
        if intent.unknown_concept:
            latency = (time.perf_counter() - t0) * 1000.0
            trace.append("[Stage 2: Hard Abstention] REJECTED: Phenomenon not in CEPALSTAT scope (LOW_CONCEPTUAL_RELEVANCE).")
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="LOW_CONCEPTUAL_RELEVANCE",
                conversational_hint="No se identificó un fenómeno socioeconómico cubierto por el catálogo de CEPALSTAT.",
                polarity_info=intent.polarity_info,
                execution_trace=trace,
                latency_ms=latency,
            )

        if intent.unsupported_facet:
            latency = (time.perf_counter() - t0) * 1000.0
            trace.append(f"[Stage 2: Hard Abstention] REJECTED: Facet '{intent.unsupported_facet}' not supported for this indicator.")
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason=intent.unsupported_facet,
                unsupported_facet=intent.unsupported_facet,
                conversational_hint=f"CEPALSTAT no dispone de desagregación para '{intent.unsupported_facet}' en este indicador.",
                polarity_info=intent.polarity_info,
                execution_trace=trace,
                latency_ms=latency,
            )

        if intent.period_out_of_range:
            latency = (time.perf_counter() - t0) * 1000.0
            trace.append(f"[Stage 2: Hard Abstention] REJECTED: Year {intent.year} out of historical range.")
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="PERIOD_OUT_OF_RANGE",
                conversational_hint=f"El año solicitado ({intent.year}) está fuera del rango histórico de CEPALSTAT.",
                polarity_info=intent.polarity_info,
                execution_trace=trace,
                latency_ms=latency,
            )

        if intent.unsupported_frequency:
            latency = (time.perf_counter() - t0) * 1000.0
            trace.append(f"[Stage 2: Hard Abstention] REJECTED: Requested frequency '{getattr(intent, 'frequency', 'UNSUPPORTED')}' not published for series.")
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="UNSUPPORTED_FREQUENCY",
                conversational_hint="La periodicidad solicitada no se encuentra disponible para esta serie oficial en CEPALSTAT.",
                polarity_info=intent.polarity_info,
                execution_trace=trace,
                latency_ms=latency,
            )

        if not intent.root_concept:
            latency = (time.perf_counter() - t0) * 1000.0
            trace.append("[Stage 2: Hard Abstention] REJECTED: No root concept recognized.")
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="LOW_CONCEPTUAL_RELEVANCE",
                conversational_hint="No se identificó un fenómeno socioeconómico cubierto por el catálogo de CEPALSTAT.",
                polarity_info=intent.polarity_info,
                execution_trace=trace,
                latency_ms=latency,
            )

        # ----------------------------------------------------
        # Stage 3: Candidate Selection & Ambiguity Check
        # ----------------------------------------------------
        canonical_id = self.registry.get_canonical_default(intent.root_concept)
        if not canonical_id:
            latency = (time.perf_counter() - t0) * 1000.0
            trace.append("[Stage 3: Candidate Selection] REJECTED: No canonical indicator for root concept.")
            return SemanticResolutionResponse(
                status=ResolutionStatus.ABSTAINED,
                query=query_str,
                abstention_reason="NO_CANONICAL_INDICATOR",
                polarity_info=intent.polarity_info,
                execution_trace=trace,
                latency_ms=latency,
            )

        if intent.root_concept == "POBLACION":
            canonical_id = self._route_population_indicator(intent.facets)

        trace.append(f"[Stage 2: Hard Abstention] PASSED: Root concept '{intent.root_concept}' recognized, facets valid.")
        trace.append(f"[Stage 3: Candidate Selection] Canonical indicator candidate: ID {canonical_id}")

        # Handle Ambiguous Measure Proposal upfront
        if intent.is_ambiguous_measure:
            primary_id = canonical_id
            alternatives: list[AlternativeCandidate] = []

            AMBIGUOUS_CONFIGS: dict[str, tuple[int, list[int], str]] = {
                "FEMININITY_INDEX": (3341, [3330], "Mide el ratio de mujeres por cada 100 hombres pobres (Índice de feminidad) en lugar del porcentaje."),
                "URBAN_UNEMPLOYMENT": (127, [119], "Tasa de desocupación restringida exclusivamente al área urbana."),
                "INCOME_MEASURES": (128, [3337, 3345], "Medida metodológica alternativa de ingreso o salario en CEPALSTAT."),
                "PRIVATION_GAP": (3328, [3329], "Brecha de pobreza y pobreza extrema en lugar de tasa de incidencia."),
                "INEQUALITY_INCOME": (3340, [3345], "Ingreso medio per cápita de los hogares como medida complementaria de bienestar."),
                "DISTRIBUTIVE_GAP": (3340, [3339], "Ingreso laboral medio de la población ocupada por sexo y área."),
                "LABOR_SITUATION": (127, [3331, 128], "Desempleo juvenil de 15 a 24 años e índice del salario medio real."),
                "UNEMPLOYMENT_AND_WAGES": (127, [128, 3337], "Índice del salario medio real y salario mínimo real."),
                "MACRO_ECONOMY": (729, [730, 731], "PIB per cápita y PIB trimestral a precios constantes."),
                "ECONOMIC_ACTIVITY": (729, [730, 731], "PIB per cápita y PIB trimestral a precios constantes."),
                "SECTORAL_INFLATION": (2928, [2929, 2930], "IPC de alimentos y bebidas e IPC de transporte y energía."),
                "GENERAL_PRICES": (2928, [2929, 2930], "IPC de alimentos y bebidas e IPC de transporte y energía."),
                "FISCAL_ACCOUNTS": (1240, [1241, 1242], "Balance primario e ingresos tributarios del gobierno central sobre el PIB."),
                "FISCAL_HEALTH": (1240, [1241, 1242], "Balance primario e ingresos tributarios del gobierno central sobre el PIB."),
                "EXTERNAL_SECTOR": (1243, [1244], "Términos de intercambio de bienes FOB/CIF."),
                "INTERNATIONAL_TRADE_PAYMENTS": (1243, [1244], "Términos de intercambio de bienes FOB/CIF."),
                "EMISSIONS_LULUCF_CHOICE": (5681, [5682], "Emisiones totales de GEI excluyendo sector UTCUTS / sin LULUCF."),
                "ENERGY_POLLUTION": (5681, [5683], "Participación de energías renovables en la generación eléctrica."),
                "SOCIOECONOMIC_WELLBEING": (3328, [3340, 128], "Distribución del ingreso por quintiles y salario medio real."),
                "MACRO_FISCAL_PANORAMA": (729, [1240, 1243], "Saldo de la deuda pública y saldo en cuenta corriente sobre el PIB."),
            }

            if intent.ambiguous_candidate in AMBIGUOUS_CONFIGS:
                primary_id, alt_ids, default_note = AMBIGUOUS_CONFIGS[intent.ambiguous_candidate]
                for alt_id in alt_ids:
                    alt_meta = self.registry.get_indicator(alt_id)
                    if alt_meta:
                        alternatives.append(
                            AlternativeCandidate(
                                indicator_id=alt_id,
                                name=alt_meta.name,
                                relationship=RelationshipType.ALTERNATIVE_MEASURE,
                                note=default_note,
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

            prim_dims = self.registry.get_dimensions(primary_id)
            if prim_dims and intent.facets:
                _, matched_dims, _ = self.matcher.match_facets_to_dimensions(
                    primary_id, prim_dims, intent.facets
                )
                applied_filters.dimensions = matched_dims

            trace.append(f"[Stage 3: Ambiguity Check] Ambiguous measure proposed: Primary ID {primary_id}, Alternatives={[a.indicator_id for a in alternatives]}")
            latency = (time.perf_counter() - t0) * 1000.0

            if intent.ambiguous_candidate == "FEMININITY_INDEX":
                conv_hint = (
                    "Se seleccionó la tasa de incidencia de la pobreza femenina (ID 3341). "
                    "Nota: también está disponible el Índice de feminidad de la pobreza (ID 3330)."
                )
            elif intent.ambiguous_candidate == "INCOME_MEASURES":
                conv_hint = (
                    "Consulta general sobre ingreso o salario sin especificación metodológica. "
                    "Se seleccionó el índice del salario medio real (ID 128). "
                    "Alternativas disponibles: Salario mínimo real (ID 3337) e Ingreso medio per cápita de los hogares (ID 3345)."
                )
            elif intent.ambiguous_candidate == "URBAN_UNEMPLOYMENT":
                conv_hint = (
                    "Se seleccionó la tasa nacional armonizada (ID 127). "
                    "Nota: también está disponible la serie urbana (ID 119)."
                )
            else:
                alt_summary = ", ".join(
                    f"{a.name} (ID {a.indicator_id})" for a in alternatives
                )
                conv_hint = (
                    f"Se seleccionó '{prim_meta.name}' (ID {primary_id}). "
                    f"Alternativas metodológicas disponibles: {alt_summary}."
                )

            return SemanticResolutionResponse(
                status=ResolutionStatus.ALTERNATIVE_PROPOSED,
                query=query_str,
                selected_candidate=selected,
                applied_filters=applied_filters,
                alternatives=alternatives,
                polarity_info=intent.polarity_info,
                conversational_hint=conv_hint,
                execution_trace=trace,
                latency_ms=latency,
            )

        # ----------------------------------------------------
        # Stage 4: Dimensional Gate & Knowledge Graph Conmutation
        # ----------------------------------------------------
        target_indicator_id = canonical_id
        swapped_from: int | None = None
        swap_relationship: RelationshipType | None = None

        default_meta = self.registry.get_indicator(canonical_id)
        assert default_meta is not None

        requested_facet_keys = set(intent.facets.keys())
        default_supported = self.registry.get_supported_facets(canonical_id)
        unhandled_facets: set[str] = {
            fk
            for fk, fv in intent.facets.items()
            if fk not in default_supported and self.ontology.is_critical_unhandled_facet(fk, fv)
        }

        default_dims = self.registry.get_dimensions(canonical_id)
        if default_dims and intent.facets:
            _, _, def_unhandled = self.matcher.match_facets_to_dimensions(
                canonical_id, default_dims, intent.facets
            )
            for fk in def_unhandled:
                if fk in default_supported and not self._has_dimension_for_facet(default_dims, fk):
                    continue
                if self.ontology.is_critical_unhandled_facet(fk, intent.facets.get(fk, "")):
                    unhandled_facets.add(fk)

        if unhandled_facets:
            trace.append(f"[Stage 4: Dimensional Gate] Canonical ID {canonical_id} lacks facets: {sorted(unhandled_facets)}. Traversing knowledge graph for 'breakdown_of' swap...")
            found_swap = False
            candidate_rels = self.registry.get_relationships(canonical_id)
            for cand_id, rel in candidate_rels.items():
                if rel == RelationshipType.BREAKDOWN_OF:
                    cand_meta = self.registry.get_indicator(cand_id)
                    if not cand_meta:
                        continue
                    cand_supported = self.registry.get_supported_facets(cand_id)
                    critical_requested = {
                        fk for fk, fv in intent.facets.items()
                        if self.ontology.is_critical_unhandled_facet(fk, fv)
                    }
                    if not unhandled_facets.issubset(cand_supported) or not critical_requested.issubset(cand_supported):
                        continue

                    cand_dims = self.registry.get_dimensions(cand_id)
                    if cand_dims:
                        cand_ok, _, cand_unhandled = self.matcher.match_facets_to_dimensions(
                            cand_id, cand_dims, intent.facets
                        )
                        crit_cand_unhandled = [
                            f for f in cand_unhandled
                            if not (f in cand_supported and not self._has_dimension_for_facet(cand_dims, f))
                            and self.ontology.is_critical_unhandled_facet(f, intent.facets.get(f, ""))
                        ]
                        if not crit_cand_unhandled:
                            target_indicator_id = cand_id
                            swapped_from = canonical_id
                            swap_relationship = rel
                            found_swap = True
                            trace.append(f"  - Swapped to ID {cand_id} ('{cand_meta.name}') via 'breakdown_of' (supports required facets)")
                            break
                    elif requested_facet_keys.issubset(cand_supported):
                        target_indicator_id = cand_id
                        swapped_from = canonical_id
                        swap_relationship = rel
                        found_swap = True
                        trace.append(f"  - Swapped to ID {cand_id} ('{cand_meta.name}') via 'breakdown_of' (supports required facets)")
                        break

            if not found_swap:
                latency = (time.perf_counter() - t0) * 1000.0
                unsupported_facet_name = sorted(unhandled_facets)[0]
                trace.append(f"  - REJECTED: No valid conmutation supports facet '{unsupported_facet_name}'.")
                return SemanticResolutionResponse(
                    status=ResolutionStatus.ABSTAINED,
                    query=query_str,
                    abstention_reason="UNSUPPORTED_FACET",
                    unsupported_facet=unsupported_facet_name,
                    polarity_info=intent.polarity_info,
                    execution_trace=trace,
                    latency_ms=latency,
                )

        selected_meta = self.registry.get_indicator(target_indicator_id)
        assert selected_meta is not None

        # Resolve dynamic dimensions and members for the chosen indicator
        target_dims = self.registry.get_dimensions(target_indicator_id)
        if target_dims and intent.facets:
            success, matched_dims, unhandled = self.matcher.match_facets_to_dimensions(
                target_indicator_id, target_dims, intent.facets
            )
            applied_filters.dimensions = matched_dims
            for f in matched_dims:
                if f.is_breakdown and f.member_names:
                    members_str = ", ".join(
                        f"{n} (ID: {i})" for n, i in zip(f.member_names, f.member_ids)
                    )
                    trace.append(
                        f"[Stage 4: Member Matcher] Bound dimension '{f.dim_name}' (ID: {f.dim_id}) -> Breakdown Members: [{members_str}]"
                    )
                else:
                    trace.append(
                        f"[Stage 4: Member Matcher] Bound dimension '{f.dim_name}' (ID: {f.dim_id}) -> Member '{f.member_name}' (ID: {f.member_id})"
                    )
                    f_facet = self.ontology.classify_dimension(f.dim_id, f.dim_name)
                    if (
                        f_facet
                        and f_facet in intent.facets
                        and self.ontology.is_critical_unhandled_facet(f_facet, intent.facets[f_facet])
                        and self.ontology.is_aggregate_member_name(f_facet, f.member_name)
                    ):
                        unhandled.append(f_facet)
            critical_unhandled = [
                f for f in unhandled
                if not (f in selected_meta.supported_facets and not self._has_dimension_for_facet(target_dims, f))
                and self.ontology.is_critical_unhandled_facet(f, intent.facets.get(f, ""))
            ]
            if critical_unhandled:
                latency = (time.perf_counter() - t0) * 1000.0
                trace.append(f"[Stage 4: Member Matcher] REJECTED: Unhandled facet '{critical_unhandled[0]}'")
                return SemanticResolutionResponse(
                    status=ResolutionStatus.ABSTAINED,
                    query=query_str,
                    abstention_reason="UNSUPPORTED_FACET",
                    unsupported_facet=critical_unhandled[0],
                    polarity_info=intent.polarity_info,
                    execution_trace=trace,
                    latency_ms=latency,
                )

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
        # Stage 3.5: Specificity Guard (Unconsumed Semantic Tokens Audit)
        # ----------------------------------------------------
        is_alternative_fallback = False
        conversational_hint: str | None = None

        if intent.unconsumed_tokens:
            uncovered_critical: list[str] = [
                tok
                for tok in intent.unconsumed_tokens
                if strip_accents(tok).lower() in CRITICAL_SPECIFICITY_TOKENS
                and not _is_token_covered_by_indicator(tok, selected_meta, target_dims)
            ]

            if uncovered_critical:
                uncovered_norms = {strip_accents(t).lower() for t in uncovered_critical}
                is_general_fallback = (
                    target_indicator_id in GENERAL_AGGREGATE_FALLBACKS
                    and uncovered_norms.issubset(GENERAL_AGGREGATE_FALLBACKS[target_indicator_id])
                )

                if is_general_fallback:
                    is_alternative_fallback = True
                    selected.relevance_score = 0.65
                    uncovered_str = ", ".join(uncovered_critical)
                    selected.selection_reason = (
                        f"El indicador {selected.indicator_id} cubre el concepto general ('{selected.name}'), "
                        f"pero no desagrega la especificidad solicitada: '{uncovered_str}'."
                    )
                    conversational_hint = (
                        f"Nota: Se propone como alternativa el indicador general {selected.indicator_id} ('{selected.name}'), "
                        f"pero la consulta solicitaba la especificidad: '{uncovered_str}'. "
                        f"Para el indicador sectorial consulte el catálogo de CEPALSTAT."
                    )
                    trace.append(
                        f"[Stage 3: Specificity Audit] DOWNGRADED to ALTERNATIVE_PROPOSED (Score: 0.65): Uncovered specificity: {uncovered_critical}."
                    )
                else:
                    latency = (time.perf_counter() - t0) * 1000.0
                    uncovered_str = ", ".join(uncovered_critical)
                    trace.append(
                        f"[Stage 3: Specificity Audit] REJECTED: Candidate ID {target_indicator_id} does not cover specificity: {uncovered_critical}. Status=ABSTAINED"
                    )
                    return SemanticResolutionResponse(
                        status=ResolutionStatus.ABSTAINED,
                        query=query_str,
                        applied_filters=applied_filters,
                        abstention_reason=f"UNRESOLVED_SPECIFICITY: {uncovered_str}",
                        conversational_hint=(
                            f"La consulta incluye especificidades temáticas no cubiertas por el indicador seleccionado ('{selected.name}'): "
                            f"{uncovered_str}. Se requiere un indicador sectorial especializado de CEPALSTAT."
                        ),
                        polarity_info=intent.polarity_info,
                        execution_trace=trace,
                        latency_ms=latency,
                    )

        # ----------------------------------------------------
        # Stage 5: Temporal Audit & Anchor Points
        # ----------------------------------------------------
        temporal_info: TemporalAnchorInfo | None = None
        status = ResolutionStatus.ALTERNATIVE_PROPOSED if is_alternative_fallback else ResolutionStatus.RESOLVED

        if len(intent.country_codes) > 1 and (intent.year or intent.years):
            target_years = list(intent.years) if intent.years else ([intent.year] if intent.year else [])
            observed_countries: list[str] = []
            unobserved_countries: list[str] = []
            observed_years_set: set[int] = set()
            unobserved_years_set: set[int] = set()
            country_anchors: dict[str, CountryTemporalAnchor] = {}
            country_name_map = dict(zip(intent.country_codes, intent.country_names))
            prev_anchor_first: int | None = None
            next_anchor_last: int | None = None

            for c_code in intent.country_codes:
                c_name = country_name_map.get(c_code, c_code)
                c_unobserved_years: list[int] = []
                c_prev: int | None = None
                c_next: int | None = None
                for y in target_years:
                    t_st, p_a, n_a = self.registry.check_temporal_availability(
                        target_indicator_id,
                        c_code,
                        y,
                    )
                    if t_st == TemporalAvailabilityStatus.OBSERVATION_EXISTING:
                        observed_years_set.add(y)
                    else:
                        c_unobserved_years.append(y)
                        unobserved_years_set.add(y)
                        if c_prev is None and p_a is not None:
                            c_prev = p_a
                        if n_a is not None:
                            c_next = n_a
                        if prev_anchor_first is None and p_a is not None:
                            prev_anchor_first = p_a
                        if n_a is not None:
                            next_anchor_last = n_a
                if c_unobserved_years:
                    country_anchors[c_code] = CountryTemporalAnchor(
                        country_code=c_code,
                        country_name=c_name,
                        unobserved_years=c_unobserved_years,
                        previous_anchor_year=c_prev,
                        next_anchor_year=c_next,
                    )
                    unobserved_countries.append(c_code)
                else:
                    observed_countries.append(c_code)

            obs_years_sorted = sorted(observed_years_set)
            unobs_years_sorted = sorted(unobserved_years_set)

            if unobserved_countries:
                overall_temp_status = TemporalAvailabilityStatus.PERIOD_UNOBSERVED
                if not is_alternative_fallback:
                    status = ResolutionStatus.RESOLVED_WITH_ANCHORS
                anchor_details = [
                    f"{ca.country_name or ca.country_code} sin medición en {ca.unobserved_years} (Puntos ancla oficiales disponibles: {ca.previous_anchor_year} y {ca.next_anchor_year})"
                    for ca in country_anchors.values()
                ]
                trace.append(
                    f"[Stage 5: Temporal Audit] Countries={intent.country_codes}, Years={target_years} -> Status={overall_temp_status.value} (Observed Countries: {observed_countries}, Unobserved Countries: {unobserved_countries}) (Anchors: Prev={prev_anchor_first}, Next={next_anchor_last})"
                )
                trace.append(
                    f"  - Sampling notice: Gaps in survey schedule for countries {unobserved_countries} in years {unobs_years_sorted}. {'; '.join(anchor_details)}. Interpolation strictly forbidden."
                )
                temporal_info = TemporalAnchorInfo(
                    requested_year=intent.year or target_years[-1],
                    requested_years=target_years,
                    observed_years=obs_years_sorted,
                    unobserved_years=unobs_years_sorted,
                    requested_countries=list(intent.country_codes),
                    observed_countries=observed_countries,
                    unobserved_countries=unobserved_countries,
                    country_anchors=country_anchors,
                    temporal_status=overall_temp_status,
                    previous_anchor_year=prev_anchor_first,
                    next_anchor_year=next_anchor_last,
                    forbid_interpolation=True,
                    disclaimer=(
                        f"Entre los países solicitados ({', '.join(intent.country_names)}), presentan brechas de medición muestral: {'; '.join(anchor_details)}. "
                        f"Países con cobertura completa en el período: {observed_countries}. Se prohíbe la interpolación."
                    ),
                )
            else:
                overall_temp_status = TemporalAvailabilityStatus.OBSERVATION_EXISTING
                trace.append(
                    f"[Stage 5: Temporal Audit] Countries={intent.country_codes}, Years={target_years} -> Status={overall_temp_status.value} (Observed Countries: {observed_countries}, Unobserved Countries: [])"
                )
                temporal_info = TemporalAnchorInfo(
                    requested_year=intent.year or target_years[-1],
                    requested_years=target_years,
                    observed_years=obs_years_sorted,
                    unobserved_years=[],
                    requested_countries=list(intent.country_codes),
                    observed_countries=observed_countries,
                    unobserved_countries=[],
                    country_anchors={},
                    temporal_status=overall_temp_status,
                    forbid_interpolation=True,
                )
        elif intent.country_code and len(intent.years) > 1:
            observed_years: list[int] = []
            unobserved_years: list[int] = []
            prev_anchor_first = None
            next_anchor_last = None

            for y in intent.years:
                t_st, p_a, n_a = self.registry.check_temporal_availability(
                    target_indicator_id,
                    intent.country_code,
                    y,
                )
                if t_st == TemporalAvailabilityStatus.OBSERVATION_EXISTING:
                    observed_years.append(y)
                else:
                    unobserved_years.append(y)
                    if prev_anchor_first is None and p_a is not None:
                        prev_anchor_first = p_a
                    if n_a is not None:
                        next_anchor_last = n_a

            if unobserved_years:
                overall_temp_status = TemporalAvailabilityStatus.PERIOD_UNOBSERVED
                if not is_alternative_fallback:
                    status = ResolutionStatus.RESOLVED_WITH_ANCHORS
                trace.append(
                    f"[Stage 5: Temporal Audit] Country={intent.country_code}, Years={intent.years} (Mode: {intent.time_mode}) -> Status={overall_temp_status.value} (Observed: {observed_years}, Unobserved: {unobserved_years})"
                )
                trace.append(
                    f"  - Sampling notice: Gaps in survey schedule for {intent.country_name} in years {unobserved_years}. Observed years in range: {observed_years}. Interpolation strictly forbidden."
                )
                c_anchors = {
                    intent.country_code: CountryTemporalAnchor(
                        country_code=intent.country_code,
                        country_name=intent.country_name,
                        unobserved_years=unobserved_years,
                        previous_anchor_year=prev_anchor_first,
                        next_anchor_year=next_anchor_last,
                    )
                }
                temporal_info = TemporalAnchorInfo(
                    requested_year=intent.year or intent.years[-1],
                    requested_years=list(intent.years),
                    observed_years=observed_years,
                    unobserved_years=unobserved_years,
                    requested_countries=[intent.country_code],
                    observed_countries=[intent.country_code] if observed_years else [],
                    unobserved_countries=[intent.country_code],
                    country_anchors=c_anchors,
                    temporal_status=overall_temp_status,
                    previous_anchor_year=prev_anchor_first,
                    next_anchor_year=next_anchor_last,
                    forbid_interpolation=True,
                    disclaimer=(
                        f"En {intent.country_name} la serie solicitada ({intent.years[0]}-{intent.years[-1]}) presenta años sin medición muestral: {unobserved_years}. "
                        f"Años con observación oficial en el rango: {observed_years}. Se prohíbe la interpolación."
                    ),
                )
            else:
                overall_temp_status = TemporalAvailabilityStatus.OBSERVATION_EXISTING
                trace.append(
                    f"[Stage 5: Temporal Audit] Country={intent.country_code}, Years={intent.years} (Mode: {intent.time_mode}) -> Status={overall_temp_status.value} (Observed: {observed_years}, Unobserved: [])"
                )
                temporal_info = TemporalAnchorInfo(
                    requested_year=intent.year or intent.years[-1],
                    requested_years=list(intent.years),
                    observed_years=observed_years,
                    unobserved_years=[],
                    requested_countries=[intent.country_code],
                    observed_countries=[intent.country_code],
                    unobserved_countries=[],
                    country_anchors={},
                    temporal_status=overall_temp_status,
                    forbid_interpolation=True,
                )
        elif intent.country_code and intent.year:
            temp_status, prev_anchor, next_anchor = self.registry.check_temporal_availability(
                target_indicator_id,
                intent.country_code,
                intent.year,
            )
            trace.append(f"[Stage 5: Temporal Audit] Country={intent.country_code}, Year={intent.year} -> Status={temp_status.value} (Anchors: Prev={prev_anchor}, Next={next_anchor})")

            if temp_status == TemporalAvailabilityStatus.PERIOD_UNOBSERVED:
                if not is_alternative_fallback:
                    status = ResolutionStatus.RESOLVED_WITH_ANCHORS
                trace.append(f"  - Sampling notice: Gap in survey schedule for {intent.country_name} in {intent.year}. Interpolation strictly forbidden.")
                c_anchors = {
                    intent.country_code: CountryTemporalAnchor(
                        country_code=intent.country_code,
                        country_name=intent.country_name,
                        unobserved_years=[intent.year],
                        previous_anchor_year=prev_anchor,
                        next_anchor_year=next_anchor,
                    )
                }
                temporal_info = TemporalAnchorInfo(
                    requested_year=intent.year,
                    requested_years=[intent.year],
                    observed_years=[],
                    unobserved_years=[intent.year],
                    requested_countries=[intent.country_code],
                    observed_countries=[],
                    unobserved_countries=[intent.country_code],
                    country_anchors=c_anchors,
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
                    requested_years=[intent.year],
                    observed_years=[intent.year],
                    unobserved_years=[],
                    requested_countries=[intent.country_code],
                    observed_countries=[intent.country_code],
                    unobserved_countries=[],
                    country_anchors={},
                    temporal_status=temp_status,
                    forbid_interpolation=True,
                )

        # Conversational hints for default assumptions & alternatives
        if conversational_hint is None:
            if target_indicator_id == 1242 and not any(t in intent.clean_query for t in ["%", "pib", "porcentaje", "porciento"]):
                trace.append("  [Decision Audit] Unidad no especificada para ingresos tributarios. Se asume estándar macroeconómico CEPAL: '% del PIB' (ID 1242 / API 821). Medida alternativa disponible: 'Moneda nacional a precios corrientes' (ID 845).")
                conversational_hint = "Nota: Se resolvió por defecto a Ingresos tributarios en porcentaje del PIB (indicador 1242 / API 821). Si requiere la serie en moneda nacional a precios corrientes, consulte el indicador 845."

        result_label = "ALTERNATIVE_PROPOSED" if is_alternative_fallback else "SUCCESS"
        trace.append(f"[Resolution Result] {result_label}: Selected ID {target_indicator_id} ('{selected.name}') with score {selected.relevance_score}. Status={status.value}")
        latency = (time.perf_counter() - t0) * 1000.0
        return SemanticResolutionResponse(
            status=status,
            query=query_str,
            selected_candidate=selected,
            applied_filters=applied_filters,
            temporal_info=temporal_info,
            polarity_info=intent.polarity_info,
            conversational_hint=conversational_hint,
            execution_trace=trace,
            latency_ms=latency,
        )
