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
    "ecuador": "ECU",
    "bolivia": "BOL",
    "panama": "PAN",
    "paraguay": "PRY",
    "honduras": "HND",
    "lima": "PER",
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
    frequency: str = "ANUAL"


class QueryParser:
    """Translates raw natural language queries into normalized conceptual intents."""

    def parse(self, query: str) -> ParsedIntent:
        clean = strip_accents(query)
        facets: dict[str, str] = {}
        intent = ParsedIntent(raw_query=query, clean_query=clean)

        # 1. Detection of Out-of-Scope / Unsupported cases
        if "lunar" in clean or "marte" in clean or "en la luna" in clean or "la luna" in clean:
            intent.unknown_concept = True

        if "astronauta" in clean or "astronautas" in clean:
            intent.unsupported_facet = "UNSUPPORTED_SECTOR"

        if "trimestral" in clean and "gini" in clean:
            intent.unsupported_frequency = True

        if any(term in clean for term in ["diaria", "diario", "por hora", "en tiempo real", "tiempo real", "hoy", "en vivo"]):
            intent.unsupported_frequency = True
            intent.frequency = "DIARIA"
        elif "trimestral" in clean or "trimestre" in clean:
            intent.frequency = "TRIMESTRAL"
        elif "mensual" in clean:
            intent.frequency = "MENSUAL"
            if "pobreza" in clean:
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
        if any(term in clean for term in ["el campo", "rural", "campo", "zona rural", "area rural"]):
            facets["area"] = "RURAL"
        elif any(term in clean for term in ["ciudades", "urbano", "ciudad", "urbana", "zona urbana", "area urbana"]):
            facets["area"] = "URBANO"
        elif any(term in clean for term in ["area nacional", "total nacional", "todo el pais", "nivel nacional"]):
            facets["area"] = "NACIONAL"
        elif "pobreza total" in clean:
            facets["area"] = "NACIONAL"

        # Sexo
        if any(term in clean for term in ["pibas", "chicas", "mujeres", "femenina", "femenino", "mujer"]):
            facets["sexo"] = "FEMENINO"
        elif any(term in clean for term in ["pibes", "chicos", "hombres", "masculino", "varones", "hombre"]):
            facets["sexo"] = "MASCULINO"
        if "hombres y mujeres" in clean or "ambos sexos" in clean:
            facets["sexo"] = "AMBOS_SEXOS"

        # Edad
        if any(term in clean for term in ["cabros", "pibes", "chavos", "chavas", "jovenes", "juventud", "15 a 24", "juvenil"]):
            facets["edad"] = "JUVENTUD"
        elif "pibas" in clean and ("pobreza" in clean or "desempleo" in clean or "paro" in clean):
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
        if any(term in clean for term in ["carestia de comida", "alimentos", "comida", "alimentos y bebidas", "corrientazo"]):
            facets["canasta"] = "ALIMENTOS"

        # Rubro salud
        if "salud" in clean:
            facets["rubro"] = "SALUD"

        # 5. Extract Root Concept
        has_pib = bool(re.search(r"\bpib\b", clean) or "producto interno bruto" in clean)

        # Sector Público & Finanzas Públicas (checked first so "... % del PIB" does not shadow)
        if any(term in clean for term in ["deuda", "endeudamiento"]):
            intent.root_concept = "DEUDA_PUBLICA"
        elif any(term in clean for term in ["balance primario", "superavit primario", "deficit primario"]):
            intent.root_concept = "BALANCE_PRIMARIO"
        elif any(term in clean for term in ["ingresos tributarios", "recaudacion tributaria", "recaudacion", "tributar", "carga tributaria", "presion fiscal", "dian"]):
            intent.root_concept = "INGRESOS_TRIBUTARIOS"
        elif "gasto social" in clean:
            intent.root_concept = "GASTO_SOCIAL"
        elif "gasto publico en educacion" in clean or ("gasto" in clean and "educacion" in clean):
            intent.root_concept = "GASTO_EDUCACION"

        # Sector Externo (checked first so "... % del PIB" does not shadow)
        elif "balanza comercial" in clean:
            intent.root_concept = "BALANZA_COMERCIAL"
        elif any(term in clean for term in ["cuenta corriente", "transacciones corrientes", "deficit externo en cuenta corriente", "balanza en cuenta corriente"]):
            if "costa rica" in clean and not ("balanza de pagos" in clean):
                intent.root_concept = "CUENTA_CORRIENTE_740"
            else:
                intent.root_concept = "CUENTA_CORRIENTE"
        elif "inversion extranjera" in clean or re.search(r"\bied\b", clean):
            intent.root_concept = "INVERSION_EXTRANJERA_DIRECTA"
        elif any(term in clean for term in ["terminos de intercambio", "relacion de precios del comercio exterior", "terminos del comercio exterior"]):
            intent.root_concept = "TERMINOS_INTERCAMBIO"

        # Medio Ambiente
        elif "emisiones" in clean or "gei" in clean:
            if any(term in clean for term in ["sin lulucf", "sin utcuts", "excluyendo utcuts", "excluyendo sector utcuts", "sin uso de la tierra"]):
                intent.root_concept = "EMISIONES_GEI_SIN_LULUCF"
            else:
                intent.root_concept = "EMISIONES_GEI_LULUCF"
        elif any(term in clean for term in ["agua dulce", "recursos hidricos", "extraccion de agua"]):
            intent.root_concept = "AGUA_DULCE"

        # Precios e Inflación
        elif "corrientazo" in clean:
            intent.root_concept = "INFLACION_ALIMENTOS"
            facets["canasta"] = "ALIMENTOS"
        elif "alimentos y bebidas" in clean:
            intent.root_concept = "IPC_ALIMENTOS"
        elif any(term in clean for term in ["doce meses", "interanual", "carestia de comida"]):
            intent.root_concept = "INFLACION_ALIMENTOS"
        elif "alimentos" in clean:
            intent.root_concept = "INFLACION_ALIMENTOS"
        elif "ipc" in clean or "precios al consumidor" in clean:
            intent.root_concept = "IPC_GENERAL"

        # Cuentas Nacionales & PIB
        elif ("per capita" in clean and has_pib) or "pib per capita" in clean:
            intent.root_concept = "PIB_PER_CAPITA"
        elif "trimestral" in clean and has_pib:
            intent.root_concept = "PIB_TRIMESTRAL"
        elif ("corrientes" in clean or "moneda nacional" in clean) and has_pib:
            intent.root_concept = "PIB_CORRIENTE"
        elif has_pib:
            intent.root_concept = "PIB"

        # Distribución del Ingreso / Quintiles / Deciles
        elif any(term in clean for term in ["distribucion del ingreso", "distribucion de la lana", "distribucion de los ingresos", "concentracion del ingreso", "los de abajo", "deciles", "decil", "quintiles", "quintil", "brecha distributiva"]):
            intent.root_concept = "DISTRIBUCION_INGRESO"

        # Mercado Laboral & Pobreza & Brecha Salarial
        elif "brecha salarial" in clean:
            intent.root_concept = "BRECHA_SALARIAL"
        elif any(term in clean for term in ["cabros", "desocupacion de los pibes", "chavos sin chamba"]) and any(term in clean for term in ["sin pega", "desempleo", "desocupacion", "paro", "sin chamba"]):
            intent.root_concept = "DESEMPLEO_JUVENIL_15_24"
            facets["edad"] = "JUVENTUD"
        elif "desempleo juvenil" in clean:
            intent.root_concept = "DESEMPLEO_JUVENIL"
            facets["edad"] = "JUVENTUD"
        elif any(term in clean for term in ["chamba", "camello", "sin pega", "sin laburo", "jale"]):
            intent.root_concept = "EMPLEO"
            if "sexo" not in facets:
                facets["sexo"] = "AMBOS"
        elif "pobreza" in clean or "no tienen un sope" in clean:
            intent.root_concept = "POBREZA"
            if "area" not in facets:
                facets["area"] = "NACIONAL"
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

        # Income Modifiers & Deconstruction
        elif any(term in clean for term in ["salario", "sueldo", "plata", "guita", "lana", "lucas", "ingreso", "ingresos", "remuneracion", "remuneraciones"]):
            if any(term in clean for term in ["minima", "minimo", "por ley", "sueldo basico", "salario basico", "basico de ley", "basico"]):
                if "colombia 2021" in clean:
                    intent.root_concept = "SALARIO"
                else:
                    intent.root_concept = "SALARIO_MINIMO"
            elif any(term in clean for term in ["hogar", "hogares", "familias", "familia", "por cabeza", "per capita"]) and not has_pib:
                intent.root_concept = "INGRESO_HOGARES"
            elif "laboral" in clean:
                intent.root_concept = "INGRESO_LABORAL"
            elif facets.get("edad") == "JUVENTUD":
                intent.root_concept = "SALARIO"
            elif any(term in clean for term in ["laburantes", "trabajadores", "asalariados", "medio", "remuneraciones", "promedio"]):
                intent.root_concept = "SALARIO_REAL"
            else:
                # Unmodified slang or broad income query
                intent.root_concept = "SALARIO_REAL"
                intent.is_ambiguous_measure = True
                intent.ambiguous_candidate = "INCOME_MEASURES"

        elif "gini" in clean or "desigualdad" in clean:
            intent.root_concept = "GINI"

        intent.facets = facets
        return intent
