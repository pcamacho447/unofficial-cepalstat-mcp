"""Declarative thesaurus engine for Latin American socioeconomic vocabulary and econometrics polarities."""

from enum import Enum
from functools import lru_cache
import re
import unicodedata
from pydantic import BaseModel, Field


def strip_accents(text: str) -> str:
    """Normalize string to lowercase and strip diacritics."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


class PolarityType(str, Enum):
    """Econometric and dimensional polarity classifications."""

    STATE_INVERSION = "STATE_INVERSION"          # Ocupación vs Desocupación
    ACCOUNTING_SIGN = "ACCOUNTING_SIGN"          # Superávit vs Déficit
    INCLUSION_EXCLUSION = "INCLUSION_EXCLUSION"  # Con LULUCF vs Sin LULUCF
    FACET_COMPLEMENT = "FACET_COMPLEMENT"        # Formal vs Informal, Urbano vs Rural


class ExpectedSign(str, Enum):
    """Expected mathematical/economic sign for accounting indicators."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    UNSPECIFIED = "UNSPECIFIED"


class PolarityResolution(BaseModel):
    """Traceable polarity determination extracted from query terms."""

    polarity_type: PolarityType
    term_detected: str
    canonical_opposite: str
    canonical_indicator_id: int | None = None
    expected_sign: ExpectedSign = ExpectedSign.UNSPECIFIED
    explanation: str = ""


class Synset(BaseModel):
    """Equivalence class of synonyms and regionalisms for a domain facet or concept."""

    canonical_id: str
    domain: str
    canonical_term: str
    synonyms: list[str] = Field(default_factory=list)
    regional_tags: dict[str, list[str]] = Field(default_factory=dict)


class AntonymRule(BaseModel):
    """Rule defining opposite terms and their econometric implications."""

    rule_id: str
    positive_term: str
    negative_term: str
    polarity_type: PolarityType
    canonical_indicator_id: int | None = None
    target_indicator_positive: int | None = None
    target_indicator_negative: int | None = None
    positive_sign: ExpectedSign = ExpectedSign.UNSPECIFIED
    negative_sign: ExpectedSign = ExpectedSign.UNSPECIFIED
    explanation: str = ""


class SynsetMatch(BaseModel):
    """Result of a successful synset lookup in a query."""

    canonical_id: str
    domain: str
    matched_term: str
    start_pos: int
    end_pos: int


