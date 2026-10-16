"""Dynamic Dimension & Member Matching Engine for CEPALSTAT."""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING
from statscepal.semantic.facet_ontology import (
    DEFAULT_FACET_ONTOLOGY,
    FacetOntology,
    strip_accents,
)
from statscepal.semantic.models import AppliedDimensionFilter

if TYPE_CHECKING:
    from statscepal.dimensions import Dimension, Member


DIMENSION_KEY_PATTERNS: dict[str, list[str]] = DEFAULT_FACET_ONTOLOGY.build_dimension_key_patterns()
MEMBER_VALUE_PATTERNS: dict[str, list[str]] = DEFAULT_FACET_ONTOLOGY.build_member_value_patterns()


class DynamicMemberMatcher:
    """Matches canonical conceptual facets to indicator dimensions and members dynamically."""

    def __init__(self, ontology: FacetOntology | None = None) -> None:
        self.ontology = ontology or DEFAULT_FACET_ONTOLOGY
        if ontology is not None and ontology is not DEFAULT_FACET_ONTOLOGY:
            self._dimension_key_patterns = self.ontology.build_dimension_key_patterns()
            self._member_value_patterns = self.ontology.build_member_value_patterns()
        else:
            self._dimension_key_patterns = DIMENSION_KEY_PATTERNS
            self._member_value_patterns = MEMBER_VALUE_PATTERNS

    def match_facets_to_dimensions(
        self,
        indicator_id: int,
        dimensions: list[Dimension],
        facets: dict[str, str],
    ) -> tuple[bool, list[AppliedDimensionFilter], list[str]]:
        """Resolve canonical conceptual facets against concrete dimensions and members.

        Args:
            indicator_id: ID of the indicator.
            dimensions: List of Dimension objects containing Member objects.
            facets: Dict mapping facet keys to canonical values (e.g. {"sexo": "FEMENINO"}).

        Returns:
            Tuple of:
            - all_matched (bool): True if all requested facets were matched.
            - applied_filters (list[AppliedDimensionFilter]): Resolved dimension/member filters.
            - unhandled_facets (list[str]): List of facet keys that could not be resolved.
        """
        applied_filters: list[AppliedDimensionFilter] = []
        unhandled_facets: list[str] = []
        used_dim_ids: set[int] = set()

        for facet_key, facet_val in facets.items():
            key_norm = strip_accents(facet_key)
            val_norm = strip_accents(facet_val).upper()
            facet_def = self.ontology.get_facet(facet_key)

            # Target member patterns for this facet value
            target_patterns = list(self._member_value_patterns.get(val_norm, []))
            raw_val_clean = strip_accents(facet_val)
            if raw_val_clean and raw_val_clean not in target_patterns:
                target_patterns.append(raw_val_clean)

            # Find candidate dimensions for this facet key
            if facet_def and facet_def.dimension_name_patterns:
                key_patterns = list(facet_def.dimension_name_patterns)
            else:
                key_patterns = self._dimension_key_patterns.get(key_norm, [key_norm])

            # Group dimensions: Group A (matches key by name or known dim ID), Group B (fallback)
            candidate_dims_a: list[Dimension] = []
            candidate_dims_b: list[Dimension] = []

            for d in dimensions:
                if d.id in used_dim_ids:
                    continue
                d_name_norm = strip_accents(d.name)
                is_candidate_a = False
                if facet_def is not None:
                    if d.id in facet_def.known_dimension_ids or any(kp in d_name_norm for kp in key_patterns):
                        is_candidate_a = True
                else:
                    if any(kp in d_name_norm for kp in key_patterns):
                        is_candidate_a = True

                if is_candidate_a:
                    candidate_dims_a.append(d)
                else:
                    candidate_dims_b.append(d)

            # Try candidate group A first
            match_found = self._find_best_match(candidate_dims_a, target_patterns)
            if not match_found:
                # Try fallback group B
                match_found = self._find_best_match(candidate_dims_b, target_patterns, min_score=60)

            if match_found:
                best_dim, best_member = match_found
                applied_filters.append(
                    AppliedDimensionFilter(
                        dim_id=best_dim.id,
                        dim_name=best_dim.name,
                        member_id=best_member.id,
                        member_name=best_member.name,
                    )
                )
                used_dim_ids.add(best_dim.id)
            else:
                unhandled_facets.append(facet_key)

        all_matched = len(unhandled_facets) == 0
        return all_matched, applied_filters, unhandled_facets

    def _find_best_match(
        self,
        candidate_dims: list[Dimension],
        target_patterns: list[str],
        min_score: int = 1,
    ) -> tuple[Dimension, Member] | None:
        best_candidate: tuple[Dimension, Member] | None = None
        highest_score = -1

        for dim in candidate_dims:
            for member in dim.members:
                score = self._score_member(member.name, target_patterns)
                if score >= min_score and score > highest_score:
                    highest_score = score
                    best_candidate = (dim, member)

        return best_candidate

    def _score_member(self, member_name: str, target_patterns: list[str]) -> int:
        m_name_norm = strip_accents(member_name)
        best_score = 0

        for idx, pat in enumerate(target_patterns):
            rank_penalty = min(idx, 15)
            if m_name_norm == pat:
                score = 100 - rank_penalty
            elif re.search(r"(?:\b|_)" + re.escape(pat) + r"(?:\b|_)", m_name_norm):
                score = 80 - rank_penalty
            elif pat in m_name_norm:
                score = 60 - rank_penalty
            elif len(m_name_norm) >= 3 and m_name_norm in pat:
                score = 40 - rank_penalty
            else:
                score = 0

            if score > best_score:
                best_score = score

        return best_score
