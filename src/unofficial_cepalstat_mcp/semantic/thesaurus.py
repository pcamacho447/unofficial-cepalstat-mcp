"""Declarative thesaurus engine for Latin American socioeconomic vocabulary and econometrics polarities."""

import re
import unicodedata
from enum import Enum
from functools import lru_cache

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
            if term not in clean:
                continue
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
            if synset.canonical_id in seen_canonical_ids or term not in clean:
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
            if term_clean not in clean:
                continue
            m = pattern.search(clean)
            if m:
                term_detected = rule.positive_term if is_positive else rule.negative_term
                opposite = rule.negative_term if is_positive else rule.positive_term
                sign = rule.positive_sign if is_positive else rule.negative_sign
                if is_positive and rule.target_indicator_positive is not None:
                    target_id = rule.target_indicator_positive
                elif not is_positive and rule.target_indicator_negative is not None:
                    target_id = rule.target_indicator_negative
                else:
                    target_id = rule.canonical_indicator_id
                return PolarityResolution(
                    polarity_type=rule.polarity_type,
                    term_detected=term_detected,
                    canonical_opposite=opposite,
                    canonical_indicator_id=target_id,
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
        canonical_term="total nacional",
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
    # facet_etnia
    Synset(
        canonical_id="ETNICO_TOTAL",
        domain="facet_etnia",
        canonical_term="etnica",
        synonyms=[
            "etnica",
            "etnico",
            "etnicas",
            "etnicos",
            "etnia",
            "etnias",
            "autoidentificacion etnica",
            "autoidentificacion etnico-racial",
            "origen etnico",
        ],
    ),
    Synset(
        canonical_id="INDIGENA",
        domain="facet_etnia",
        canonical_term="indigena",
        synonyms=[
            "indigena",
            "indigenas",
            "pueblos indigenas",
            "originarios",
            "pueblos originarios",
            "poblacion indigena",
        ],
    ),
    Synset(
        canonical_id="AFRODESCENDIENTE",
        domain="facet_etnia",
        canonical_term="afrodescendiente",
        synonyms=[
            "afrodescendiente",
            "afrodescendientes",
            "afro",
            "afrolatino",
            "afrolatinos",
            "afrolatina",
            "afrolatinas",
            "negros",
        ],
    ),
    Synset(
        canonical_id="NO_INDIGENA",
        domain="facet_etnia",
        canonical_term="no indigena",
        synonyms=[
            "no indigena",
            "no indigena ni afrodescendiente",
            "blancos y mestizos",
        ],
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


DEFAULT_ANTONYM_RULES: list[AntonymRule] = [
    # 1. State Inversion (Mercado laboral: Ocupación vs Desocupación / Desempleo / Paro)
    AntonymRule(
        rule_id="LABOR_OCUPACION_DESOCUPACION",
        positive_term="ocupacion",
        negative_term="desocupacion",
        polarity_type=PolarityType.STATE_INVERSION,
        canonical_indicator_id=127,
        target_indicator_positive=5097,
        target_indicator_negative=127,
        explanation="Inversión de estado entre tasa de ocupación (5097) y tasa de desocupación (127).",
    ),
    AntonymRule(
        rule_id="LABOR_OCUPACION_DESEMPLEO",
        positive_term="ocupacion",
        negative_term="desempleo",
        polarity_type=PolarityType.STATE_INVERSION,
        canonical_indicator_id=127,
        target_indicator_positive=5097,
        target_indicator_negative=127,
        explanation="Inversión de estado entre tasa de ocupación (5097) y tasa de desempleo (127).",
    ),
    AntonymRule(
        rule_id="LABOR_EMPLEO_PARO",
        positive_term="empleo",
        negative_term="paro",
        polarity_type=PolarityType.STATE_INVERSION,
        canonical_indicator_id=127,
        target_indicator_positive=5097,
        target_indicator_negative=127,
        explanation="Inversión de estado entre empleo (5097) y paro laboral (127).",
    ),
    AntonymRule(
        rule_id="LABOR_OCUPADOS_DESOCUPADOS",
        positive_term="ocupados",
        negative_term="desocupados",
        polarity_type=PolarityType.STATE_INVERSION,
        canonical_indicator_id=127,
        target_indicator_positive=5097,
        target_indicator_negative=127,
        explanation="Inversión de estado entre personas ocupadas (5097) y desocupadas (127).",
    ),
    AntonymRule(
        rule_id="LABOR_EMPLEADOS_DESEMPLEADOS",
        positive_term="empleados",
        negative_term="desempleados",
        polarity_type=PolarityType.STATE_INVERSION,
        canonical_indicator_id=127,
        target_indicator_positive=5097,
        target_indicator_negative=127,
        explanation="Inversión de estado entre personas empleadas (5097) y desempleadas (127).",
    ),

    # 2. Accounting Sign (Balanza de Pagos y Finanzas Públicas: Superávit vs Déficit)
    AntonymRule(
        rule_id="CURRENT_ACCOUNT_BALANCE_EN",
        positive_term="superavit en cuenta corriente",
        negative_term="deficit en cuenta corriente",
        polarity_type=PolarityType.ACCOUNTING_SIGN,
        canonical_indicator_id=1243,
        positive_sign=ExpectedSign.POSITIVE,
        negative_sign=ExpectedSign.NEGATIVE,
        explanation="Signo contable de balanza de pagos en Cuenta Corriente (1243): superávit positivo, déficit negativo.",
    ),
    AntonymRule(
        rule_id="CURRENT_ACCOUNT_BALANCE_DE",
        positive_term="superavit de cuenta corriente",
        negative_term="deficit de cuenta corriente",
        polarity_type=PolarityType.ACCOUNTING_SIGN,
        canonical_indicator_id=1243,
        positive_sign=ExpectedSign.POSITIVE,
        negative_sign=ExpectedSign.NEGATIVE,
        explanation="Signo contable de balanza de pagos en Cuenta Corriente (1243): superávit positivo, déficit negativo.",
    ),
    AntonymRule(
        rule_id="CURRENT_ACCOUNT_BALANCE_SHORT",
        positive_term="superavit cuenta corriente",
        negative_term="deficit cuenta corriente",
        polarity_type=PolarityType.ACCOUNTING_SIGN,
        canonical_indicator_id=1243,
        positive_sign=ExpectedSign.POSITIVE,
        negative_sign=ExpectedSign.NEGATIVE,
        explanation="Signo contable de balanza de pagos en Cuenta Corriente (1243): superávit positivo, déficit negativo.",
    ),
    AntonymRule(
        rule_id="PRIMARY_BALANCE_SIGN_SPECIFIC",
        positive_term="superavit primario",
        negative_term="deficit primario",
        polarity_type=PolarityType.ACCOUNTING_SIGN,
        canonical_indicator_id=1241,
        positive_sign=ExpectedSign.POSITIVE,
        negative_sign=ExpectedSign.NEGATIVE,
        explanation="Signo contable de finanzas públicas en Balance Primario (1241): superávit positivo, déficit negativo.",
    ),
    AntonymRule(
        rule_id="FISCAL_BALANCE_SIGN_SPECIFIC",
        positive_term="superavit fiscal",
        negative_term="deficit fiscal",
        polarity_type=PolarityType.ACCOUNTING_SIGN,
        canonical_indicator_id=1241,
        positive_sign=ExpectedSign.POSITIVE,
        negative_sign=ExpectedSign.NEGATIVE,
        explanation="Signo contable de finanzas públicas en Balance Fiscal / Primario (1241): superávit positivo, déficit negativo.",
    ),
    AntonymRule(
        rule_id="FISCAL_BALANCE_SIGN",
        positive_term="superavit",
        negative_term="deficit",
        polarity_type=PolarityType.ACCOUNTING_SIGN,
        canonical_indicator_id=1241,
        positive_sign=ExpectedSign.POSITIVE,
        negative_sign=ExpectedSign.NEGATIVE,
        explanation="Signo contable general en Balance Primario / Fiscal (1241): superávit positivo, déficit negativo.",
    ),
    AntonymRule(
        rule_id="TRADE_BALANCE_SIGN",
        positive_term="superavit comercial",
        negative_term="deficit comercial",
        polarity_type=PolarityType.ACCOUNTING_SIGN,
        canonical_indicator_id=None,
        positive_sign=ExpectedSign.POSITIVE,
        negative_sign=ExpectedSign.NEGATIVE,
        explanation="Signo contable de Balanza Comercial: superávit positivo (exportaciones > importaciones), déficit negativo.",
    ),

    # 3. Inclusion / Exclusion (LULUCF / UTCUTS: con LULUCF vs sin LULUCF)
    AntonymRule(
        rule_id="LULUCF_INCLUSION_EXCLUSION",
        positive_term="con lulucf",
        negative_term="sin lulucf",
        polarity_type=PolarityType.INCLUSION_EXCLUSION,
        canonical_indicator_id=5681,
        target_indicator_positive=5681,
        target_indicator_negative=5682,
        explanation="Inclusión/exclusión de Uso de la Tierra, Cambio de Uso de la Tierra y Silvicultura (LULUCF): con LULUCF neto (5681) vs sin LULUCF bruto (5682).",
    ),
    AntonymRule(
        rule_id="UTCUTS_INCLUSION_EXCLUSION",
        positive_term="con utcuts",
        negative_term="sin utcuts",
        polarity_type=PolarityType.INCLUSION_EXCLUSION,
        canonical_indicator_id=5681,
        target_indicator_positive=5681,
        target_indicator_negative=5682,
        explanation="Inclusión/exclusión de Uso de la Tierra, Cambio de Uso de la Tierra y Silvicultura (UTCUTS): con UTCUTS neto (5681) vs sin UTCUTS bruto (5682).",
    ),
    AntonymRule(
        rule_id="LULUCF_INCLUYENDO_EXCLUYENDO",
        positive_term="incluyendo lulucf",
        negative_term="excluyendo lulucf",
        polarity_type=PolarityType.INCLUSION_EXCLUSION,
        canonical_indicator_id=5681,
        target_indicator_positive=5681,
        target_indicator_negative=5682,
        explanation="Inclusión/exclusión de LULUCF en emisiones de GEI: con LULUCF (5681) vs sin LULUCF (5682).",
    ),
    AntonymRule(
        rule_id="UTCUTS_INCLUYENDO_EXCLUYENDO",
        positive_term="incluyendo utcuts",
        negative_term="excluyendo utcuts",
        polarity_type=PolarityType.INCLUSION_EXCLUSION,
        canonical_indicator_id=5681,
        target_indicator_positive=5681,
        target_indicator_negative=5682,
        explanation="Inclusión/exclusión de UTCUTS en emisiones de GEI: con UTCUTS (5681) vs sin UTCUTS (5682).",
    ),

    # 4. Facet Complement (Formal vs Informal, Urbano vs Rural)
    AntonymRule(
        rule_id="FACET_FORMAL_INFORMAL_EMPLEO",
        positive_term="empleo formal",
        negative_term="empleo informal",
        polarity_type=PolarityType.FACET_COMPLEMENT,
        explanation="Complementariedad dimensional en la faceta formalidad laboral (empleo formal vs empleo informal).",
    ),
    AntonymRule(
        rule_id="FACET_FORMAL_INFORMAL_TRABAJO",
        positive_term="trabajo formal",
        negative_term="trabajo informal",
        polarity_type=PolarityType.FACET_COMPLEMENT,
        explanation="Complementariedad dimensional en la faceta formalidad laboral (trabajo formal vs trabajo informal).",
    ),
    AntonymRule(
        rule_id="FACET_FORMAL_INFORMAL",
        positive_term="formal",
        negative_term="informal",
        polarity_type=PolarityType.FACET_COMPLEMENT,
        explanation="Complementariedad dimensional en la faceta formalidad laboral (formal vs informal).",
    ),
    AntonymRule(
        rule_id="FACET_URBANO_RURAL_ZONA",
        positive_term="zona urbana",
        negative_term="zona rural",
        polarity_type=PolarityType.FACET_COMPLEMENT,
        explanation="Complementariedad dimensional en la faceta área geográfica (zona urbana vs zona rural).",
    ),
    AntonymRule(
        rule_id="FACET_URBANO_RURAL_AREA",
        positive_term="area urbana",
        negative_term="area rural",
        polarity_type=PolarityType.FACET_COMPLEMENT,
        explanation="Complementariedad dimensional en la faceta área geográfica (área urbana vs área rural).",
    ),
    AntonymRule(
        rule_id="FACET_URBANO_RURAL",
        positive_term="urbano",
        negative_term="rural",
        polarity_type=PolarityType.FACET_COMPLEMENT,
        explanation="Complementariedad dimensional en la faceta área geográfica (urbano vs rural).",
    ),
]


@lru_cache(maxsize=1)
def get_default_thesaurus() -> Thesaurus:
    """Return preloaded default Thesaurus catalogue for Latin American socioeconomic vocabulary."""
    thesaurus = Thesaurus()
    for synset in DEFAULT_CANONICAL_SYNSETS:
        thesaurus.register_synset(synset)
    for rule in DEFAULT_ANTONYM_RULES:
        thesaurus.register_antonym_rule(rule)
    return thesaurus