class Thesaurus:
    """Declarative thesaurus engine for Latin American socioeconomic vocabulary."""

    def __init__(self) -> None:
        self._synsets: dict[str, list[Synset]] = {}  # domain -> list[Synset]
        self._compiled_synsets: dict[str, list[tuple[Synset, str, re.Pattern[str]]]] = {}
        self._antonyms: list[AntonymRule] = []
        self._compiled_antonyms: list[tuple[AntonymRule, bool, str, re.Pattern[str]]] = []

    @property
    def synsets(self) -> dict[str, list[Synset]]:
        """Dictionary of registered synsets by domain."""
        return self._synsets

    @property
    def antonyms(self) -> list[AntonymRule]:
        """List of registered antonym rules."""
        return self._antonyms

    def register_synset(self, synset: Synset) -> None:
        """Register a synset and precompile its regex patterns with word boundaries."""
        clean_synset = Synset(
            canonical_id=synset.canonical_id,
            domain=synset.domain,
            canonical_term=synset.canonical_term,
            synonyms=[strip_accents(s) for s in synset.synonyms],
            regional_tags={k: [strip_accents(s) for s in v] for k, v in synset.regional_tags.items()},
        )
        self._synsets.setdefault(clean_synset.domain, []).append(clean_synset)

        compiled_list = self._compiled_synsets.setdefault(clean_synset.domain, [])
        all_terms = set(clean_synset.synonyms)
        for tags in clean_synset.regional_tags.values():
            all_terms.update(tags)
        if clean_synset.canonical_term:
            all_terms.add(strip_accents(clean_synset.canonical_term))

        for term in all_terms:
            if not term.strip():
                continue
            pattern = re.compile(r"\b" + re.escape(term) + r"\b")
            compiled_list.append((clean_synset, term, pattern))

        # Re-sort descending by term length to ensure longer phrases match first
        compiled_list.sort(key=lambda item: len(item[1]), reverse=True)

    def register_antonym_rule(self, rule: AntonymRule) -> None:
        """Register an antonym rule and precompile word-bounded regex patterns."""
        self._antonyms.append(rule)
        pos_clean = strip_accents(rule.positive_term)
        neg_clean = strip_accents(rule.negative_term)

        if pos_clean.strip():
            pat_pos = re.compile(r"\b" + re.escape(pos_clean) + r"\b")
            self._compiled_antonyms.append((rule, True, pos_clean, pat_pos))

        if neg_clean.strip():
            pat_neg = re.compile(r"\b" + re.escape(neg_clean) + r"\b")
            self._compiled_antonyms.append((rule, False, neg_clean, pat_neg))

        # Re-sort descending by term length
        self._compiled_antonyms.sort(key=lambda item: len(item[2]), reverse=True)

    def match_synset(self, domain: str, query: str) -> SynsetMatch | None:
        """Match the first synset in the specified domain with word boundary protection."""
        clean = strip_accents(query)
        compiled_list = self._compiled_synsets.get(domain, [])
        for synset, term, pattern in compiled_list:
            m = pattern.search(clean)
            if m:
                return SynsetMatch(
                    canonical_id=synset.canonical_id,
                    domain=synset.domain,
                    matched_term=term,
                    start_pos=m.start(),
                    end_pos=m.end(),
                )
        return None

    def match_all_synsets(self, domain: str, query: str) -> list[SynsetMatch]:
        """Find all distinct synsets matching within the specified domain."""
        clean = strip_accents(query)
        matches: list[SynsetMatch] = []
        seen_canonical_ids: set[str] = set()
        compiled_list = self._compiled_synsets.get(domain, [])
        for synset, term, pattern in compiled_list:
            if synset.canonical_id in seen_canonical_ids:
                continue
            m = pattern.search(clean)
            if m:
                matches.append(
                    SynsetMatch(
                        canonical_id=synset.canonical_id,
                        domain=synset.domain,
                        matched_term=term,
                        start_pos=m.start(),
                        end_pos=m.end(),
                    )
                )
                seen_canonical_ids.add(synset.canonical_id)
        return matches

    def resolve_polarity(self, query: str) -> PolarityResolution | None:
        """Detect antonym and polarity signals in a query string."""
        clean = strip_accents(query)
        for rule, is_positive, term_clean, pattern in self._compiled_antonyms:
            m = pattern.search(clean)
            if m:
                term_detected = rule.positive_term if is_positive else rule.negative_term
                opposite = rule.negative_term if is_positive else rule.positive_term
                sign = rule.positive_sign if is_positive else rule.negative_sign
                return PolarityResolution(
                    polarity_type=rule.polarity_type,
                    term_detected=term_detected,
                    canonical_opposite=opposite,
                    canonical_indicator_id=rule.canonical_indicator_id,
                    expected_sign=sign,
                    explanation=rule.explanation,
                )
        return None


