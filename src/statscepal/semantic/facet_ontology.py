"""Declarative Facet Ontology and Registry for CEPALSTAT.

Centralizes canonical socioeconomic and structural facets, known dimension IDs,
name patterns, member value patterns, and implicit-aggregate semantics.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def strip_accents(text: str) -> str:
    """Normalize string to lowercase and strip diacritics."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").strip()


class QueryTriggerRule(BaseModel):
    """Lexical trigger rule mapping query phrases to canonical facet values."""

    model_config = ConfigDict(frozen=True)

    canonical_value: str
    phrases: tuple[str, ...]
    require_word_boundary: bool = True


class MemberPatternRule(BaseModel):
    """Pattern rule mapping dimension member labels to canonical values."""

    model_config = ConfigDict(frozen=True)

    canonical_value: str
    patterns: tuple[str, ...]


class FacetDefinition(BaseModel):
    """Declarative specification of a canonical conceptual facet in CEPALSTAT."""

    model_config = ConfigDict(frozen=True)

    facet_key: str
    description: str
    synset_domain: str | None = None
    known_dimension_ids: frozenset[int] = Field(default_factory=frozenset)
    dimension_name_patterns: tuple[str, ...] = Field(default_factory=tuple)
    member_value_patterns: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    implicit_aggregate_values: frozenset[str] = Field(default_factory=frozenset)
    breakdown_values: frozenset[str] = Field(default_factory=frozenset)
    total_member_patterns: tuple[str, ...] = Field(default_factory=tuple)
    query_triggers: tuple[QueryTriggerRule, ...] = Field(default_factory=tuple)


class FacetAuditReport(BaseModel):
    """Audit report comparing harvested dimensions against the facet ontology."""

    total_distinct_dimensions: int = 0
    structural_dimensions: list[dict[str, Any]] = Field(default_factory=list)
    mapped_dimensions: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    unmapped_dimensions: list[dict[str, Any]] = Field(default_factory=list)
    coverage_ratio: float = 0.0

    @property
    def mapped_count(self) -> int:
        """Total count of mapped non-structural dimensions."""
        return sum(len(dims) for dims in self.mapped_dimensions.values())

    def to_dict(self) -> dict[str, Any]:
        """Convert audit report to dictionary."""
        return self.model_dump()



