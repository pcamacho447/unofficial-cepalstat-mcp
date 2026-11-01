"""Systematic Mutation Testing Suite against Silent Degradation.

Verifies that modifying canonical queries across 4 mutation operators:
1. Unsupported / bogus breakdown (e.g. 'por tipo de sangre', 'por religión', 'por signo zodiacal')
2. Geography invalidation (replacing LAC country with non-LAC country)
3. Frequency invalidation (e.g. 'en tiempo real', 'al minuto')
4. Denominator / unit mutation (e.g. 'per cápita')

NEVER silently returns the base aggregate indicator with score 1.0 and identical dimension filters.
Strict Invariant: 100% of mutations must alter the response (change candidate, adapt filters,
propose alternative, or abstain).
"""

import pytest

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus

# Canonical base queries covering diverse socioeconomic dimensions and LAC countries
BASE_QUERIES = [
    "inflación anual en Chile 2022",
    "pobreza en Colombia 2021",
    "desempleo en Perú 2022",
    "PIB en México 2021",
    "deuda pública en Brasil 2021",
    "salario mínimo en Uruguay 2021",
    "gasto social en Costa Rica 2020",
    "esperanza de vida en Ecuador 2022",
]

NON_LAC_REPLACEMENTS = {
    "Chile": "España",
    "Colombia": "Alemania",
    "Perú": "Francia",
    "México": "Italia",
    "Brasil": "Japón",
    "Uruguay": "Canadá",
    "Costa Rica": "Reino Unido",
    "Ecuador": "Estados Unidos",
}


def mutate_geography_invalidation(query: str) -> str:
    """Replaces any LAC country present in the query with its non-LAC counterpart."""
    mutated = query
    for lac, non_lac in NON_LAC_REPLACEMENTS.items():
        if lac in mutated:
            mutated = mutated.replace(lac, non_lac)
            break
    return mutated


def test_mutations_never_return_silent_identical_aggregate() -> None:
    """Core 4-operator mutation loop ensuring 100% divergence from base canonical response."""
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")

    for base_query in BASE_QUERIES:
        base_resp = engine.resolve(base_query)
        assert base_resp.status == ResolutionStatus.RESOLVED, (
            f"Base query '{base_query}' must resolve cleanly before testing mutations."
        )
        base_id = base_resp.selected_candidate.indicator_id if base_resp.selected_candidate else None
        base_filters = base_resp.applied_filters.dimensions if base_resp.applied_filters else []

        # Operator 1: Unsupported Breakdown Mutation
        mut_breakdown = f"{base_query} por tipo de sangre"
        resp_b = engine.resolve(mut_breakdown)
        assert resp_b.status == ResolutionStatus.ABSTAINED, (
            f"Must abstain on bogus breakdown: '{mut_breakdown}'"
        )

        # Operator 2: Geography Invalidation Mutation
        mut_geo = mutate_geography_invalidation(base_query)
        resp_g = engine.resolve(mut_geo)
        assert resp_g.status == ResolutionStatus.ABSTAINED, (
            f"Must abstain on non-LAC geography: '{mut_geo}'"
        )
        assert "UNSUPPORTED_COUNTRY_NON_LAC" in (resp_g.abstention_reason or ""), (
            f"Abstention reason for '{mut_geo}' must mention UNSUPPORTED_COUNTRY_NON_LAC, got: {resp_g.abstention_reason}"
        )

        # Operator 3: Real-Time Frequency Invalidation Mutation
        mut_freq = f"{base_query} en tiempo real"
        resp_f = engine.resolve(mut_freq)
        assert resp_f.status == ResolutionStatus.ABSTAINED, (
            f"Must abstain on real-time request: '{mut_freq}'"
        )
        assert resp_f.abstention_reason == "UNSUPPORTED_FREQUENCY", (
            f"Abstention reason for '{mut_freq}' must be UNSUPPORTED_FREQUENCY, got: {resp_f.abstention_reason}"
        )

        # Operator 4: Denominator / Unit Mutation
        # When query is modified with "per cápita", it must NOT return the identical total indicator without adapting
        if "PIB" in base_query or "gasto social" in base_query:
            mut_pc = f"{base_query} per cápita"
            resp_pc = engine.resolve(mut_pc)
            if resp_pc.status == ResolutionStatus.RESOLVED and resp_pc.selected_candidate:
                # Must adapt indicator (e.g. 2206 instead of 2204, 3128 instead of 4410) or add dimension
                new_id = resp_pc.selected_candidate.indicator_id
                assert new_id != base_id or resp_pc.applied_filters.dimensions != base_filters, (
                    f"Query '{mut_pc}' silently returned identical aggregate indicator {base_id}!"
                )


