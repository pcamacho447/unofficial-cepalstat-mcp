"""Dynamic Dimension & Member Matching Engine for CEPALSTAT."""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING
from statscepal.semantic.models import AppliedDimensionFilter

if TYPE_CHECKING:
    from statscepal.dimensions import Dimension, Member


def strip_accents(text: str) -> str:
    """Normalize string to lowercase and strip diacritics."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").strip()


DIMENSION_KEY_PATTERNS: dict[str, list[str]] = {
    "sexo": ["sexo", "genero"],
    "area": ["area", "zona", "area geografica"],
    "edad": ["edad", "grupo de edad", "tramo de edad", "grupos de edad"],
    "quintil": ["quintil", "decil", "estrato"],
    "moneda": ["moneda", "precios", "unidad"],
    "actividad": ["actividad", "rama", "sector"],
    "severidad": ["pobreza", "severidad", "tipo de pobreza", "condicion de pobreza"],
    "canasta": ["canasta", "alimentos", "bienes"],
    "educacion": ["educacion", "anos de educacion", "nivel", "instruccion"],
}

MEMBER_VALUE_PATTERNS: dict[str, list[str]] = {
    # Sexo
    "FEMENINO": ["mujeres", "mujer", "femenino"],
    "MUJER": ["mujeres", "mujer", "femenino"],
    "MASCULINO": ["hombres", "hombre", "masculino"],
    "HOMBRE": ["hombres", "hombre", "masculino"],
    "AMBOS_SEXOS": ["ambos sexos", "ambos", "total"],
    "TOTAL": ["total", "ambos sexos", "ambos", "nacional", "pais"],
    # Area
    "RURAL": ["rural", "area rural", "sector rural"],
    "URBANO": ["urbano", "area urbana", "sector urbano"],
    "NACIONAL": ["nacional", "total", "pais", "todo el pais"],
    # Edad
    "JUVENTUD": ["15 a 24 anos", "15-24", "jovenes", "juventud", "15 a 24"],
    "JOVENES": ["15 a 24 anos", "15-24", "jovenes", "juventud", "15 a 24"],
    "ADULTOS_MAYORES": ["60 anos y mas", "65 anos y mas", "60 y mas", "65 y mas", "adultos mayores", "tercera edad"],
    "INFANCIA": ["0 a 14 anos", "0-14", "ninos", "ninas", "infancia", "0 a 14"],
    # Quintiles
    "QUINTIL_1": ["quintil 1", "i quintil", "primer quintil", "q1", "1 quintil"],
    "QUINTIL_2": ["quintil 2", "ii quintil", "segundo quintil", "q2", "2 quintil"],
    "QUINTIL_3": ["quintil 3", "iii quintil", "tercer quintil", "q3", "3 quintil"],
    "QUINTIL_4": ["quintil 4", "iv quintil", "cuarto quintil", "q4", "4 quintil"],
    "QUINTIL_5": ["quintil 5", "v quintil", "quinto quintil", "q5", "5 quintil"],
    # Severidad
    "POBREZA_EXTREMA": ["pobreza extrema", "extrema", "indigencia", "pobreza extrema / indigencia", "indigente"],
    "EXTREMA": ["pobreza extrema", "extrema", "indigencia", "pobreza extrema / indigencia", "indigente"],
    "POBREZA_TOTAL": ["total", "pobreza", "total pobreza", "pobres"],
    "POBREZA": ["total", "pobreza", "total pobreza", "pobres"],
    # Moneda
    "DOLARES_CONSTANTES": ["dolares a precios constantes", "dolares constantes", "precios constantes", "dolares"],
    "MONEDA_NACIONAL": ["moneda nacional", "moneda local"],
    # Canasta
    "ALIMENTOS": ["alimentos y bebidas", "alimentos", "comida", "alimentos y bebidas no alcoholicas"],
    # Sector / Actividad
    "PUBLICO": ["publico", "sector publico", "gobierno"],
    "PRIVADO": ["privado", "sector privado"],
}


class DynamicMemberMatcher:
    """Matches canonical conceptual facets to indicator dimensions and members dynamically."""

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

            # Target member patterns for this facet value
            target_patterns = list(MEMBER_VALUE_PATTERNS.get(val_norm, []))
            raw_val_clean = strip_accents(facet_val)
            if raw_val_clean and raw_val_clean not in target_patterns:
                target_patterns.append(raw_val_clean)

            # Find candidate dimensions for this facet key
            key_patterns = DIMENSION_KEY_PATTERNS.get(key_norm, [key_norm])

            # Group dimensions: Group A (matches key by name), Group B (fallback)
            candidate_dims_a: list[Dimension] = []
            candidate_dims_b: list[Dimension] = []

            for d in dimensions:
                if d.id in used_dim_ids:
                    continue
                d_name_norm = strip_accents(d.name)
                if any(kp in d_name_norm for kp in key_patterns):
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
