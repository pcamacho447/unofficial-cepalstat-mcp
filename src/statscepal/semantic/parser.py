"""Lexical and conceptual query parser for the CEPALSTAT semantic engine."""

import re
import unicodedata
from pydantic import BaseModel, Field


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
}


class ParsedIntent(BaseModel):
    """Normalized structured representation of a natural language query."""

    raw_query: str
    clean_query: str
    root_concept: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    year: int | None = None
    facets: dict[str, str] = Field(default_factory=dict)
    is_ambiguous_measure: bool = False
    ambiguous_candidate: str | None = None
    unsupported_facet: str | None = None
    unknown_concept: bool = False
    period_out_of_range: bool = False
    unsupported_frequency: bool = False


class QueryParser:
    """Translates raw natural language queries into normalized conceptual intents."""

    def parse(self, query: str) -> ParsedIntent:
        clean = strip_accents(query)
        facets: dict[str, str] = {}
        intent = ParsedIntent(raw_query=query, clean_query=clean)

        # 1. Detection of Out-of-Scope / Unsupported cases
        if "lunar" in clean or "marte" in clean:
            intent.unknown_concept = True

        if "astronauta" in clean or "astronautas" in clean:
            intent.unsupported_facet = "UNSUPPORTED_SECTOR"

        if "trimestral" in clean and "gini" in clean:
            intent.unsupported_frequency = True

        # 2. Extract Year
        year_match = re.search(r"\b(1\d{3}|20\d{2})\b", query)
        if year_match:
            year_val = int(year_match.group(1))
            intent.year = year_val
            if year_val < 1950 or year_val > 2030:
                intent.period_out_of_range = True

        # 3. Extract Country
        for name, code in COUNTRY_LEXICON.items():
            if re.search(r"\b" + re.escape(name) + r"\b", clean):
                intent.country_code = code
                intent.country_name = COUNTRY_NAMES[code]
                break

        # 4. Extract Facets (with Latin American regionalisms)
        # Area
        if any(term in clean for term in ["el campo", "rural", "campo"]):
            facets["area"] = "RURAL"
        elif any(term in clean for term in ["ciudades", "urbano", "ciudad", "urbana"]):
            facets["area"] = "URBANO"
        elif "total" in clean or "nacional" in clean or "pais" in clean:
            facets["area"] = "NACIONAL"

        # Sexo
        if any(term in clean for term in ["pibas", "chicas", "mujeres", "femenina", "femenino", "mujer"]):
            facets["sexo"] = "FEMENINO"
        elif any(term in clean for term in ["pibes", "chicos", "hombres", "masculino", "varones", "hombre"]):
            facets["sexo"] = "MASCULINO"

        # Edad
        if any(term in clean for term in ["pibes", "chavos", "jovenes", "juventud", "15 a 24"]):
            facets["edad"] = "JUVENTUD"
        elif any(term in clean for term in ["tercera edad", "abuelos", "ancianos", "adultos mayores", "65 y mas"]):
            facets["edad"] = "ADULTOS_MAYORES"
        elif any(term in clean for term in ["ninos", "ninas", "infancia", "0 a 14"]):
            facets["edad"] = "INFANCIA"

        # Severidad de pobreza
        if any(term in clean for term in ["extrema", "indigencia", "indigente", "miseria"]):
            facets["severidad"] = "POBREZA_EXTREMA"
        elif "pobreza" in clean:
            facets["severidad"] = "POBREZA_TOTAL"

        # Formalidad laboral (check if unsupported for poverty)
        if any(term in clean for term in ["en negro", "informal", "informalidad", "chamba informal"]):
            facets["formalidad"] = "INFORMAL"
            if "pobreza" in clean:
                intent.unsupported_facet = "FORMALIDAD_LABORAL"

        # Canasta alimentos
        if any(term in clean for term in ["carestia de comida", "alimentos", "comida", "alimentos y bebidas"]):
            facets["canasta"] = "ALIMENTOS"

        # 5. Extract Root Concept
        if "alimentos" in clean or "carestia de comida" in clean:
            intent.root_concept = "INFLACION_ALIMENTOS"
        elif "pobreza" in clean:
            intent.root_concept = "POBREZA"
            # Default area to NACIONAL if not specified
            if "area" not in facets:
                facets["area"] = "NACIONAL"
            # Check ambiguity: "pobreza femenina" without specific age/area
            if "femenina" in clean and "edad" not in facets and facets.get("area") == "NACIONAL" and not intent.year:
                intent.is_ambiguous_measure = True
                intent.ambiguous_candidate = "FEMININITY_INDEX"
        elif any(term in clean for term in ["desempleo", "desocupacion", "paro"]):
            intent.root_concept = "EMPLEO"
            if "sexo" not in facets:
                facets["sexo"] = "TOTAL"
            if "urbano" in clean and "edad" not in facets and not intent.year:
                intent.is_ambiguous_measure = True
                intent.ambiguous_candidate = "URBAN_UNEMPLOYMENT"
        elif "pib" in clean or "producto interno bruto" in clean:
            intent.root_concept = "PIB"
        elif "salario" in clean or "sueldo" in clean:
            intent.root_concept = "SALARIO"
        elif "gini" in clean or "desigualdad" in clean:
            intent.root_concept = "GINI"

        intent.facets = facets
        return intent
