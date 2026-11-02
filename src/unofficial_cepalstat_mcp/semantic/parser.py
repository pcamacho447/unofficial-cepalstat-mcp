"""Lexical and conceptual query parser for the CEPALSTAT semantic engine."""

import re
import unicodedata

from pydantic import BaseModel, Field

from unofficial_cepalstat_mcp.semantic.concept_ontology import (
    DEFAULT_CONCEPT_ONTOLOGY,
    ConceptOntology,
)
from unofficial_cepalstat_mcp.semantic.facet_ontology import (
    DEFAULT_FACET_ONTOLOGY,
    FacetOntology,
)
from unofficial_cepalstat_mcp.semantic.thesaurus import (
    PolarityResolution,
    Thesaurus,
    get_default_thesaurus,
)


def strip_accents(text: str) -> str:
    """Normalize string to lowercase and strip diacritics."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


COUNTRY_LEXICON: dict[str, str] = {
    # Regional aggregates
    "america latina y el caribe": "ALC",
    "america latina": "ALC",
    "alc": "ALC",
    "america del sur": "SUD",
    "centroamerica": "CAM",
    "el caribe": "CAR",
    "brasil": "BRA",
    "brazil": "BRA",
    "colombia": "COL",
    "chile": "CHL",
    "mexico": "MEX",
    "argentina": "ARG",
    "uruguay": "URY",
    "costa rica": "CRI",
    "peru": "PER",
    "ecuador": "ECU",
    "bolivia": "BOL",
    "panama": "PAN",
    "paraguay": "PRY",
    "honduras": "HND",
    "guatemala": "GTM",
    "el salvador": "SLV",
    "nicaragua": "NIC",
    "republica dominicana": "DOM",
    "venezuela": "VEN",
    "cuba": "CUB",
    "haiti": "HTI",
    "jamaica": "JAM",
    "trinidad y tobago": "TTO",
    "bahamas": "BHS",
    "barbados": "BRB",
    "belice": "BLZ",
    "guyana": "GUY",
    "surinam": "SUR",
    "lima": "PER",
    # Demonyms (gentilicios latinoamericanos)
    "brasileno": "BRA",
    "brasilena": "BRA",
    "brasilenos": "BRA",
    "brasilenas": "BRA",
    "colombiano": "COL",
    "colombiana": "COL",
    "colombianos": "COL",
    "colombianas": "COL",
    "chileno": "CHL",
    "chilena": "CHL",
    "chilenos": "CHL",
    "chilenas": "CHL",
    "mexicano": "MEX",
    "mexicana": "MEX",
    "mexicanos": "MEX",
    "mexicanas": "MEX",
    "argentino": "ARG",
    "argentinos": "ARG",
    "argentinas": "ARG",
    "uruguayo": "URY",
    "uruguaya": "URY",
    "uruguayos": "URY",
    "uruguayas": "URY",
    "costarricense": "CRI",
    "costarricenses": "CRI",
    "peruano": "PER",
    "peruana": "PER",
    "peruanos": "PER",
    "peruanas": "PER",
    "ecuatoriano": "ECU",
    "ecuatoriana": "ECU",
    "ecuatorianos": "ECU",
    "ecuatorianas": "ECU",
    "boliviano": "BOL",
    "boliviana": "BOL",
    "bolivianos": "BOL",
    "bolivianas": "BOL",
    "panameno": "PAN",
    "panamena": "PAN",
    "panamenos": "PAN",
    "panamenas": "PAN",
    "paraguayo": "PRY",
    "paraguaya": "PRY",
    "paraguayos": "PRY",
    "paraguayas": "PRY",
    "hondureno": "HND",
    "hondurena": "HND",
    "hondurenos": "HND",
    "hondurenas": "HND",
    "guatemalteco": "GTM",
    "guatemalteca": "GTM",
    "guatemaltecos": "GTM",
    "guatemaltecas": "GTM",
    "salvadoreno": "SLV",
    "salvadorena": "SLV",
    "salvadorenos": "SLV",
    "salvadorenas": "SLV",
    "nicaraguense": "NIC",
    "nicaraguenses": "NIC",
    "dominicano": "DOM",
    "dominicana": "DOM",
    "dominicanos": "DOM",
    "dominicanas": "DOM",
    "venezolano": "VEN",
    "venezolana": "VEN",
    "venezolanos": "VEN",
    "venezolanas": "VEN",
    "cubano": "CUB",
    "cubana": "CUB",
    "cubanos": "CUB",
    "cubanas": "CUB",
    "haitiano": "HTI",
    "haitiana": "HTI",
    "haitianos": "HTI",
    "haitianas": "HTI",
}

_SORTED_COUNTRY_LEXICON: tuple[tuple[str, str], ...] = tuple(
    sorted(COUNTRY_LEXICON.items(), key=lambda x: len(x[0]), reverse=True)
)

COUNTRY_NAMES: dict[str, str] = {
    "ALC": "América Latina y el Caribe",
    "SUD": "América del Sur",
    "CAM": "Centroamérica",
    "CAR": "El Caribe",
    "BRA": "Brasil",
    "COL": "Colombia",
    "CHL": "Chile",
    "MEX": "México",
    "ARG": "Argentina",
    "URY": "Uruguay",
    "CRI": "Costa Rica",
    "PER": "Perú",
    "ECU": "Ecuador",
    "BOL": "Bolivia",
    "PAN": "Panamá",
    "PRY": "Paraguay",
    "HND": "Honduras",
    "GTM": "Guatemala",
    "SLV": "El Salvador",
    "NIC": "Nicaragua",
    "DOM": "República Dominicana",
    "VEN": "Venezuela",
    "CUB": "Cuba",
    "HTI": "Haití",
    "JAM": "Jamaica",
    "TTO": "Trinidad y Tobago",
    "BHS": "Bahamas",
    "BRB": "Barbados",
    "BLZ": "Belice",
    "GUY": "Guyana",
    "SUR": "Surinam",
}

NON_LAC_COUNTRY_NAMES: dict[str, str] = {
    "DEU": "Alemania",
    "ESP": "España",
    "FRA": "Francia",
    "ITA": "Italia",
    "GBR": "Reino Unido",
    "USA": "Estados Unidos",
    "CHN": "China",
    "JPN": "Japón",
    "CAN": "Canadá",
    "PRT": "Portugal",
    "AUS": "Australia",
    "RUS": "Rusia",
    "IND": "India",
}

NON_LAC_COUNTRIES: dict[str, str] = {
    "francia": "FRA",
    "espana": "ESP",
    "alemania": "DEU",
    "italia": "ITA",
    "reino unido": "GBR",
    "estados unidos": "USA",
    "eeuu": "USA",
    "china": "CHN",
    "japon": "JPN",
    "canada": "CAN",
    "portugal": "PRT",
    "australia": "AUS",
    "rusia": "RUS",
    "india": "IND",
}

_LAC_COUNTRY_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(re.escape(c) for c in sorted(COUNTRY_LEXICON.keys(), key=len, reverse=True))
    + r")\b"
)
_NON_LAC_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(re.escape(c) for c in sorted(NON_LAC_COUNTRIES.keys(), key=len, reverse=True))
    + r")\b"
)


class ParsedIntent(BaseModel):
    """Normalized structured representation of a natural language query."""

    raw_query: str
    clean_query: str
    root_concept: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    country_codes: list[str] = Field(default_factory=list)
    country_names: list[str] = Field(default_factory=list)
    year: int | None = None
    years: list[int] = Field(default_factory=list)
    time_mode: str = "SINGLE"  # "SINGLE", "LIST", "RANGE", "RELATIVE_WINDOW"
    relative_window_size: int | None = None
    facets: dict[str, str] = Field(default_factory=dict)
    polarity_info: PolarityResolution | None = None
    is_ambiguous_measure: bool = False
    ambiguous_candidate: str | None = None
    unsupported_facet: str | None = None
    unknown_concept: bool = False
    period_out_of_range: bool = False
    unsupported_frequency: bool = False
    frequency: str = "ANUAL"
    unconsumed_tokens: list[str] = Field(default_factory=list)
    concept_tokens: list[str] = Field(default_factory=list)


_RE_REL_YEARS = re.compile(r"\bultimos?\s+(\d+)\s+anos?\b")
_RE_REL_DECADE = re.compile(r"\bultima\s+decada\b")
_RE_REL_QUINQUENNIUM = re.compile(r"\bultimo\s+quinquenio\b")
_RE_REL_TRIENNIUM = re.compile(r"\bultimo\s+trienio\b")

_RE_RANGE_A = re.compile(
    r"\b(?:del|desde|entre)\s+(?:el\s+)?(?:ano\s+)?(1\d{3}|20\d{2})\s+(?:al|a|hasta|y)\s+(?:el\s+)?(?:ano\s+)?(1\d{3}|20\d{2})\b"
)
_RE_RANGE_B = re.compile(
    r"\bde\s+(?:el\s+)?(?:ano\s+)?(1\d{3}|20\d{2})\s+(?:a|al|hasta)\s+(?:el\s+)?(?:ano\s+)?(1\d{3}|20\d{2})\b"
)
_RE_RANGE_C = re.compile(r"\b(1\d{3}|20\d{2})\s*[-–]\s*(1\d{3}|20\d{2})\b")

_RE_YEAR = re.compile(r"\b(1\d{3}|20\d{2})\b")
_RE_FALLBACK_YEAR = re.compile(r"\b(?:ano|el\s+ano)\s+(\d{1,4})\b")

SPANISH_STOPWORDS: frozenset[str] = frozenset(
    {
        # Grammatical articles and contractions
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "lo",
        "al",
        "del",
        # Prepositions
        "a",
        "ante",
        "bajo",
        "cabe",
        "con",
        "contra",
        "de",
        "desde",
        "durante",
        "en",
        "entre",
        "hacia",
        "hasta",
        "mediante",
        "para",
        "por",
        "segun",
        "sin",
        "so",
        "sobre",
        "tras",
        "versus",
        "vs",
        "frente",
        "per",
        # Conjunctions, negations and connectives
        "y",
        "e",
        "ni",
        "no",
        "o",
        "u",
        "pero",
        "mas",
        "sino",
        "aunque",
        "que",
        "como",
        "si",
        # Pronouns and inquiry words
        "cual",
        "cuales",
        "quien",
        "quienes",
        "donde",
        "cuando",
        "cuanto",
        "cuanta",
        "cuantos",
        "cuantas",
        "me",
        "te",
        "se",
        "nos",
        "os",
        "le",
        "les",
        # Demonstratives and possessives
        "este",
        "esta",
        "estos",
        "estas",
        "esto",
        "ese",
        "esa",
        "esos",
        "esas",
        "eso",
        "aquel",
        "aquella",
        "aquellos",
        "aquellas",
        "aquello",
        "mi",
        "mis",
        "tu",
        "tus",
        "su",
        "sus",
        "nuestro",
        "nuestra",
        "nuestros",
        "nuestras",
        # Inquiry verbs and conversational terms
        "dame",
        "dime",
        "quiero",
        "ver",
        "busca",
        "buscar",
        "buscame",
        "mostrar",
        "muestra",
        "muestrame",
        "consultar",
        "consulta",
        "obtener",
        "traer",
        "traeme",
        "saber",
        "conocer",
        "dar",
        "des",
        "decir",
        "revisar",
        "revisa",
        "deseo",
        "quisiera",
        "favor",
        "porfavor",
        "porfa",
        # Common verbs / copulas
        "es",
        "son",
        "fue",
        "fueron",
        "era",
        "eran",
        "ha",
        "han",
        "hay",
        "hubo",
        "habia",
        "esta",
        "estan",
        "estuvo",
        "estuvieron",
        "tener",
        "tiene",
        "tienen",
        "tenia",
        "tuvo",
        "ando",
        "anduvo",
        "entra",
        "entran",
        "entrado",
        "entron",
        "salen",
        "salieron",
        "cobra",
        "cobran",
        "crecio",
        # Generic statistical filler nouns, adjectives, and inquiry terms
        "saldo",
        "saldos",
        "comparacion",
        "comparaciones",
        "personas",
        "persona",
        "gente",
        # Generic statistical filler nouns and adjectives
        "tasa",
        "tasas",
        "nivel",
        "niveles",
        "indicador",
        "indicadores",
        "datos",
        "dato",
        "serie",
        "series",
        "cifra",
        "cifras",
        "estadistica",
        "estadisticas",
        "estimacion",
        "estimaciones",
        "valor",
        "valores",
        "indice",
        "indices",
        "ano",
        "anos",
        "trimestre",
        "trimestres",
        "mes",
        "meses",
        "periodo",
        "periodos",
        "promedio",
        "promedios",
        "medio",
        "medios",
        "media",
        "medias",
        "porcentaje",
        "porcentajes",
        "%",
        "oficial",
        "oficiales",
        "total",
        "totales",
        "agregado",
        "agregada",
        "agregados",
        "agregadas",
        "incidencia",
        "participacion",
        "proporcion",
        "evolucion",
        "desempeno",
        "variacion",
        "variaciones",
        "situacion",
        "medicion",
        "medida",
        "medidas",
        "registro",
        "registros",
        "historico",
        "historica",
        "historicos",
        "historicas",
        "reciente",
        "recientes",
        "actual",
        "actuales",
        "ultimo",
        "ultima",
        "ultimos",
        "ultimas",
        "nacional",
        "nacionales",
        "pais",
        "todo",
        "toda",
        "todos",
        "todas",
        "medido",
        "medidos",
        "calculado",
        "calculada",
        "relacion",
        "diferencia",
    }
)

CURRENCY_AND_UNIT_PHRASES: tuple[str, ...] = (
    "moneda nacional",
    "moneda local",
    "precios corrientes",
    "precios constantes",
    "dolares constantes",
    "dolares",
    "dolar",
    "pesos",
    "soles",
    "reales",
    "real",
    "fob/cif",
    "fob cif",
    "fob",
    "cif",
    "porcentaje del pib",
    "sobre el pib",
    "frente al pib",
    "como porcentaje del pib",
    "en porcentaje del pib",
    "porcentaje del pbi",
    "sobre el pbi",
    "frente al pbi",
    "como porcentaje del pbi",
    "en porcentaje del pbi",
)


class QueryParser:
    """Translates raw natural language queries into normalized conceptual intents."""

    def __init__(
        self,
        catalog_profile: str = "official_25",
        thesaurus: Thesaurus | None = None,
        ontology: FacetOntology | None = None,
        concept_ontology: ConceptOntology | None = None,
    ):
        self.catalog_profile = catalog_profile
        self.thesaurus = thesaurus or get_default_thesaurus()
        self.ontology = ontology or DEFAULT_FACET_ONTOLOGY
        self.concept_ontology = concept_ontology or DEFAULT_CONCEPT_ONTOLOGY

    def parse(self, query: str) -> ParsedIntent:
        clean = strip_accents(query)
        facets: dict[str, str] = {}
        consumed_phrases: list[str] = []
        intent = ParsedIntent(raw_query=query, clean_query=clean)
        intent.polarity_info = self.thesaurus.resolve_polarity(clean)
        if intent.polarity_info and intent.polarity_info.term_detected:
            consumed_phrases.append(strip_accents(intent.polarity_info.term_detected))

        for cur in CURRENCY_AND_UNIT_PHRASES:
            if cur in clean:
                consumed_phrases.append(cur)

        # ----------------------------------------------------
        # 1. Detection of Out-of-Scope / Unsupported cases
        # ----------------------------------------------------
        has_lac_country = bool(_LAC_COUNTRY_PATTERN.search(clean))
        if not has_lac_country:
            non_lac_match = _NON_LAC_PATTERN.search(clean)
            if non_lac_match:
                matched_str = non_lac_match.group(0)
                non_lac_code = NON_LAC_COUNTRIES[matched_str]
                intent.unsupported_facet = f"UNSUPPORTED_COUNTRY_NON_LAC_{non_lac_code}"
                intent.country_code = non_lac_code
                intent.country_name = NON_LAC_COUNTRY_NAMES.get(non_lac_code, matched_str.title())
                intent.country_codes = [non_lac_code]
                intent.country_names = [intent.country_name]

        if "lunar" in clean or "en la luna" in clean or "la luna" in clean:
            intent.unsupported_facet = "UNSUPPORTED_GEOGRAPHY_MOON"
            intent.unknown_concept = True
        elif "marte" in clean:
            intent.unsupported_facet = "UNSUPPORTED_GEOGRAPHY_MARS"
            intent.unknown_concept = True
        elif "atlantis" in clean:
            intent.unsupported_facet = "UNSUPPORTED_COUNTRY_ATLANTIS"
            intent.unknown_concept = True

        if "astronauta" in clean or "astronautas" in clean:
            intent.unsupported_facet = "UNSUPPORTED_SECTOR"

        if (
            "coeficiencia intelectual" in clean
            or "coeficiente intelectual" in clean
            or re.search(r"\biq\b", clean)
        ):
            intent.unsupported_facet = "UNSUPPORTED_FACET_IQ"

        if any(term in clean for term in ["milmillonarios", "forbes", "riqueza de los"]):
            intent.unsupported_facet = "UNSUPPORTED_DATASET_WEALTH_BILLIONAIRES"

        if any(term in clean for term in ["secreto", "espia", "espias"]):
            intent.unsupported_facet = "UNSUPPORTED_FACET_SECRET_DEFENSE"

        if any(term in clean for term in ["bitcoin", "criptomoneda", "criptomonedas"]):
            intent.unsupported_facet = "UNSUPPORTED_COMMODITY_BITCOIN"

        if any(term in clean for term in ["unicornio", "unicornios"]):
            intent.unsupported_facet = "UNSUPPORTED_FACET_UNICORNS"

        if any(term in clean for term in ["telepatia", "telequinesis"]):
            intent.unsupported_facet = "UNSUPPORTED_FACET_TELEPATHY"

        if any(
            term in clean
            for term in ["tipo de sangre", "tipos de sangre", "grupo sanguineo", "factor rh"]
        ):
            intent.unsupported_facet = "UNSUPPORTED_FACET_BLOOD_TYPE"

        if any(
            term in clean for term in ["religion", "religiones", "credo", "afiliacion religiosa"]
        ):
            intent.unsupported_facet = "UNSUPPORTED_FACET_RELIGION"

        if "trimestral" in clean and "gini" in clean:
            intent.unsupported_frequency = True

        if any(
            term in clean
            for term in [
                "por segundo",
                "minuto a minuto",
                "al minuto",
                "en tiempo real",
                "tiempo real",
            ]
        ):
            intent.unsupported_frequency = True
            intent.frequency = "REALTIME"
            for t in [
                "por segundo",
                "minuto a minuto",
                "al minuto",
                "en tiempo real",
                "tiempo real",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["diaria", "diario", "semana pasada"]):
            intent.unsupported_frequency = True
            intent.frequency = "DIARIA"
            for t in ["diaria", "diario", "semana pasada"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["por hora", "horaria", "horario"]):
            intent.unsupported_frequency = True
            intent.frequency = "HOURLY"
            for t in ["por hora", "horaria", "horario"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif "trimestral" in clean or "trimestre" in clean:
            intent.frequency = "TRIMESTRAL"
            if "trimestral" in clean:
                consumed_phrases.append("trimestral")
            if "trimestre" in clean:
                consumed_phrases.append("trimestre")
        elif "mensual" in clean:
            intent.frequency = "MENSUAL"
            consumed_phrases.append("mensual")
            if "pobreza" in clean:
                intent.unsupported_frequency = True
        elif "hoy" in clean:
            intent.unsupported_frequency = True
            intent.frequency = "REALTIME"
            consumed_phrases.append("hoy")

        if "anual" in clean:
            consumed_phrases.append("anual")
        if "anuales" in clean:
            consumed_phrases.append("anuales")
        if "interanual" in clean:
            consumed_phrases.append("interanual")

        # ----------------------------------------------------
        # 2. Extract Year & Range Check (Temporal Extraction)
        # ----------------------------------------------------
        temporal_start_idx = len(consumed_phrases)
        rel_match = _RE_REL_YEARS.search(clean)
        if rel_match:
            consumed_phrases.append(rel_match.group(0))
            intent.time_mode = "RELATIVE_WINDOW"
            intent.relative_window_size = int(rel_match.group(1))
            intent.year = None
            intent.years = []
        elif rel_dec := _RE_REL_DECADE.search(clean):
            consumed_phrases.append(rel_dec.group(0))
            intent.time_mode = "RELATIVE_WINDOW"
            intent.relative_window_size = 10
            intent.year = None
            intent.years = []
        elif rel_quinq := _RE_REL_QUINQUENNIUM.search(clean):
            consumed_phrases.append(rel_quinq.group(0))
            intent.time_mode = "RELATIVE_WINDOW"
            intent.relative_window_size = 5
            intent.year = None
            intent.years = []
        elif rel_tri := _RE_REL_TRIENNIUM.search(clean):
            consumed_phrases.append(rel_tri.group(0))
            intent.time_mode = "RELATIVE_WINDOW"
            intent.relative_window_size = 3
            intent.year = None
            intent.years = []
        else:
            range_match = _RE_RANGE_A.search(clean)
            if not range_match:
                range_match = _RE_RANGE_B.search(clean)
            if not range_match:
                range_match = _RE_RANGE_C.search(clean)

            if range_match:
                consumed_phrases.append(range_match.group(0))
                y1 = int(range_match.group(1))
                y2 = int(range_match.group(2))
                start_year = min(y1, y2)
                end_year = max(y1, y2)
                intent.time_mode = "RANGE"
                intent.years = list(range(start_year, end_year + 1))
                intent.year = end_year
                if any(y < 1950 or y > 2030 for y in intent.years):
                    intent.period_out_of_range = True
            else:
                for ym in _RE_YEAR.finditer(clean):
                    consumed_phrases.append(ym.group(0))
                found_years = [int(y) for y in _RE_YEAR.findall(clean)]
                unique_years = sorted(set(found_years))
                if len(unique_years) >= 2:
                    intent.time_mode = "LIST"
                    intent.years = unique_years
                    intent.year = max(unique_years)
                    if any(y < 1950 or y > 2030 for y in unique_years):
                        intent.period_out_of_range = True
                elif len(unique_years) == 1:
                    year_val = unique_years[0]
                    intent.time_mode = "SINGLE"
                    intent.year = year_val
                    intent.years = [year_val]
                    if year_val < 1950 or year_val > 2030:
                        intent.period_out_of_range = True
                else:
                    fallback_match = _RE_FALLBACK_YEAR.search(clean)
                    if fallback_match:
                        consumed_phrases.append(fallback_match.group(0))
                        year_val = int(fallback_match.group(1))
                        intent.time_mode = "SINGLE"
                        intent.year = year_val
                        intent.years = [year_val]
                        if year_val < 1950 or year_val > 2030:
                            intent.period_out_of_range = True

        # ----------------------------------------------------
        # 3. Extract Country (Single or Multi-Country in Query Order)
        # ----------------------------------------------------
        geo_start_idx = len(consumed_phrases)
        matched_spans: list[tuple[int, int, str, str]] = []
        for name, code in _SORTED_COUNTRY_LEXICON:
            if name not in clean:
                continue
            for m in re.finditer(r"\b" + re.escape(name) + r"\b", clean):
                s, e = m.start(), m.end()
                if any(not (e <= span_s or s >= span_e) for span_s, span_e, _, _ in matched_spans):
                    continue
                matched_spans.append((s, e, code, name))
                consumed_phrases.append(name)

        if matched_spans:
            matched_spans.sort(key=lambda item: item[0])
            seen_codes: set[str] = set()
            ordered_codes: list[str] = []
            for _, _, code, _ in matched_spans:
                if code not in seen_codes:
                    seen_codes.add(code)
                    ordered_codes.append(code)
            intent.country_codes = ordered_codes
            intent.country_names = [COUNTRY_NAMES[c] for c in ordered_codes]
            intent.country_code = ordered_codes[0]
            intent.country_name = COUNTRY_NAMES[ordered_codes[0]]

        # ----------------------------------------------------
        # 4. Extract Facets (with Regionalisms)
        # ----------------------------------------------------
        facet_start_idx = len(consumed_phrases)
        # Area
        if any(term in clean for term in ["urbano y rural", "urbana y rural"]):
            facets["area"] = "AREA_DESGLOSE"
            for t in ["urbano y rural", "urbana y rural"]:
                if t in clean:
                    consumed_phrases.append(t)
        else:
            area_match = self.thesaurus.match_synset("facet_area", clean)
            if area_match:
                facets["area"] = area_match.canonical_id
                consumed_phrases.append(area_match.matched_term)
            elif any(
                term in clean for term in ["el campo", "rural", "campo", "zona rural", "area rural"]
            ):
                facets["area"] = "RURAL"
                for t in ["el campo", "rural", "campo", "zona rural", "area rural"]:
                    if t in clean:
                        consumed_phrases.append(t)
            elif any(
                term in clean
                for term in [
                    "ciudades",
                    "urbano",
                    "ciudad",
                    "urbana",
                    "zona urbana",
                    "area urbana",
                    "villas",
                ]
            ):
                facets["area"] = "URBANO"
                for t in [
                    "ciudades",
                    "urbano",
                    "ciudad",
                    "urbana",
                    "zona urbana",
                    "area urbana",
                    "villas",
                ]:
                    if t in clean:
                        consumed_phrases.append(t)
            elif any(
                term in clean
                for term in ["area nacional", "total nacional", "todo el pais", "nivel nacional"]
            ):
                facets["area"] = "NACIONAL"
                for t in ["area nacional", "total nacional", "todo el pais", "nivel nacional"]:
                    if t in clean:
                        consumed_phrases.append(t)
        if "pobreza total" in clean and "area" not in facets:
            facets["area"] = "NACIONAL"
            consumed_phrases.append("pobreza total")

        # Sexo
        sexo_match = self.thesaurus.match_synset("facet_sexo", clean)
        if sexo_match:
            facets["sexo"] = sexo_match.canonical_id
            consumed_phrases.append(sexo_match.matched_term)
        elif any(
            term in clean
            for term in ["pibas", "chicas", "mujeres", "femenina", "femenino", "mujer"]
        ):
            facets["sexo"] = "FEMENINO"
            for t in ["pibas", "chicas", "mujeres", "femenina", "femenino", "mujer"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(
            term in clean
            for term in ["pibes", "chicos", "hombres", "masculino", "varones", "hombre"]
        ):
            facets["sexo"] = "MASCULINO"
            for t in ["pibes", "chicos", "hombres", "masculino", "varones", "hombre"]:
                if t in clean:
                    consumed_phrases.append(t)
        if "hombres y mujeres" in clean or "ambos sexos" in clean:
            facets["sexo"] = "AMBOS_SEXOS"
            if "hombres y mujeres" in clean:
                consumed_phrases.append("hombres y mujeres")
            if "ambos sexos" in clean:
                consumed_phrases.append("ambos sexos")

        # Edad (Check infancia before youth so 0 a 14 takes precedence)
        edad_matches = self.thesaurus.match_all_synsets("facet_edad", clean)
        if any(m.canonical_id == "INFANCIA" for m in edad_matches):
            facets["edad"] = "INFANCIA"
        elif edad_matches:
            facets["edad"] = edad_matches[0].canonical_id
        for edad_m in edad_matches:
            consumed_phrases.append(edad_m.matched_term)

        if any(term in clean for term in ["ninos", "ninas", "infancia", "0 a 14", "infantil"]):
            if "edad" not in facets:
                facets["edad"] = "INFANCIA"
            for t in ["ninos", "ninas", "infancia", "0 a 14", "infantil"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(
            term in clean
            for term in [
                "cabros",
                "pibes",
                "chavos",
                "chavas",
                "jovenes",
                "juventud",
                "15 a 24",
                "juvenil",
            ]
        ):
            if "edad" not in facets:
                facets["edad"] = "JUVENTUD"
            for t in [
                "cabros",
                "pibes",
                "chavos",
                "chavas",
                "jovenes",
                "juventud",
                "15 a 24",
                "juvenil",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(
            term in clean
            for term in ["tercera edad", "abuelos", "ancianos", "adultos mayores", "65 y mas"]
        ):
            if "edad" not in facets:
                facets["edad"] = "ADULTOS_MAYORES"
            for t in [
                "tercera edad",
                "abuelos",
                "ancianos",
                "adultos mayores",
                "65 y mas",
                "65 anos y mas",
                "65 anos",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
        if "pibas" in clean and any(
            term in clean for term in ["pobreza", "desempleo", "desocupacion", "paro"]
        ):
            facets["edad"] = "JUVENTUD"

        # Severidad de pobreza
        severidad_match = self.thesaurus.match_synset("facet_severidad", clean)
        if severidad_match:
            facets["severidad"] = severidad_match.canonical_id
            consumed_phrases.append(severidad_match.matched_term)
        elif any(term in clean for term in ["extrema", "indigencia", "indigente", "miseria"]):
            facets["severidad"] = "POBREZA_EXTREMA"
            for t in ["extrema", "indigencia", "indigente", "miseria"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif "pobreza" in clean:
            facets["severidad"] = "POBREZA_TOTAL"
            consumed_phrases.append("pobreza")

        # Formalidad laboral
        formalidad_match = self.thesaurus.match_synset("facet_formalidad", clean)
        if formalidad_match:
            facets["formalidad"] = formalidad_match.canonical_id
            consumed_phrases.append(formalidad_match.matched_term)
            if formalidad_match.canonical_id == "INFORMAL" and "pobreza" in clean:
                intent.unsupported_facet = "FORMALIDAD_LABORAL"
        elif any(
            term in clean for term in ["en negro", "informal", "informalidad", "chamba informal"]
        ):
            facets["formalidad"] = "INFORMAL"
            for t in ["en negro", "informal", "informalidad", "chamba informal"]:
                if t in clean:
                    consumed_phrases.append(t)
            if "pobreza" in clean:
                intent.unsupported_facet = "FORMALIDAD_LABORAL"

        # Estrato (Income distribution quintiles/deciles)
        for t in [
            "quintil 5 versus quintil 1",
            "q5 versus q1",
            "quintil 5 vs quintil 1",
            "primer quintil",
            "q1",
            "quintil 1",
            "quintil mas pobre",
            "los de abajo",
            "quinto quintil",
            "q5",
            "quintil 5",
            "20 por ciento mas rico",
            "decil 10",
            "decil mas rico",
            "los mas ricos",
            "decil 1",
            "decil mas pobre",
            "decil 1 mas vulnerable",
            "por quintiles",
            "los quintiles",
            "entre los quintiles",
            "entre quintiles",
            "quintiles",
            "quintil",
            "por deciles",
            "los deciles",
            "entre los deciles",
            "entre deciles",
            "deciles",
            "decil",
        ]:
            if t in clean:
                consumed_phrases.append(t)

        if any(
            term in clean
            for term in ["quintil 5 versus quintil 1", "q5 versus q1", "quintil 5 vs quintil 1"]
        ):
            facets["estrato"] = "RELACION_Q5_Q1"
        elif any(
            term in clean
            for term in ["primer quintil", "q1", "quintil 1", "quintil mas pobre", "los de abajo"]
        ):
            facets["estrato"] = "QUINTIL_1"
        elif any(
            term in clean
            for term in ["quinto quintil", "q5", "quintil 5", "20 por ciento mas rico"]
        ):
            facets["estrato"] = "QUINTIL_5"
        elif any(term in clean for term in ["decil 10", "decil mas rico", "los mas ricos"]):
            facets["estrato"] = "DECIL_10"
        elif any(
            term in clean for term in ["decil 1", "decil mas pobre", "decil 1 mas vulnerable"]
        ):
            facets["estrato"] = "DECIL_1"
        elif any(
            term in clean
            for term in [
                "por quintiles",
                "los quintiles",
                "entre los quintiles",
                "entre quintiles",
                "quintiles",
                "quintil",
            ]
        ):
            facets["estrato"] = "QUINTIL"
        elif any(
            term in clean
            for term in [
                "por deciles",
                "los deciles",
                "entre los deciles",
                "entre deciles",
                "deciles",
                "decil",
            ]
        ):
            facets["estrato"] = "DECIL"

        # Canasta alimentos & rubros
        canasta_match = self.thesaurus.match_synset("facet_canasta", clean)
        if canasta_match and canasta_match.canonical_id == "CANASTA_ALIMENTOS":
            facets["canasta"] = "ALIMENTOS"
            consumed_phrases.append(canasta_match.matched_term)
        elif any(
            term in clean
            for term in [
                "carestia de comida",
                "alimentos",
                "comida",
                "alimentos y bebidas",
                "corrientazo",
                "morfi",
                "canasta alimentaria",
            ]
        ):
            facets["canasta"] = "ALIMENTOS"
            for t in [
                "carestia de comida",
                "alimentos",
                "comida",
                "alimentos y bebidas",
                "corrientazo",
                "morfi",
                "canasta alimentaria",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
        if "salud" in clean:
            if any(
                term in clean
                for term in ["gasto", "presupuesto", "inversion publica", "cofog", "sector publico"]
            ):
                facets["funcion"] = "SALUD"
            else:
                facets["rubro"] = "SALUD"
            consumed_phrases.append("salud")

        if any(term in clean for term in ["moneda nacional", "moneda local"]):
            facets["moneda"] = "MONEDA_NACIONAL"
            for t in ["moneda nacional", "moneda local"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(
            term in clean
            for term in [
                "dolares constantes",
                "a precios constantes en dolares",
                "precios constantes en dolares",
            ]
        ):
            facets["moneda"] = "DOLARES_CONSTANTES"
            for t in [
                "dolares constantes",
                "a precios constantes en dolares",
                "precios constantes en dolares",
            ]:
                if t in clean:
                    consumed_phrases.append(t)

        # Generic ontology-driven facet extraction
        for fdef in self.ontology._facets.values():
            compiled_rules = self.ontology._compiled_triggers.get(fdef.facet_key)
            if compiled_rules:
                for _, pat, norm_phrases in compiled_rules:
                    if pat is not None and pat.search(clean):
                        for p in norm_phrases:
                            if p in clean:
                                consumed_phrases.append(p)
                    elif any(p in clean for p in norm_phrases):
                        for p in norm_phrases:
                            if p in clean:
                                consumed_phrases.append(p)

        ontology_facets = self.ontology.extract_facets_from_query(clean, self.thesaurus)
        for k, v in ontology_facets.items():
            if k not in facets or self.ontology.is_breakdown_value(k, v):
                if k == "educacion" and ("gasto" in clean or "presupuesto" in clean):
                    continue
                # Only override with breakdown value if a specific non-aggregate value wasn't explicitly set
                if k in facets and not self.ontology.is_breakdown_value(k, v):
                    continue
                if k in facets and self.ontology.is_critical_unhandled_facet(k, facets[k]):
                    continue
                facets[k] = v

        # ----------------------------------------------------
        # 5. Extract Root Concept & Controlled Ambiguities
        # ----------------------------------------------------
        facet_end_idx = len(consumed_phrases)

        concept_match = self.concept_ontology.extract_concept(
            clean,
            thesaurus=self.thesaurus,
            facets=facets,
            year=intent.year,
            catalog_profile=self.catalog_profile,
            polarity_info=intent.polarity_info,
        )
        if concept_match:
            intent.root_concept = concept_match.concept_key
            intent.is_ambiguous_measure = concept_match.is_ambiguous_measure
            intent.ambiguous_candidate = concept_match.ambiguous_candidate
            for phrase in concept_match.consumed_phrases:
                consumed_phrases.append(phrase)
            for f_k, f_v in concept_match.suggested_facets.items():
                if f_k not in facets:
                    facets[f_k] = f_v

        # Ensure gender ratio / comparison concepts don't unilaterally filter to a single sex
        if intent.root_concept == "BRECHA_SALARIAL":
            facets.pop("sexo", None)
        elif any(t in clean for t in ["mujeres", "mujer", "femenin"]) and any(
            t in clean for t in ["hombres", "hombre", "masculin"]
        ):
            facets["sexo"] = "SEXO_DESGLOSE"

        if intent.root_concept in ("GASTO_SOCIAL", "GASTO_EDUCACION"):
            if intent.root_concept == "GASTO_EDUCACION":
                facets.pop("funcion", None)
            else:
                facets.pop("rubro", None)
                if "salud" in clean or "sanitario" in clean or "atencion medica" in clean:
                    facets["funcion"] = "SALUD"
                elif "educacion" in clean or "educativo" in clean:
                    facets["funcion"] = "EDUCACION"
                elif "proteccion social" in clean or "seguridad social" in clean:
                    facets["funcion"] = "PROTECCION_SOCIAL"

        if (
            intent.root_concept
            in (
                "IPC_GENERAL",
                "IPC_ALIMENTOS",
                "IPC_SUBYACENTE",
                "INFLACION_ALIMENTOS",
                "IPC_TRANSPORTE_ENERGIA",
            )
            or "rubro" in facets
        ):
            facets.pop("funcion", None)

        if "moneda nacional" in clean and facets.get("area") == "NACIONAL":
            if not any(
                term in clean
                for term in ["area nacional", "nivel nacional", "total nacional", "todo el pais"]
            ):
                facets.pop("area", None)

        # ----------------------------------------------------
        # 6. Extract Unconsumed Semantic Tokens & Concept Tokens
        # ----------------------------------------------------
        raw_tokens = re.findall(r"\b[a-z0-9_]+\b", clean)
        consumed_words: set[str] = set()
        for phrase in consumed_phrases:
            for w in re.findall(r"\b[a-z0-9_]+\b", phrase):
                consumed_words.add(w)

        unconsumed: list[str] = []
        seen_unconsumed: set[str] = set()
        for tok in raw_tokens:
            if tok in SPANISH_STOPWORDS or tok in consumed_words:
                continue
            if tok not in seen_unconsumed:
                seen_unconsumed.add(tok)
                unconsumed.append(tok)

        # Informative concept tokens remaining after stripping geography, years, stopwords, and matched facet triggers
        temporal_phrases = consumed_phrases[temporal_start_idx:geo_start_idx]
        geo_phrases = consumed_phrases[geo_start_idx:facet_start_idx]
        facet_phrases = consumed_phrases[facet_start_idx:facet_end_idx]

        geo_words = {w for phrase in geo_phrases for w in re.findall(r"\b[a-z0-9_]+\b", phrase)}
        facet_words = {w for phrase in facet_phrases for w in re.findall(r"\b[a-z0-9_]+\b", phrase)}
        temporal_words = {
            w for phrase in temporal_phrases for w in re.findall(r"\b[a-z0-9_]+\b", phrase)
        }

        concept_tokens: list[str] = []
        seen_concepts: set[str] = set()
        for tok in raw_tokens:
            if (
                tok in SPANISH_STOPWORDS
                or tok.isdigit()
                or tok in geo_words
                or tok in facet_words
                or tok in temporal_words
                or len(tok) < 2
            ):
                continue
            if tok not in seen_concepts:
                seen_concepts.add(tok)
                concept_tokens.append(tok)

        intent.unconsumed_tokens = unconsumed
        intent.concept_tokens = concept_tokens
        intent.facets = facets
        return intent