@pytest.mark.parametrize("breakdown", [
    "por tipo de sangre",
    "por religión",
])
def test_operator_1_unsupported_breakdown_mutations(breakdown: str) -> None:
    """Verifies that appending unscientific or unsupported breakdowns triggers hard abstention."""
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    for base_query in BASE_QUERIES:
        mutated = f"{base_query} {breakdown}"
        resp = engine.resolve(mutated)
        assert resp.status == ResolutionStatus.ABSTAINED, (
            f"Bogus breakdown mutation '{mutated}' should have abstained, got {resp.status} with candidate {resp.selected_candidate}"
        )


def test_operator_2_geography_invalidation_all_countries() -> None:
    """Verifies that substituting each LAC country with a non-LAC country yields UNSUPPORTED_COUNTRY_NON_LAC."""
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    for base_query in BASE_QUERIES:
        mut_geo = mutate_geography_invalidation(base_query)
        resp = engine.resolve(mut_geo)
        assert resp.status == ResolutionStatus.ABSTAINED, (
            f"Query with non-LAC geography '{mut_geo}' should have abstained, got {resp.status}"
        )
        assert resp.abstention_reason is not None and "UNSUPPORTED_COUNTRY_NON_LAC" in resp.abstention_reason, (
            f"Query '{mut_geo}' expected UNSUPPORTED_COUNTRY_NON_LAC reason, got: {resp.abstention_reason}"
        )


@pytest.mark.parametrize("freq_mod", [
    "en tiempo real",
    "al minuto",
    "minuto a minuto",
])
def test_operator_3_frequency_invalidation_mutations(freq_mod: str) -> None:
    """Verifies that high-frequency real-time modifiers trigger UNSUPPORTED_FREQUENCY abstention."""
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    for base_query in BASE_QUERIES:
        mutated = f"{base_query} {freq_mod}"
        resp = engine.resolve(mutated)
        assert resp.status == ResolutionStatus.ABSTAINED, (
            f"Frequency invalidation mutation '{mutated}' should have abstained, got {resp.status}"
        )
        assert resp.abstention_reason == "UNSUPPORTED_FREQUENCY", (
            f"Expected UNSUPPORTED_FREQUENCY for '{mutated}', got: {resp.abstention_reason}"
        )


def test_strict_mutation_invariant_zero_silent_degradation() -> None:
    """Enforces 100% mutation divergence rate across all 4 operators applied to all base queries."""
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    total_mutations = 0
    diverged_mutations = 0

    for base_query in BASE_QUERIES:
        base_resp = engine.resolve(base_query)
        assert base_resp.status == ResolutionStatus.RESOLVED
        base_id = base_resp.selected_candidate.indicator_id if base_resp.selected_candidate else None
        base_filters = base_resp.applied_filters.dimensions if base_resp.applied_filters else []

        mutations = [
            f"{base_query} por tipo de sangre",
            mutate_geography_invalidation(base_query),
            f"{base_query} en tiempo real",
            f"{base_query} per cápita",
        ]

        for mut_q in mutations:
            total_mutations += 1
            mut_resp = engine.resolve(mut_q)

            # Invariant: mutated response must differ from base aggregate (status change, candidate change,
            # filters change, or abstention). It must NEVER return identical indicator with identical filters and score 1.0.
            mut_id = mut_resp.selected_candidate.indicator_id if mut_resp.selected_candidate else None
            mut_filters = mut_resp.applied_filters.dimensions if mut_resp.applied_filters else []

            is_silent_duplicate = (
                mut_resp.status == ResolutionStatus.RESOLVED
                and mut_id == base_id
                and mut_filters == base_filters
            )

            assert not is_silent_duplicate, (
                f"MUTATION SILENT DEGRADATION: Query '{mut_q}' returned identical aggregate indicator {base_id} "
                f"with identical filters {base_filters}!"
            )
            diverged_mutations += 1

    mutation_divergence_rate = (diverged_mutations / total_mutations) * 100.0
    assert mutation_divergence_rate == 100.0, (
        f"Strict Invariant: 100% of mutations must alter response, got {mutation_divergence_rate:.1f}% "
        f"({diverged_mutations}/{total_mutations})"
    )