class FacetOntology:
    """Declarative ontology and classification registry for CEPALSTAT facets."""

    def __init__(
        self,
        facets: Sequence[FacetDefinition] | Mapping[str, FacetDefinition] | None = None,
    ) -> None:
        if facets is None:
            self._facets: dict[str, FacetDefinition] = {}
        elif isinstance(facets, Mapping):
            self._facets = dict(facets)
        else:
            self._facets = {f.facet_key: f for f in facets}

        self._compiled_triggers: dict[
            str, list[tuple[str, re.Pattern[str] | None, tuple[str, ...]]]
        ] = {}
        self._normalized_total_patterns: dict[str, frozenset[str]] = {}
        for fdef in self._facets.values():
            self._normalized_total_patterns[fdef.facet_key] = frozenset(
                strip_accents(p) for p in fdef.total_member_patterns if strip_accents(p)
            )
            if not fdef.query_triggers:
                continue
            rules_list: list[tuple[str, re.Pattern[str] | None, tuple[str, ...]]] = []
            for rule in fdef.query_triggers:
                norm_phrases = tuple(
                    strip_accents(p) for p in rule.phrases if strip_accents(p)
                )
                if not norm_phrases:
                    continue
                if rule.require_word_boundary:
                    joined = "|".join(re.escape(p) for p in norm_phrases)
                    pat = re.compile(r"\b(?:" + joined + r")\b")
                    rules_list.append((rule.canonical_value, pat, norm_phrases))
                else:
                    rules_list.append((rule.canonical_value, None, norm_phrases))
            if rules_list:
                self._compiled_triggers[fdef.facet_key] = rules_list

    def get_facet(self, facet_key: str) -> FacetDefinition | None:
        """Retrieve a facet definition by its canonical key."""
        return self._facets.get(strip_accents(facet_key).lower())

    def all_facets(self) -> list[FacetDefinition]:
        """Return all registered facet definitions."""
        return list(self._facets.values())

    def is_critical_unhandled_facet(self, facet_key: str, facet_value: str) -> bool:
        """Return True if facet is unknown or if facet_value is NOT in implicit_aggregate_values.

        Explicit breakdown values always require the dimension to exist. Implicit national/total
        defaults can be satisfied by canonical indicators without forcing a breakdown swap.
        """
        fdef = self.get_facet(facet_key)
        if fdef is None:
            return True
        val_norm = strip_accents(facet_value).upper()
        return val_norm not in fdef.implicit_aggregate_values

    def is_breakdown_value(self, facet_key: str, facet_value: str) -> bool:
        """Return True if facet_value requests a full multi-member breakdown of the dimension."""
        fdef = self.get_facet(facet_key)
        if fdef is None:
            return False
        val_norm = strip_accents(facet_value).upper()
        return val_norm in fdef.breakdown_values

    def is_aggregate_member_name(self, facet_key: str, member_name: str) -> bool:
        """Return True if member_name represents an aggregate/total member for the given facet."""
        m_norm = strip_accents(member_name)
        if not m_norm:
            return False
        key_clean = strip_accents(facet_key).lower()
        norm_set = self._normalized_total_patterns.get(key_clean)
        if norm_set is not None and len(norm_set) > 0:
            return m_norm in norm_set
        return m_norm in {"total", "nacional", "ambos sexos"}

    def is_structural_dimension(self, dim_id: int, dim_name: str) -> bool:
        """Return True if dimension is Country or Time structural dimension."""
        if dim_id in {208, 29117}:
            return True
        norm = strip_accents(dim_name).replace("_", " ")
        base = re.sub(r"__.*$", "", norm).strip()

        structural_exact = {
            "pais",
            "paises",
            "ano",
            "anos",
            "trimestre",
            "trimestres",
            "mes",
            "meses",
            "quinquenio",
            "periodo",
            "tiempo",
        }
        if base in structural_exact:
            return True

        if re.search(
            r"^\b(pais|paises|anos?|trimestres?|mes(es)?|quinquenio|periodo)\b(\s+estandar.*)?$",
            base,
        ):
            return True

        return False

    def classify_dimension(self, dim_id: int, dim_name: str) -> str | None:
        """Classify a dimension ID and name into a facet key, '__structural__', or None."""
        # 1. Known dimension IDs in ontology
        for fdef in self._facets.values():
            if dim_id in fdef.known_dimension_ids:
                return fdef.facet_key

        # 2. Structural dimension check
        if self.is_structural_dimension(dim_id, dim_name):
            return "__structural__"

        # 3. Match dimension name patterns across facets
        norm = strip_accents(dim_name).replace("_", " ")
        base = re.sub(r"__.*$", "", norm).strip()

        for fdef in self._facets.values():
            for pat in fdef.dimension_name_patterns:
                pat_norm = strip_accents(pat)
                if pat_norm == base or pat_norm == norm:
                    return fdef.facet_key
                if re.search(r"\b" + re.escape(pat_norm) + r"\b", base) or re.search(
                    r"\b" + re.escape(pat_norm) + r"\b", norm
                ):
                    return fdef.facet_key

        return None

    def build_dimension_key_patterns(self) -> dict[str, list[str]]:
        """Build mapping from facet keys to dimension name patterns for matching."""
        return {
            f.facet_key: list(f.dimension_name_patterns)
            for f in self._facets.values()
        }

    def build_member_value_patterns(self) -> dict[str, list[str]]:
        """Build unified mapping from canonical member keys to match patterns."""
        result: dict[str, list[str]] = {}
        for f in self._facets.values():
            for member_key, patterns in f.member_value_patterns.items():
                if member_key not in result:
                    result[member_key] = []
                for p in patterns:
                    if p not in result[member_key]:
                        result[member_key].append(p)
        return result

    def audit_dimensions(self, dimension_rows: list[dict[str, Any]]) -> FacetAuditReport:
        """Audit harvested dimension rows against this ontology."""
        structural: list[dict[str, Any]] = []
        mapped: dict[str, list[dict[str, Any]]] = {}
        unmapped: list[dict[str, Any]] = []

        for row in dimension_rows:
            dim_id = int(row["dim_id"])
            dim_name = str(row.get("dim_name", ""))
            classification = self.classify_dimension(dim_id, dim_name)

            if classification == "__structural__":
                structural.append(row)
            elif classification is not None:
                mapped.setdefault(classification, []).append(row)
            else:
                unmapped.append(row)

        total = len(dimension_rows)
        mapped_or_structural = len(structural) + sum(len(v) for v in mapped.values())
        coverage = (mapped_or_structural / total) if total > 0 else 1.0

        return FacetAuditReport(
            total_distinct_dimensions=total,
            structural_dimensions=structural,
            mapped_dimensions=mapped,
            unmapped_dimensions=unmapped,
            coverage_ratio=coverage,
        )

    def extract_facets_from_query(
        self,
        clean_query: str,
        thesaurus: Any = None,
    ) -> dict[str, str]:
        """Extract canonical facets from a normalized query string using triggers and synsets."""
        clean = strip_accents(clean_query)
        facets: dict[str, str] = {}

        for fdef in self._facets.values():
            # 1. Check QueryTriggerRules for breakdown values first (e.g., 'urbano y rural', 'por sexo')
            compiled_rules = self._compiled_triggers.get(fdef.facet_key)
            if compiled_rules:
                for canonical_val, pat, norm_phrases in compiled_rules:
                    if canonical_val in fdef.breakdown_values:
                        if pat is not None:
                            if pat.search(clean):
                                facets[fdef.facet_key] = canonical_val
                                break
                        else:
                            if any(p in clean for p in norm_phrases):
                                facets[fdef.facet_key] = canonical_val
                                break
            if fdef.facet_key in facets:
                continue

            # 2. Thesaurus synset match if domain is defined
            if thesaurus is not None and fdef.synset_domain:
                if fdef.synset_domain == "facet_edad" and hasattr(thesaurus, "match_all_synsets"):
                    edad_matches = thesaurus.match_all_synsets("facet_edad", clean)
                    if any(m.canonical_id == "INFANCIA" for m in edad_matches):
                        facets[fdef.facet_key] = "INFANCIA"
                    elif edad_matches:
                        facets[fdef.facet_key] = edad_matches[0].canonical_id
                else:
                    match = thesaurus.match_synset(fdef.synset_domain, clean)
                    if match:
                        cid = match.canonical_id
                        if fdef.facet_key == "canasta":
                            if cid == "CANASTA_ALIMENTOS":
                                facets[fdef.facet_key] = "ALIMENTOS"
                        else:
                            facets[fdef.facet_key] = cid

            # 3. QueryTriggerRules if not yet matched
            if fdef.facet_key not in facets:
                compiled_rules = self._compiled_triggers.get(fdef.facet_key)
                if compiled_rules:
                    for canonical_val, pat, norm_phrases in compiled_rules:
                        if pat is not None:
                            if pat.search(clean):
                                facets[fdef.facet_key] = canonical_val
                                break
                        else:
                            if any(p in clean for p in norm_phrases):
                                facets[fdef.facet_key] = canonical_val
                                break

        return facets