DEFAULT_CANONICAL_SYNSETS: list[Synset] = [
    # facet_canasta
    Synset(
        canonical_id="CANASTA_ALIMENTOS",
        domain="facet_canasta",
        canonical_term="canasta basica de alimentos",
        synonyms=["morfi", "corrientazo", "alimentos", "comida", "canasta basica de alimentos", "carestia de comida"],
        regional_tags={"COL": ["corrientazo"], "ARG": ["morfi"]},
    ),
    Synset(
        canonical_id="CANASTA_COMBUSTIBLES",
        domain="facet_canasta",
        canonical_term="combustibles y energia",
        synonyms=["bencina", "nafta", "gasolina", "diesel", "gasoil", "electricidad", "combustibles", "energia", "transporte"],
        regional_tags={"CHL": ["bencina"], "ARG": ["nafta", "gasoil"], "COL": ["gasolina"]},
    ),
    # facet_area
    Synset(
        canonical_id="RURAL",
        domain="facet_area",
        canonical_term="rural",
        synonyms=["campo", "el campo", "zona rural", "area rural"],
    ),
    Synset(
        canonical_id="URBANO",
        domain="facet_area",
        canonical_term="urbano",
        synonyms=["ciudades", "ciudad", "villas", "zona urbana", "area urbana"],
    ),
    Synset(
        canonical_id="NACIONAL",
        domain="facet_area",
        canonical_term="nacional",
        synonyms=["todo el pais", "nivel nacional", "area nacional", "total nacional"],
    ),
    # facet_sexo
    Synset(
        canonical_id="FEMENINO",
        domain="facet_sexo",
        canonical_term="mujeres",
        synonyms=["mujeres", "chicas", "pibas", "femenina", "femenino", "mujer"],
        regional_tags={"ARG": ["pibas"]},
    ),
    Synset(
        canonical_id="MASCULINO",
        domain="facet_sexo",
        canonical_term="hombres",
        synonyms=["hombres", "chicos", "pibes", "masculino", "varones", "hombre"],
        regional_tags={"ARG": ["pibes"]},
    ),
    Synset(
        canonical_id="AMBOS_SEXOS",
        domain="facet_sexo",
        canonical_term="ambos sexos",
        synonyms=["hombres y mujeres", "ambos sexos"],
    ),
    # facet_edad
    Synset(
        canonical_id="INFANCIA",
        domain="facet_edad",
        canonical_term="infancia",
        synonyms=["ninos", "ninas", "infancia", "0 a 14", "infantil"],
    ),
    Synset(
        canonical_id="JUVENTUD",
        domain="facet_edad",
        canonical_term="juventud",
        synonyms=["cabros", "pibes", "chavos", "chavas", "jovenes", "juventud", "15 a 24", "juvenil"],
        regional_tags={"CHL": ["cabros"], "MEX": ["chavos", "chavas"], "ARG": ["pibes"]},
    ),
    Synset(
        canonical_id="ADULTOS_MAYORES",
        domain="facet_edad",
        canonical_term="adultos mayores",
        synonyms=["tercera edad", "abuelos", "ancianos", "adultos mayores", "65 y mas"],
    ),
    # facet_severidad
    Synset(
        canonical_id="POBREZA_EXTREMA",
        domain="facet_severidad",
        canonical_term="pobreza extrema",
        synonyms=["extrema", "indigencia", "indigente", "miseria"],
    ),
    Synset(
        canonical_id="POBREZA_TOTAL",
        domain="facet_severidad",
        canonical_term="pobreza total",
        synonyms=["pobreza", "pobres", "pobreza total"],
    ),
    # facet_formalidad
    Synset(
        canonical_id="INFORMAL",
        domain="facet_formalidad",
        canonical_term="informal",
        synonyms=["en negro", "informal", "informalidad", "chamba informal", "rebusque"],
        regional_tags={"ARG": ["en negro"], "MEX": ["chamba informal"], "COL": ["rebusque"]},
    ),
    Synset(
        canonical_id="FORMAL",
        domain="facet_formalidad",
        canonical_term="formal",
        synonyms=["en blanco", "formal", "formalidad", "empleo formal"],
        regional_tags={"ARG": ["en blanco"]},
    ),
    # concept_income
    Synset(
        canonical_id="SALARIO_MINIMO",
        domain="concept_income",
        canonical_term="salario minimo",
        synonyms=["plata minima", "salario minimo", "sueldo minimo", "sueldo basico", "salario de ley", "minimo por ley"],
    ),
    Synset(
        canonical_id="SALARIO_MEDIO",
        domain="concept_income",
        canonical_term="salario medio",
        synonyms=["salario medio", "sueldo medio", "salario promedio", "sueldo promedio", "remuneracion media", "laburantes"],
        regional_tags={"ARG": ["laburantes"]},
    ),
    Synset(
        canonical_id="INGRESO_HOGAR_PER_CAPITA",
        domain="concept_income",
        canonical_term="ingreso per capita de los hogares",
        synonyms=["ingreso por cabeza", "ingreso de los hogares", "ingreso familiar", "per capita de los hogares"],
    ),
    Synset(
        canonical_id="SLANG_INCOME_AMBIGUOUS",
        domain="concept_income",
        canonical_term="ingreso o remuneracion",
        synonyms=["guita", "plata", "lana", "lucas", "sueldo", "salario", "remuneraciones"],
        regional_tags={"ARG": ["guita"], "MEX": ["lana"], "CHL": ["lucas"], "COL": ["plata"]},
    ),
    # concept_labor
    Synset(
        canonical_id="EMPLEO_GENERAL",
        domain="concept_labor",
        canonical_term="empleo y mercado laboral",
        synonyms=["chamba", "pega", "laburo", "camello", "empleo", "trabajo", "desocupacion", "desempleo", "paro"],
        regional_tags={"MEX": ["chamba"], "CHL": ["pega"], "ARG": ["laburo"], "COL": ["camello"]},
    ),
    # concept_macro
    Synset(
        canonical_id="PIB_GENERAL",
        domain="concept_macro",
        canonical_term="producto interno bruto",
        synonyms=["pib", "producto interno bruto", "actividad economica", "crecimiento economico"],
    ),
    Synset(
        canonical_id="IPC_GENERAL",
        domain="concept_macro",
        canonical_term="indice de precios al consumidor",
        synonyms=["inflacion", "tasa de inflacion", "ipc", "costo de vida", "carestia", "aumento de precios"],
    ),
]


@lru_cache(maxsize=1)
def get_default_thesaurus() -> Thesaurus:
    """Return preloaded default Thesaurus catalogue for Latin American socioeconomic vocabulary."""
    thesaurus = Thesaurus()
    for synset in DEFAULT_CANONICAL_SYNSETS:
        thesaurus.register_synset(synset)
    return thesaurus

