"""Lexical and conceptual query parser for the CEPALSTAT semantic engine."""

import re
import unicodedata
from pydantic import BaseModel, Field

from statscepal.semantic.facet_ontology import (
    DEFAULT_FACET_ONTOLOGY,
    FacetOntology,
)
from statscepal.semantic.thesaurus import (
    PolarityResolution,
    PolarityType,
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

COUNTRY_NAMES: dict[str, str] = {
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

SPANISH_STOPWORDS: frozenset[str] = frozenset({
    # Grammatical articles and contractions
    "el", "la", "los", "las", "un", "una", "unos", "unas", "lo", "al", "del",
    # Prepositions
    "a", "ante", "bajo", "cabe", "con", "contra", "de", "desde", "durante",
    "en", "entre", "hacia", "hasta", "mediante", "para", "por", "segun",
    "sin", "so", "sobre", "tras", "versus", "vs", "frente",
    # Conjunctions and connectives
    "y", "e", "ni", "o", "u", "pero", "mas", "sino", "aunque", "que", "como", "si",
    # Pronouns and inquiry words
    "cual", "cuales", "quien", "quienes", "donde", "cuando", "cuanto", "cuanta",
    "cuantos", "cuantas", "me", "te", "se", "nos", "os", "le", "les",
    # Demonstratives and possessives
    "este", "esta", "estos", "estas", "esto", "ese", "esa", "esos", "esas", "eso",
    "aquel", "aquella", "aquellos", "aquellas", "aquello",
    "mi", "mis", "tu", "tus", "su", "sus", "nuestro", "nuestra", "nuestros", "nuestras",
    # Inquiry verbs and conversational terms
    "dame", "dime", "quiero", "ver", "busca", "buscar", "buscame", "mostrar",
    "muestra", "muestrame", "consultar", "consulta", "obtener", "traer", "traeme",
    "saber", "conocer", "dar", "decir", "revisar", "revisa", "deseo", "quisiera",
    "favor", "porfavor", "porfa",
    # Common verbs / copulas
    "es", "son", "fue", "fueron", "era", "eran", "ha", "han", "hay", "hubo",
    "habia", "esta", "estan", "estuvo", "estuvieron", "tener", "tiene", "tienen",
    "tenia", "tuvo", "ando", "anduvo", "entra", "entran", "entrado", "entron",
    "salen", "salieron", "cobra", "cobran", "crecio",
    # Generic statistical filler nouns and adjectives
    "tasa", "tasas",
    "nivel", "niveles",
    "indicador", "indicadores",
    "datos", "dato",
    "serie", "series",
    "cifra", "cifras",
    "estadistica", "estadisticas",
    "estimacion", "estimaciones",
    "valor", "valores",
    "indice", "indices",
    "ano", "anos",
    "trimestre", "trimestres",
    "mes", "meses",
    "periodo", "periodos",
    "promedio", "promedios",
    "medio", "medios", "media", "medias",
    "porcentaje", "porcentajes", "%",
    "oficial", "oficiales",
    "total", "totales",
    "general", "generales",
    "agregado", "agregada", "agregados", "agregadas",
    "incidencia", "participacion", "proporcion", "evolucion", "desempeno",
    "variacion", "variaciones", "situacion", "medicion", "medida", "medidas",
    "registro", "registros", "historico", "historica", "historicos", "historicas",
    "reciente", "recientes", "actual", "actuales", "ultimo", "ultima", "ultimos", "ultimas",
    "nacional", "nacionales", "pais", "todo", "toda", "todos", "todas",
    "medido", "medida", "medidos", "medidas", "calculado", "calculada",
    "relacion", "diferencia",
})

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
    "nominal",
    "nominales",
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
)


class QueryParser:
    """Translates raw natural language queries into normalized conceptual intents."""

    def __init__(
        self,
        catalog_profile: str = "official_25",
        thesaurus: Thesaurus | None = None,
        ontology: FacetOntology | None = None,
    ):
        self.catalog_profile = catalog_profile
        self.thesaurus = thesaurus or get_default_thesaurus()
        self.ontology = ontology or DEFAULT_FACET_ONTOLOGY

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

        if "coeficiencia intelectual" in clean or "coeficiente intelectual" in clean or re.search(r"\biq\b", clean):
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

        if "trimestral" in clean and "gini" in clean:
            intent.unsupported_frequency = True

        if any(term in clean for term in ["por segundo", "minuto a minuto", "en tiempo real", "tiempo real"]):
            intent.unsupported_frequency = True
            intent.frequency = "REALTIME"
            for t in ["por segundo", "minuto a minuto", "en tiempo real", "tiempo real"]:
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
        matched_countries: list[tuple[int, str]] = []
        for name, code in COUNTRY_LEXICON.items():
            if name not in clean:
                continue
            m = re.search(r"\b" + re.escape(name) + r"\b", clean)
            if m:
                matched_countries.append((m.start(), code))
                consumed_phrases.append(name)

        if matched_countries:
            matched_countries.sort(key=lambda item: item[0])
            seen_codes: set[str] = set()
            ordered_codes: list[str] = []
            for _, code in matched_countries:
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
            elif any(term in clean for term in ["el campo", "rural", "campo", "zona rural", "area rural"]):
                facets["area"] = "RURAL"
                for t in ["el campo", "rural", "campo", "zona rural", "area rural"]:
                    if t in clean:
                        consumed_phrases.append(t)
            elif any(term in clean for term in ["ciudades", "urbano", "ciudad", "urbana", "zona urbana", "area urbana", "villas"]):
                facets["area"] = "URBANO"
                for t in ["ciudades", "urbano", "ciudad", "urbana", "zona urbana", "area urbana", "villas"]:
                    if t in clean:
                        consumed_phrases.append(t)
            elif any(term in clean for term in ["area nacional", "total nacional", "todo el pais", "nivel nacional"]):
                facets["area"] = "NACIONAL"
                for t in ["area nacional", "total nacional", "todo el pais", "nivel nacional"]:
                    if t in clean:
                        consumed_phrases.append(t)
        if "pobreza total" in clean and "area" not in facets:
            facets["area"] = "NACIONAL"
            consumed_phrases.append("pobreza total")

        if "moneda nacional" in clean and facets.get("area") == "NACIONAL":
            if not any(term in clean for term in ["area nacional", "nivel nacional", "total nacional", "todo el pais"]):
                facets.pop("area", None)

        # Sexo
        sexo_match = self.thesaurus.match_synset("facet_sexo", clean)
        if sexo_match:
            facets["sexo"] = sexo_match.canonical_id
            consumed_phrases.append(sexo_match.matched_term)
        elif any(term in clean for term in ["pibas", "chicas", "mujeres", "femenina", "femenino", "mujer"]):
            facets["sexo"] = "FEMENINO"
            for t in ["pibas", "chicas", "mujeres", "femenina", "femenino", "mujer"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["pibes", "chicos", "hombres", "masculino", "varones", "hombre"]):
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
        for m in edad_matches:
            consumed_phrases.append(m.matched_term)

        if any(term in clean for term in ["ninos", "ninas", "infancia", "0 a 14", "infantil"]):
            if "edad" not in facets:
                facets["edad"] = "INFANCIA"
            for t in ["ninos", "ninas", "infancia", "0 a 14", "infantil"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["cabros", "pibes", "chavos", "chavas", "jovenes", "juventud", "15 a 24", "juvenil"]):
            if "edad" not in facets:
                facets["edad"] = "JUVENTUD"
            for t in ["cabros", "pibes", "chavos", "chavas", "jovenes", "juventud", "15 a 24", "juvenil"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["tercera edad", "abuelos", "ancianos", "adultos mayores", "65 y mas"]):
            if "edad" not in facets:
                facets["edad"] = "ADULTOS_MAYORES"
            for t in ["tercera edad", "abuelos", "ancianos", "adultos mayores", "65 y mas", "65 anos y mas", "65 anos"]:
                if t in clean:
                    consumed_phrases.append(t)
        if "pibas" in clean and any(term in clean for term in ["pobreza", "desempleo", "desocupacion", "paro"]):
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
        elif any(term in clean for term in ["en negro", "informal", "informalidad", "chamba informal"]):
            facets["formalidad"] = "INFORMAL"
            for t in ["en negro", "informal", "informalidad", "chamba informal"]:
                if t in clean:
                    consumed_phrases.append(t)
            if "pobreza" in clean:
                intent.unsupported_facet = "FORMALIDAD_LABORAL"

        # Estrato (Income distribution quintiles/deciles)
        for t in [
            "quintil 5 versus quintil 1", "q5 versus q1", "quintil 5 vs quintil 1",
            "primer quintil", "q1", "quintil 1", "quintil mas pobre", "los de abajo",
            "quinto quintil", "q5", "quintil 5", "20 por ciento mas rico",
            "decil 10", "decil mas rico", "los mas ricos",
            "decil 1", "decil mas pobre", "decil 1 mas vulnerable",
            "por quintiles", "los quintiles", "entre los quintiles", "entre quintiles", "quintiles", "quintil",
            "por deciles", "los deciles", "entre los deciles", "entre deciles", "deciles", "decil",
        ]:
            if t in clean:
                consumed_phrases.append(t)

        if any(term in clean for term in ["quintil 5 versus quintil 1", "q5 versus q1", "quintil 5 vs quintil 1"]):
            facets["estrato"] = "RELACION_Q5_Q1"
        elif any(term in clean for term in ["primer quintil", "q1", "quintil 1", "quintil mas pobre", "los de abajo"]):
            facets["estrato"] = "QUINTIL_1"
        elif any(term in clean for term in ["quinto quintil", "q5", "quintil 5", "20 por ciento mas rico"]):
            facets["estrato"] = "QUINTIL_5"
        elif any(term in clean for term in ["decil 10", "decil mas rico", "los mas ricos"]):
            facets["estrato"] = "DECIL_10"
        elif any(term in clean for term in ["decil 1", "decil mas pobre", "decil 1 mas vulnerable"]):
            facets["estrato"] = "DECIL_1"
        elif any(term in clean for term in ["por quintiles", "los quintiles", "entre los quintiles", "entre quintiles", "quintiles", "quintil"]):
            facets["estrato"] = "QUINTIL"
        elif any(term in clean for term in ["por deciles", "los deciles", "entre los deciles", "entre deciles", "deciles", "decil"]):
            facets["estrato"] = "DECIL"

        # Canasta alimentos & rubros
        canasta_match = self.thesaurus.match_synset("facet_canasta", clean)
        if canasta_match and canasta_match.canonical_id == "CANASTA_ALIMENTOS":
            facets["canasta"] = "ALIMENTOS"
            consumed_phrases.append(canasta_match.matched_term)
        elif any(term in clean for term in ["carestia de comida", "alimentos", "comida", "alimentos y bebidas", "corrientazo", "morfi", "canasta alimentaria"]):
            facets["canasta"] = "ALIMENTOS"
            for t in ["carestia de comida", "alimentos", "comida", "alimentos y bebidas", "corrientazo", "morfi", "canasta alimentaria"]:
                if t in clean:
                    consumed_phrases.append(t)
        if "salud" in clean:
            facets["rubro"] = "SALUD"
            consumed_phrases.append("salud")

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
        has_pib = bool(re.search(r"\bpib\b", clean) or "producto interno bruto" in clean)
        if has_pib:
            if re.search(r"\bpib\b", clean):
                consumed_phrases.append("pib")
            if "producto interno bruto" in clean:
                consumed_phrases.append("producto interno bruto")

        # Ambiguous Controlled Scenarios Upfront
        if "privacion y pobreza" in clean or ("privacion" in clean and "pobreza" in clean and not intent.year):
            intent.root_concept = "POBREZA"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "PRIVATION_GAP"
            for t in ["privacion y pobreza", "privacion", "pobreza"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif "desigualdad del ingreso" in clean and not any(k in facets for k in ["estrato"]):
            intent.root_concept = "DISTRIBUCION_INGRESO"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "INEQUALITY_INCOME"
            consumed_phrases.append("desigualdad del ingreso")
        elif "brecha distributiva" in clean and not any(k in facets for k in ["estrato"]):
            intent.root_concept = "DISTRIBUCION_INGRESO"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "DISTRIBUTIVE_GAP"
            consumed_phrases.append("brecha distributiva")
        elif "situacion laboral" in clean:
            intent.root_concept = "EMPLEO"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "LABOR_SITUATION"
            consumed_phrases.append("situacion laboral")
        elif "paro y salarios" in clean or ("desempleo y salarios" in clean):
            intent.root_concept = "EMPLEO"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "UNEMPLOYMENT_AND_WAGES"
            for t in ["paro y salarios", "desempleo y salarios", "paro", "salarios", "desempleo"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif "economia de" in clean and not has_pib and not any(t in clean for t in ["crecio", "crecimiento"]):
            intent.root_concept = "PIB"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "MACRO_ECONOMY"
            consumed_phrases.append("economia")
        elif "actividad economica en" in clean and "trimestral" not in clean and not has_pib:
            intent.root_concept = "PIB"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "ECONOMIC_ACTIVITY"
            consumed_phrases.append("actividad economica")
        elif "inflacion sectorial" in clean:
            intent.root_concept = "IPC_GENERAL"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "SECTORAL_INFLATION"
            consumed_phrases.append("inflacion sectorial")
        elif re.search(r"\bprecios en\b", clean) and not any(t in clean for t in ["alimentos", "transporte", "energia", "morfi", "consumidor"]):
            intent.root_concept = "IPC_GENERAL"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "GENERAL_PRICES"
            consumed_phrases.append("precios")
        elif "cuentas fiscales" in clean:
            intent.root_concept = "DEUDA_PUBLICA"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "FISCAL_ACCOUNTS"
            consumed_phrases.append("cuentas fiscales")
        elif "situacion hacendaria" in clean:
            intent.root_concept = "DEUDA_PUBLICA"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "FISCAL_HEALTH"
            consumed_phrases.append("situacion hacendaria")
        elif "sector externo en" in clean:
            intent.root_concept = "CUENTA_CORRIENTE"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "EXTERNAL_SECTOR"
            consumed_phrases.append("sector externo")
        elif "comercio internacional y pagos" in clean:
            intent.root_concept = "CUENTA_CORRIENTE"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "INTERNATIONAL_TRADE_PAYMENTS"
            consumed_phrases.append("comercio internacional y pagos")
        elif (
            "emisiones de gases de efecto invernadero en" in clean
            and not any(t in clean for t in ["sin", "excluyendo", "con uso"])
            and not (intent.polarity_info and intent.polarity_info.polarity_type == PolarityType.INCLUSION_EXCLUSION)
        ):
            intent.root_concept = "EMISIONES_GEI_LULUCF"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "EMISSIONS_LULUCF_CHOICE"
            consumed_phrases.append("emisiones de gases de efecto invernadero")
        elif "matriz energetica y contaminacion" in clean:
            intent.root_concept = "EMISIONES_GEI_LULUCF"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "ENERGY_POLLUTION"
            consumed_phrases.append("matriz energetica y contaminacion")
        elif "situacion socioeconomica y bienestar" in clean:
            intent.root_concept = "POBREZA"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "SOCIOECONOMIC_WELLBEING"
            consumed_phrases.append("situacion socioeconomica y bienestar")
        elif "panorama macroeconomico y fiscal" in clean:
            intent.root_concept = "PIB"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "MACRO_FISCAL_PANORAMA"
            consumed_phrases.append("panorama macroeconomico y fiscal")

        # Sector Público & Finanzas Públicas (checked first so "... % del PIB" does not shadow)
        elif any(term in clean for term in ["deuda", "endeudamiento"]):
            intent.root_concept = "DEUDA_PUBLICA"
            for t in ["deuda", "endeudamiento", "endeudamiento soberano", "deuda publica", "gobierno central", "gobierno", "estado"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(
            term in clean
            for term in [
                "balance primario",
                "superavit primario",
                "deficit primario",
                "superavit fiscal",
                "deficit fiscal",
                "rojo fiscal",
                "rojo primario",
                "resultado fiscal primario",
            ]
        ) or (
            intent.polarity_info
            and intent.polarity_info.canonical_indicator_id == 1241
            and not any(term in clean for term in ["cuenta corriente", "comercial", "balanza", "comercio"])
        ):
            intent.root_concept = "BALANCE_PRIMARIO"
            for t in [
                "balance primario", "superavit primario", "deficit primario",
                "superavit fiscal", "deficit fiscal", "rojo fiscal", "rojo primario",
                "resultado fiscal primario", "balance primario fiscal", "pago de intereses",
                "gobierno central", "gobierno",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["ingresos tributarios", "recaudacion tributaria", "recaudacion", "tributar", "carga tributaria", "presion fiscal", "dian", "cuantos impuestos", "impuestos", "el fisco"]):
            if any(term in clean for term in ["moneda nacional", "precios corrientes", "moneda local", "en pesos", "en soles", "en reales", "nominales", "nominal"]):
                intent.root_concept = "INGRESOS_TRIBUTARIOS_CORRIENTES"
            else:
                intent.root_concept = "INGRESOS_TRIBUTARIOS"
            for t in ["ingresos tributarios", "recaudacion tributaria", "recaudacion", "tributar", "carga tributaria", "presion fiscal", "presion fiscal tributaria", "dian", "cuantos impuestos", "impuestos", "el fisco", "gobierno central", "gobierno"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif "gasto social" in clean:
            intent.root_concept = "GASTO_SOCIAL"
            consumed_phrases.append("gasto social")
        elif "gasto publico en educacion" in clean or ("gasto" in clean and "educacion" in clean):
            intent.root_concept = "GASTO_EDUCACION"
            for t in ["gasto publico en educacion", "gasto", "educacion", "presupuesto"]:
                if t in clean:
                    consumed_phrases.append(t)

        # Sector Externo (checked first so "... % del PIB" does not shadow)
        elif "balanza comercial" in clean:
            intent.root_concept = "BALANZA_COMERCIAL"
            consumed_phrases.append("balanza comercial")
        elif any(term in clean for term in ["cuenta corriente", "transacciones corrientes", "deficit externo en cuenta corriente", "balanza en cuenta corriente"]):
            if "costa rica" in clean and "balanza de pagos" not in clean:
                intent.root_concept = "CUENTA_CORRIENTE_740"
            else:
                intent.root_concept = "CUENTA_CORRIENTE"
            for t in ["cuenta corriente", "transacciones corrientes", "deficit externo en cuenta corriente", "balanza en cuenta corriente", "balanza de pagos", "deficit externo"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif "inversion extranjera" in clean or re.search(r"\bied\b", clean):
            intent.root_concept = "INVERSION_EXTRANJERA_DIRECTA"
            for t in ["inversion extranjera", "ied"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in [
            "terminos de intercambio",
            "relacion de precios del comercio exterior",
            "terminos del comercio exterior",
            "exportaciones versus importaciones",
            "lo que vendemos versus lo que compramos",
        ]):
            intent.root_concept = "TERMINOS_INTERCAMBIO"
            for t in [
                "terminos de intercambio", "relacion de precios del comercio exterior",
                "terminos del comercio exterior", "exportaciones versus importaciones",
                "lo que vendemos versus lo que compramos", "relacion de intercambio",
                "bienes", "comercio exterior",
            ]:
                if t in clean:
                    consumed_phrases.append(t)

        # Medio Ambiente
        elif any(term in clean for term in [
            "renovable",
            "renovables",
            "energia limpia",
            "energias limpias",
            "matriz electrica",
            "luz verde",
            "enchufes",
            "generacion electrica renovable",
            "porcentaje de energias limpias",
            "proporcion de renovables",
        ]):
            intent.root_concept = "ENERGIA_RENOVABLE"
            for t in [
                "renovable", "renovables", "energia limpia", "energias limpias",
                "matriz electrica", "luz verde", "enchufes", "generacion electrica renovable",
                "porcentaje de energias limpias", "proporcion de renovables",
                "generacion electrica", "electrica", "contaminamos",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
        elif (
            "emisiones" in clean
            or "gei" in clean
            or "gases de invernadero" in clean
            or "huella de carbono" in clean
            or (intent.polarity_info and intent.polarity_info.polarity_type == PolarityType.INCLUSION_EXCLUSION)
        ):
            if (intent.polarity_info and intent.polarity_info.canonical_indicator_id == 5682) or any(
                term in clean
                for term in [
                    "sin lulucf",
                    "sin utcuts",
                    "excluyendo utcuts",
                    "excluyendo sector utcuts",
                    "sin uso de la tierra",
                    "sin cambio de uso",
                    "sin considerar bosques",
                    "excluyendo el sector uso de la tierra",
                ]
            ):
                intent.root_concept = "EMISIONES_GEI_SIN_LULUCF"
            else:
                intent.root_concept = "EMISIONES_GEI_LULUCF"
            for t in [
                "emisiones", "gei", "gases de invernadero", "huella de carbono",
                "gases de efecto invernadero", "emisiones totales", "emisiones netas",
                "emisiones brutas", "sin lulucf", "sin utcuts", "excluyendo utcuts",
                "excluyendo sector utcuts", "sin uso de la tierra", "sin cambio de uso",
                "sin considerar bosques", "excluyendo el sector uso de la tierra",
                "con lulucf", "incluyendo utcuts", "deforestacion y cambio de uso de suelo",
                "metano", "carbono",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["agua dulce", "recursos hidricos", "extraccion de agua"]):
            intent.root_concept = "AGUA_DULCE"
            for t in ["agua dulce", "recursos hidricos", "extraccion de agua"]:
                if t in clean:
                    consumed_phrases.append(t)

        # Precios e Inflación
        elif any(
            term in clean
            for term in [
                "transporte",
                "energia",
                "transporte y energia",
                "combustible",
                "combustibles",
                "gasolina",
                "nafta",
                "bencina",
                "diesel",
                "gasoil",
                "electricidad",
                "tarifas de luz",
            ]
        ) or (
            (canasta_syn := self.thesaurus.match_synset("facet_canasta", clean))
            and canasta_syn.canonical_id == "CANASTA_COMBUSTIBLES"
        ):
            if any(
                term in clean
                for term in [
                    "ipc",
                    "precios",
                    "precio",
                    "inflacion",
                    "golpe al bolsillo",
                    "variacion de precios",
                    "variacion",
                    "aumento",
                    "suba",
                    "alza",
                    "carestia",
                    "costo",
                ]
            ):
                intent.root_concept = "IPC_TRANSPORTE_ENERGIA"
            for t in [
                "transporte", "energia", "transporte y energia", "combustible",
                "combustibles", "gasolina", "nafta", "bencina", "diesel", "gasoil",
                "electricidad", "tarifas de luz", "ipc", "precios", "precio",
                "inflacion", "golpe al bolsillo", "variacion de precios", "variacion",
                "aumento", "suba", "alza", "carestia", "costo",
            ]:
                if t in clean:
                    consumed_phrases.append(t)

        elif "corrientazo" in clean or "alimentos y bebidas" in clean or "canasta alimentaria" in clean or "morfi" in clean or "carestia de la comida" in clean:
            intent.root_concept = "IPC_ALIMENTOS"
            facets["canasta"] = "ALIMENTOS"
            for t in ["corrientazo", "alimentos y bebidas", "canasta alimentaria", "morfi", "carestia de la comida", "carestia de comida"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif ("inflacion de alimentos" in clean or any(term in clean for term in ["doce meses", "interanual", "carestia de comida"])) and not has_pib:
            intent.root_concept = "INFLACION_ALIMENTOS"
            for t in ["inflacion de alimentos", "doce meses", "interanual", "carestia de comida", "alimentos"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif "alimentos" in clean and any(term in clean for term in ["ipc", "inflacion", "precios"]):
            intent.root_concept = "INFLACION_ALIMENTOS" if "inflacion" in clean else "IPC_ALIMENTOS"
            for t in ["alimentos", "ipc", "inflacion", "precios"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(
            term in clean
            for term in [
                "subyacente",
                "inflacion subyacente",
                "ipc subyacente",
                "inflacion basica",
                "inflacion core",
                "core anual",
                "core inflation",
                "precios subyacentes",
            ]
        ):
            intent.root_concept = "IPC_SUBYACENTE"
            for t in [
                "subyacente", "inflacion subyacente", "ipc subyacente", "inflacion basica",
                "inflacion core", "core anual", "core inflation", "precios subyacentes",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(
            term in clean
            for term in [
                "ipc",
                "precios al consumidor",
                "costo de la vida",
                "costo de vida",
                "inflacion general",
                "tasa de inflacion",
                "inflacion",
            ]
        ):
            intent.root_concept = "IPC_GENERAL"
            for t in [
                "ipc", "precios al consumidor", "costo de la vida", "costo de vida",
                "inflacion general", "tasa de inflacion", "inflacion", "precios",
            ]:
                if t in clean:
                    consumed_phrases.append(t)

        # Cuentas Nacionales & PIB
        elif ("per capita" in clean and (has_pib or "riqueza" in clean)) or "pib per capita" in clean or "por habitante" in clean or "riqueza por cabeza" in clean:
            intent.root_concept = "PIB_PER_CAPITA"
            for t in ["per capita", "pib per capita", "por habitante", "riqueza por cabeza", "por cabeza", "riqueza"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif ("trimestral" in clean and (has_pib or "actividad economica" in clean or "desempeno economico" in clean)) or "crecimiento interanual trimestral" in clean:
            intent.root_concept = "PIB_TRIMESTRAL"
            for t in ["trimestral", "crecimiento interanual trimestral", "actividad economica", "desempeno economico"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif ("corrientes" in clean or "moneda nacional" in clean) and has_pib:
            intent.root_concept = "PIB_CORRIENTE"
            for t in ["corrientes", "moneda nacional"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif has_pib or any(term in clean for term in ["crecio la economia", "crecimiento del pib", "crecimiento de la economia", "aparato productivo"]):
            intent.root_concept = "PIB"
            for t in ["crecio la economia", "crecimiento del pib", "crecimiento de la economia", "aparato productivo"]:
                if t in clean:
                    consumed_phrases.append(t)

        # Pobreza Brecha
        elif "brecha de pobreza" in clean or ("brecha" in clean and "pobreza" in clean and "salarial" not in clean):
            intent.root_concept = "POBREZA_BRECHA"
            if "area" not in facets:
                facets["area"] = "NACIONAL"
            for t in ["brecha de pobreza", "brecha", "pobreza"]:
                if t in clean:
                    consumed_phrases.append(t)

        # Distribución del Ingreso / Quintiles / Deciles
        elif any(term in clean for term in [
            "distribucion del ingreso",
            "distribucion de la lana",
            "distribucion de los ingresos",
            "concentracion del ingreso",
            "los de abajo",
            "deciles",
            "decil",
            "quintiles",
            "quintil",
            "brecha distributiva",
            "cuanta torta",
            "reparto del billete",
            "20 por ciento mas rico",
        ]):
            for t in [
                "distribucion del ingreso", "distribucion de la lana", "distribucion de los ingresos",
                "concentracion del ingreso", "los de abajo", "deciles", "decil",
                "quintiles", "quintil", "brecha distributiva", "cuanta torta",
                "reparto del billete", "20 por ciento mas rico",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
            if any(term in clean for term in ["poblacion", "habitantes", "personas", "indigena", "afrodescendiente", "demografia", "demografico", "demograficos"]) or "etnia" in facets:
                intent.root_concept = "POBLACION"
                if "estrato" not in facets and any(term in clean for term in ["quintil", "quintiles"]):
                    facets["estrato"] = "QUINTIL"
            else:
                intent.root_concept = "DISTRIBUCION_INGRESO"

        # Mercado Laboral & Pobreza & Brecha Salarial
        elif any(
            term in clean
            for term in [
                "brecha salarial",
                "brecha de ingresos",
                "brecha de ingreso",
                "brecha de genero",
                "relacion de ingreso",
                "relacion de ingresos",
                "relacion del ingreso",
                "diferencia de ingresos entre",
                "diferencia salarial entre",
                "diferencia de salario entre",
            ]
        ) and (
            any(term in clean for term in ["genero", "mujeres", "hombres", "sexo", "laboral", "laborales", "salarial", "salariales", "trabajadores"])
            or "brecha salarial" in clean
        ):
            intent.root_concept = "BRECHA_SALARIAL"
            for t in [
                "brecha salarial", "brecha de ingresos", "brecha de ingreso", "brecha de genero",
                "relacion de ingreso", "relacion de ingresos", "relacion del ingreso",
                "diferencia de ingresos entre", "diferencia salarial entre", "diferencia de salario entre",
                "genero", "mujeres", "hombres", "sexo", "laboral", "laborales", "salarial", "salariales", "trabajadores",
            ]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["cabros", "desocupacion de los pibes", "chavos sin chamba"]) and any(term in clean for term in ["sin pega", "desempleo", "desocupacion", "paro", "sin chamba"]):
            intent.root_concept = "DESEMPLEO_JUVENIL_15_24"
            facets["edad"] = "JUVENTUD"
            for t in ["cabros", "desocupacion de los pibes", "chavos sin chamba", "sin pega", "desempleo", "desocupacion", "paro", "sin chamba"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in [
            "desempleo juvenil",
            "desempleo de los jovenes",
            "desempleo de mujeres jovenes",
            "desempleo juvenil masculino",
            "jovenes sin chamba",
        ]):
            intent.root_concept = "DESEMPLEO_JUVENIL"
            facets["edad"] = "JUVENTUD"
            for t in ["desempleo juvenil", "desempleo de los jovenes", "desempleo de mujeres jovenes", "desempleo juvenil masculino", "jovenes sin chamba", "desempleo", "desocupacion", "paro"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["chamba", "camello", "sin pega", "sin laburo", "jale"]):
            intent.root_concept = "EMPLEO"
            if "sexo" not in facets:
                facets["sexo"] = "TOTAL" if self.catalog_profile == "legacy_50" else "AMBOS"
            for t in ["chamba", "camello", "sin pega", "sin laburo", "jale"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["pobreza", "miseria", "indigencia", "no tienen un sope", "malaria economica"]):
            intent.root_concept = "POBREZA"
            if "area" not in facets:
                facets["area"] = "NACIONAL"
            if "femenina" in clean and "edad" not in facets and facets.get("area") == "NACIONAL" and not intent.year:
                intent.is_ambiguous_measure = True
                intent.ambiguous_candidate = "FEMININITY_INDEX"
            for t in ["pobreza", "miseria", "indigencia", "no tienen un sope", "malaria economica", "femenina"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["desempleo", "desocupacion", "paro", "desocupacion abierta"]):
            intent.root_concept = "EMPLEO"
            if "sexo" not in facets:
                facets["sexo"] = "TOTAL" if self.catalog_profile == "legacy_50" else "AMBOS"
            if "urbano" in clean and "edad" not in facets and not intent.year:
                intent.is_ambiguous_measure = True
                intent.ambiguous_candidate = "URBAN_UNEMPLOYMENT"
            for t in ["desempleo", "desocupacion", "paro", "desocupacion abierta"]:
                if t in clean:
                    consumed_phrases.append(t)

        # Income Modifiers & Deconstruction
        elif any(term in clean for term in ["salario", "sueldo", "plata", "guita", "lana", "lucas", "ingreso", "ingresos", "remuneracion", "remuneraciones", "billete"]):
            for t in ["salario", "sueldo", "plata", "guita", "lana", "lucas", "ingreso", "ingresos", "remuneracion", "remuneraciones", "billete"]:
                if t in clean:
                    consumed_phrases.append(t)
            if any(term in clean for term in ["minima", "minimo", "por ley", "sueldo basico", "salario basico", "basico de ley", "basico"]):
                intent.root_concept = "SALARIO_MINIMO"
                for t in ["minima", "minimo", "por ley", "sueldo basico", "salario basico", "basico de ley", "basico"]:
                    if t in clean:
                        consumed_phrases.append(t)
            elif any(term in clean for term in ["hogar", "hogares", "familias", "familia", "por cabeza", "per capita"]) and not has_pib:
                intent.root_concept = "INGRESO_HOGARES"
                for t in ["hogar", "hogares", "familias", "familia", "por cabeza", "per capita"]:
                    if t in clean:
                        consumed_phrases.append(t)
            elif "laboral" in clean:
                intent.root_concept = "INGRESO_LABORAL"
                consumed_phrases.append("laboral")
            elif facets.get("edad") == "JUVENTUD":
                intent.root_concept = "SALARIO"
            elif any(term in clean for term in ["laburantes", "trabajadores", "trabajadores rasos", "asalariados", "medio", "remuneraciones", "promedio"]):
                intent.root_concept = "SALARIO_REAL"
                for t in ["laburantes", "trabajadores", "trabajadores rasos", "asalariados", "medio", "remuneraciones", "promedio"]:
                    if t in clean:
                        consumed_phrases.append(t)
            else:
                # Unmodified slang or broad income query
                intent.root_concept = "SALARIO_REAL"
                intent.is_ambiguous_measure = True
                intent.ambiguous_candidate = "INCOME_MEASURES"

        elif "gini" in clean or "desigualdad" in clean:
            intent.root_concept = "GINI"
            for t in ["gini", "desigualdad"]:
                if t in clean:
                    consumed_phrases.append(t)
        elif any(term in clean for term in ["poblacion", "habitantes", "demografia", "demografico", "demograficos"]):
            intent.root_concept = "POBLACION"
            for t in ["poblacion", "habitantes", "demografia", "demografico", "demograficos"]:
                if t in clean:
                    consumed_phrases.append(t)

        # Ensure gender ratio / comparison concepts don't unilaterally filter to a single sex
        if intent.root_concept == "BRECHA_SALARIAL":
            facets.pop("sexo", None)
        elif (
            any(t in clean for t in ["mujeres", "mujer", "femenin"])
            and any(t in clean for t in ["hombres", "hombre", "masculin"])
        ):
            facets["sexo"] = "SEXO_DESGLOSE"

        if "moneda nacional" in clean and facets.get("area") == "NACIONAL":
            if not any(term in clean for term in ["area nacional", "nivel nacional", "total nacional", "todo el pais"]):
                facets.pop("area", None)

        # ----------------------------------------------------
        # 6. Extract Unconsumed Semantic Tokens
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

        intent.unconsumed_tokens = unconsumed
        intent.facets = facets
        return intent