DEFAULT_FACETS: list[FacetDefinition] = [
    FacetDefinition(
        facet_key="sexo",
        description="Desagregación por sexo o género",
        synset_domain="facet_sexo",
        known_dimension_ids=frozenset({144}),
        dimension_name_patterns=("sexo", "genero"),
        member_value_patterns={
            "FEMENINO": ("mujeres", "mujer", "femenino", "pibas", "chavas", "chicas"),
            "MUJER": ("mujeres", "mujer", "femenino", "pibas", "chavas", "chicas"),
            "MASCULINO": ("hombres", "hombre", "masculino", "varones", "pibes", "chavos"),
            "HOMBRE": ("hombres", "hombre", "masculino", "varones", "pibes", "chavos"),
            "AMBOS_SEXOS": ("ambos sexos", "ambos", "total"),
            "AMBOS": ("ambos sexos", "ambos", "total"),
            "TOTAL": ("total", "ambos sexos", "ambos", "nacional", "pais"),
            "SEXO_DESGLOSE": ("hombres", "mujeres"),
        },
        implicit_aggregate_values=frozenset({"TOTAL", "AMBOS_SEXOS", "AMBOS"}),
        breakdown_values=frozenset({"SEXO_DESGLOSE"}),
        total_member_patterns=("total", "ambos sexos", "ambos"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="SEXO_DESGLOSE",
                phrases=("por sexo", "segun sexo", "por genero", "segun genero"),
            ),
            QueryTriggerRule(
                canonical_value="FEMENINO",
                phrases=("mujeres", "mujer", "femenino", "femenina", "pibas", "chicas"),
            ),
            QueryTriggerRule(
                canonical_value="MASCULINO",
                phrases=("hombres", "hombre", "masculino", "varones", "pibes"),
            ),
            QueryTriggerRule(
                canonical_value="AMBOS_SEXOS",
                phrases=("ambos sexos", "hombres y mujeres"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="area",
        description="Desagregación geográfica por área urbana o rural",
        synset_domain="facet_area",
        known_dimension_ids=frozenset({326, 1364}),
        dimension_name_patterns=("area", "zona", "area geografica"),
        member_value_patterns={
            "RURAL": ("rural", "area rural", "sector rural", "campo", "el campo", "zona rural"),
            "URBANO": ("urbano", "area urbana", "sector urbano", "ciudad", "ciudades", "zona urbana"),
            "NACIONAL": ("nacional", "total", "pais", "todo el pais"),
            "AREA_DESGLOSE": ("urbano", "rural"),
        },
        implicit_aggregate_values=frozenset({"NACIONAL"}),
        breakdown_values=frozenset({"AREA_DESGLOSE"}),
        total_member_patterns=("nacional", "total", "pais", "todo el pais"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="AREA_DESGLOSE",
                phrases=(
                    "por area",
                    "segun area",
                    "por area geografica",
                    "segun area geografica",
                    "urbano y rural",
                    "urbana y rural",
                ),
            ),
            QueryTriggerRule(
                canonical_value="RURAL",
                phrases=("rural", "campo", "el campo", "sector rural", "zona rural"),
            ),
            QueryTriggerRule(
                canonical_value="URBANO",
                phrases=("urbano", "ciudad", "ciudades", "sector urbano", "zona urbana"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="severidad",
        description="Nivel de severidad o línea de pobreza (extrema vs total)",
        synset_domain="facet_severidad",
        known_dimension_ids=frozenset({1361, 500}),
        dimension_name_patterns=("pobreza", "severidad", "tipo de pobreza", "condicion de pobreza"),
        member_value_patterns={
            "POBREZA_EXTREMA": (
                "pobreza extrema",
                "extrema",
                "indigencia",
                "pobreza extrema / indigencia",
                "indigente",
            ),
            "EXTREMA": (
                "pobreza extrema",
                "extrema",
                "indigencia",
                "pobreza extrema / indigencia",
                "indigente",
            ),
            "POBREZA_TOTAL": ("total", "pobreza", "total pobreza", "pobres"),
            "POBREZA": ("total", "pobreza", "total pobreza", "pobres"),
        },
        implicit_aggregate_values=frozenset({"POBREZA_TOTAL"}),
        total_member_patterns=("total", "pobreza", "total pobreza"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="POBREZA_EXTREMA",
                phrases=("pobreza extrema", "extrema", "indigencia", "indigente"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="etnia",
        description="Pertenencia étnica o racial (indígena, afrodescendiente)",
        synset_domain="facet_etnia",
        known_dimension_ids=frozenset({43039, 78149, 140625}),
        dimension_name_patterns=(
            "etnia",
            "tipo de etnia",
            "autoidentificacion etnico-racial",
            "etnico",
            "etnico-racial",
            "raza",
            "condicion indigena",
            "condicion afrodescendiente",
        ),
        member_value_patterns={
            "INDIGENA": ("indigena", "indigenas", "pueblos indigenas", "originarios"),
            "AFRODESCENDIENTE": ("afrodescendiente", "afrodescendientes", "afro", "negros"),
            "NO_INDIGENA": ("no indigena", "no indigena ni afrodescendiente"),
            "ETNICO_TOTAL": (
                "indigena",
                "no indigena",
                "afrodescendiente",
                "no afrodescendiente",
                "no indigena ni afrodescendiente",
                "etnia",
                "etnico",
                "etnica",
            ),
            "ETNICO": ("etnia", "etnico", "etnica"),
        },
        implicit_aggregate_values=frozenset(),
        breakdown_values=frozenset({"ETNICO_TOTAL", "ETNICO"}),
        total_member_patterns=("total", "nacional", "ambos", "ambos sexos"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="INDIGENA",
                phrases=("indigena", "indigenas", "pueblos indigenas", "originarios", "pueblos originarios"),
            ),
            QueryTriggerRule(
                canonical_value="AFRODESCENDIENTE",
                phrases=("afrodescendiente", "afrodescendientes", "afro", "afrolatino", "afrolatina"),
            ),
            QueryTriggerRule(
                canonical_value="NO_INDIGENA",
                phrases=("no indigena", "no indigena ni afrodescendiente"),
            ),
            QueryTriggerRule(
                canonical_value="ETNICO_TOTAL",
                phrases=("etnica", "etnico", "etnicas", "etnicos", "etnia"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="edad",
        description="Grupos y tramos de edad",
        synset_domain="facet_edad",
        known_dimension_ids=frozenset(),
        dimension_name_patterns=("edad", "grupo de edad", "tramo de edad", "grupos de edad"),
        member_value_patterns={
            "JUVENTUD": (
                "15 a 24 anos",
                "15-24",
                "jovenes",
                "juventud",
                "15 a 24",
                "cabros",
                "pibes",
                "chavos",
                "juvenil",
            ),
            "JOVENES": (
                "15 a 24 anos",
                "15-24",
                "jovenes",
                "juventud",
                "15 a 24",
                "cabros",
                "pibes",
                "chavos",
                "juvenil",
            ),
            "ADULTOS_MAYORES": (
                "60 anos y mas",
                "65 anos y mas",
                "60 y mas",
                "65 y mas",
                "adultos mayores",
                "tercera edad",
            ),
            "INFANCIA": ("0 a 14 anos", "0-14", "ninos", "ninas", "infancia", "0 a 14"),
            "EDAD_DESGLOSE": ("0 a 14", "15 a 24", "65"),
        },
        implicit_aggregate_values=frozenset(),
        breakdown_values=frozenset({"EDAD_DESGLOSE"}),
        total_member_patterns=("total", "todas las edades"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="EDAD_DESGLOSE",
                phrases=(
                    "por edad",
                    "segun edad",
                    "por grupo de edad",
                    "por grupos de edad",
                    "segun grupo de edad",
                    "segun grupos de edad",
                ),
            ),
            QueryTriggerRule(
                canonical_value="JUVENTUD",
                phrases=("jovenes", "juventud", "juvenil", "15 a 24 anos"),
            ),
            QueryTriggerRule(
                canonical_value="ADULTOS_MAYORES",
                phrases=("adultos mayores", "tercera edad", "ancianos"),
            ),
            QueryTriggerRule(
                canonical_value="INFANCIA",
                phrases=("infancia", "ninos", "ninas", "primera infancia"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="quintil",
        description="Estratificación por quintil o decil de ingreso",
        synset_domain="facet_quintil",
        known_dimension_ids=frozenset(),
        dimension_name_patterns=("quintil", "decil", "estrato"),
        member_value_patterns={
            "QUINTIL_1": ("quintil 1", "i quintil", "primer quintil", "q1", "1 quintil"),
            "QUINTIL_2": ("quintil 2", "ii quintil", "segundo quintil", "q2", "2 quintil"),
            "QUINTIL_3": ("quintil 3", "iii quintil", "tercer quintil", "q3", "3 quintil"),
            "QUINTIL_4": ("quintil 4", "iv quintil", "cuarto quintil", "q4", "4 quintil"),
            "QUINTIL_5": ("quintil 5", "v quintil", "quinto quintil", "q5", "5 quintil"),
            "QUINTIL": ("quintil", "quintiles"),
        },
        implicit_aggregate_values=frozenset(),
        breakdown_values=frozenset({"QUINTIL"}),
        total_member_patterns=("total", "nacional"),
        query_triggers=(),
    ),
    FacetDefinition(
        facet_key="estrato",
        description="Estratificación socioeconómica o nivel de ingreso",
        synset_domain="facet_estrato",
        known_dimension_ids=frozenset(),
        dimension_name_patterns=("estrato", "estratificacion", "nivel socioeconomico"),
        member_value_patterns={
            "QUINTIL_1": ("quintil 1", "i quintil", "primer quintil", "q1", "1 quintil"),
            "QUINTIL_2": ("quintil 2", "ii quintil", "segundo quintil", "q2", "2 quintil"),
            "QUINTIL_3": ("quintil 3", "iii quintil", "tercer quintil", "q3", "3 quintil"),
            "QUINTIL_4": ("quintil 4", "iv quintil", "cuarto quintil", "q4", "4 quintil"),
            "QUINTIL_5": ("quintil 5", "v quintil", "quinto quintil", "q5", "5 quintil"),
            "DECIL_1": ("decil 1", "i decil", "primer decil", "d1"),
            "DECIL_10": ("decil 10", "x decil", "decimo decil", "d10"),
            "DECIL": ("decil", "deciles"),
            "QUINTIL": ("quintil", "quintiles", "estrato", "estratos"),
            "RELACION_Q5_Q1": ("relacion quintil 5 / quintil 1", "q5/q1", "q5 versus q1", "quintil 5 vs quintil 1", "quintil 5 versus quintil 1"),
        },
        implicit_aggregate_values=frozenset(),
        breakdown_values=frozenset({"QUINTIL", "DECIL"}),
        total_member_patterns=("total", "nacional"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="QUINTIL",
                phrases=("estrato", "estratos"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="educacion",
        description="Nivel educativo o años de instrucción",
        synset_domain="facet_educacion",
        known_dimension_ids=frozenset(),
        dimension_name_patterns=(
            "educacion",
            "anos de educacion",
            "nivel",
            "instruccion",
            "nivel de instruccion",
            "escolaridad",
        ),
        member_value_patterns={
            "PRIMARIA": ("primaria", "primaria completa", "educacion primaria", "basica"),
            "SECUNDARIA": ("secundaria", "secundaria completa", "educacion secundaria", "media"),
            "TERCIARIA": ("terciaria", "superior", "educacion superior"),
            "UNIVERSITARIA": ("universitaria", "universidad", "superior universitaria"),
            "SIN_INSTRUCCION": ("sin instruccion", "ninguno", "analfabeto"),
        },
        implicit_aggregate_values=frozenset(),
        total_member_patterns=("total", "nacional"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="UNIVERSITARIA",
                phrases=("educacion universitaria", "universitaria", "universidad", "educacion superior", "terciaria"),
            ),
            QueryTriggerRule(
                canonical_value="SECUNDARIA",
                phrases=("educacion secundaria", "secundaria completa", "secundaria", "educacion media"),
            ),
            QueryTriggerRule(
                canonical_value="PRIMARIA",
                phrases=("educacion primaria", "primaria completa", "primaria", "educacion basica"),
            ),
            QueryTriggerRule(
                canonical_value="SIN_INSTRUCCION",
                phrases=("sin instruccion", "ninguna instruccion", "analfabetos", "analfabeto"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="formalidad",
        description="Condición de formalidad o informalidad laboral",
        synset_domain="facet_formalidad",
        known_dimension_ids=frozenset(),
        dimension_name_patterns=(
            "formalidad",
            "empleo formal",
            "informal",
            "tipo de empleo",
            "categoria ocupacional",
        ),
        member_value_patterns={
            "FORMAL": ("formal", "empleo formal", "sector formal"),
            "INFORMAL": ("informal", "empleo informal", "sector informal"),
        },
        implicit_aggregate_values=frozenset(),
        total_member_patterns=("total", "nacional"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="INFORMAL",
                phrases=("informal", "empleo informal", "informalidad"),
            ),
            QueryTriggerRule(
                canonical_value="FORMAL",
                phrases=("formal", "empleo formal", "formalidad"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="canasta",
        description="Tipo de canasta (básica, alimentaria)",
        synset_domain="facet_canasta",
        known_dimension_ids=frozenset(),
        dimension_name_patterns=("canasta", "alimentos", "bienes"),
        member_value_patterns={
            "ALIMENTOS": (
                "alimentos y bebidas",
                "alimentos",
                "comida",
                "alimentos y bebidas no alcoholicas",
            ),
            "BASICA": ("canasta basica", "cba", "linea basica"),
        },
        implicit_aggregate_values=frozenset(),
        total_member_patterns=("total", "general"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="ALIMENTOS",
                phrases=("canasta basica de alimentos", "cba", "alimentos"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="rubro",
        description="Rubro o componente del gasto / IPC",
        synset_domain="facet_rubro",
        known_dimension_ids=frozenset(),
        dimension_name_patterns=("rubro", "grupo de gasto", "componente", "division"),
        member_value_patterns={
            "GENERAL": ("general", "indice general", "total"),
            "ALIMENTOS": ("alimentos", "alimentos y bebidas"),
        },
        implicit_aggregate_values=frozenset(),
        total_member_patterns=("general", "total"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="GENERAL",
                phrases=("rubro general", "total rubro"),
            ),
        ),
    ),
    FacetDefinition(
        facet_key="moneda",
        description="Unidad monetaria o de valuación",
        synset_domain="facet_moneda",
        known_dimension_ids=frozenset(),
        dimension_name_patterns=("moneda", "precios", "unidad"),
        member_value_patterns={
            "DOLARES_CONSTANTES": (
                "dolares a precios constantes",
                "dolares constantes",
                "precios constantes",
                "dolares",
            ),
            "MONEDA_NACIONAL": ("moneda nacional", "moneda local"),
        },
        implicit_aggregate_values=frozenset(),
        total_member_patterns=("moneda nacional", "total"),
        query_triggers=(),
    ),
    FacetDefinition(
        facet_key="actividad",
        description="Sector de actividad económica o rama",
        synset_domain="facet_actividad",
        known_dimension_ids=frozenset(),
        dimension_name_patterns=("actividad", "rama", "sector", "actividad economica"),
        member_value_patterns={
            "PUBLICO": ("publico", "sector publico", "gobierno"),
            "PRIVADO": ("privado", "sector privado"),
            "AGRICULTURA": ("agricultura", "agropecuario", "sector primario"),
            "INDUSTRIA": ("industria", "manufactura", "sector secundario"),
            "SERVICIOS": ("servicios", "sector terciario"),
        },
        implicit_aggregate_values=frozenset(),
        total_member_patterns=("total", "todas las actividades"),
        query_triggers=(
            QueryTriggerRule(
                canonical_value="AGRICULTURA",
                phrases=("sector agropecuario", "sector agricola", "rama agropecuaria", "rama agricola"),
            ),
            QueryTriggerRule(
                canonical_value="INDUSTRIA",
                phrases=("sector manufacturero", "sector industrial", "rama manufacturera", "rama industrial"),
            ),
            QueryTriggerRule(
                canonical_value="SERVICIOS",
                phrases=("sector servicios", "rama servicios"),
            ),
        ),
    ),
]

DEFAULT_FACET_ONTOLOGY = FacetOntology(DEFAULT_FACETS)


def get_default_facet_ontology() -> FacetOntology:
    """Return the default CEPALSTAT declarative facet ontology."""
    return DEFAULT_FACET_ONTOLOGY
