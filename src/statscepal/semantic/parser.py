"""Lexical and conceptual query parser for the CEPALSTAT semantic engine."""

import re
import unicodedata
from pydantic import BaseModel, Field

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
    polarity_info: PolarityResolution | None = None
    is_ambiguous_measure: bool = False
    ambiguous_candidate: str | None = None
    unsupported_facet: str | None = None
    unknown_concept: bool = False
    period_out_of_range: bool = False
    unsupported_frequency: bool = False
    frequency: str = "ANUAL"


class QueryParser:
    """Translates raw natural language queries into normalized conceptual intents."""

    def __init__(
        self,
        catalog_profile: str = "official_25",
        thesaurus: Thesaurus | None = None,
    ):
        self.catalog_profile = catalog_profile
        self.thesaurus = thesaurus or get_default_thesaurus()

    def parse(self, query: str) -> ParsedIntent:
        clean = strip_accents(query)
        facets: dict[str, str] = {}
        intent = ParsedIntent(raw_query=query, clean_query=clean)
        intent.polarity_info = self.thesaurus.resolve_polarity(clean)

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
        elif any(term in clean for term in ["diaria", "diario", "semana pasada"]):
            intent.unsupported_frequency = True
            intent.frequency = "DIARIA"
        elif any(term in clean for term in ["por hora", "horaria", "horario"]):
            intent.unsupported_frequency = True
            intent.frequency = "HOURLY"
        elif "trimestral" in clean or "trimestre" in clean:
            intent.frequency = "TRIMESTRAL"
        elif "mensual" in clean:
            intent.frequency = "MENSUAL"
            if "pobreza" in clean:
                intent.unsupported_frequency = True
        elif "hoy" in clean:
            intent.unsupported_frequency = True
            intent.frequency = "REALTIME"

        # ----------------------------------------------------
        # 2. Extract Year & Range Check
        # ----------------------------------------------------
        year_match = re.search(r"\b(?:ano|el\s+ano)\s+(\d{1,4})\b|\b(1\d{3}|20\d{2})\b", clean)
        if year_match:
            year_val = int(year_match.group(1) or year_match.group(2))
            intent.year = year_val
            if year_val < 1950 or year_val > 2030:
                intent.period_out_of_range = True

        # ----------------------------------------------------
        # 3. Extract Country
        # ----------------------------------------------------
        for name, code in COUNTRY_LEXICON.items():
            if re.search(r"\b" + re.escape(name) + r"\b", clean):
                intent.country_code = code
                intent.country_name = COUNTRY_NAMES[code]
                break

        # ----------------------------------------------------
        # 4. Extract Facets (with Regionalisms)
        # ----------------------------------------------------
        # Area
        area_match = self.thesaurus.match_synset("facet_area", clean)
        if area_match:
            facets["area"] = area_match.canonical_id
        elif any(term in clean for term in ["el campo", "rural", "campo", "zona rural", "area rural"]):
            facets["area"] = "RURAL"
        elif any(term in clean for term in ["ciudades", "urbano", "ciudad", "urbana", "zona urbana", "area urbana", "villas"]):
            facets["area"] = "URBANO"
        elif any(term in clean for term in ["area nacional", "total nacional", "todo el pais", "nivel nacional"]):
            facets["area"] = "NACIONAL"
        if "pobreza total" in clean and "area" not in facets:
            facets["area"] = "NACIONAL"

        # Sexo
        sexo_match = self.thesaurus.match_synset("facet_sexo", clean)
        if sexo_match:
            facets["sexo"] = sexo_match.canonical_id
        elif any(term in clean for term in ["pibas", "chicas", "mujeres", "femenina", "femenino", "mujer"]):
            facets["sexo"] = "FEMENINO"
        elif any(term in clean for term in ["pibes", "chicos", "hombres", "masculino", "varones", "hombre"]):
            facets["sexo"] = "MASCULINO"
        if "hombres y mujeres" in clean or "ambos sexos" in clean:
            facets["sexo"] = "AMBOS_SEXOS"

        # Edad (Check infancia before youth so 0 a 14 takes precedence)
        edad_matches = self.thesaurus.match_all_synsets("facet_edad", clean)
        if any(m.canonical_id == "INFANCIA" for m in edad_matches):
            facets["edad"] = "INFANCIA"
        elif edad_matches:
            facets["edad"] = edad_matches[0].canonical_id
        elif any(term in clean for term in ["ninos", "ninas", "infancia", "0 a 14", "infantil"]):
            facets["edad"] = "INFANCIA"
        elif any(term in clean for term in ["cabros", "pibes", "chavos", "chavas", "jovenes", "juventud", "15 a 24", "juvenil"]):
            facets["edad"] = "JUVENTUD"
        elif any(term in clean for term in ["tercera edad", "abuelos", "ancianos", "adultos mayores", "65 y mas"]):
            facets["edad"] = "ADULTOS_MAYORES"
        if "pibas" in clean and any(term in clean for term in ["pobreza", "desempleo", "desocupacion", "paro"]):
            facets["edad"] = "JUVENTUD"

        # Severidad de pobreza
        severidad_match = self.thesaurus.match_synset("facet_severidad", clean)
        if severidad_match:
            facets["severidad"] = severidad_match.canonical_id
        elif any(term in clean for term in ["extrema", "indigencia", "indigente", "miseria"]):
            facets["severidad"] = "POBREZA_EXTREMA"
        elif "pobreza" in clean:
            facets["severidad"] = "POBREZA_TOTAL"

        # Formalidad laboral
        formalidad_match = self.thesaurus.match_synset("facet_formalidad", clean)
        if formalidad_match:
            facets["formalidad"] = formalidad_match.canonical_id
            if formalidad_match.canonical_id == "INFORMAL" and "pobreza" in clean:
                intent.unsupported_facet = "FORMALIDAD_LABORAL"
        elif any(term in clean for term in ["en negro", "informal", "informalidad", "chamba informal"]):
            facets["formalidad"] = "INFORMAL"
            if "pobreza" in clean:
                intent.unsupported_facet = "FORMALIDAD_LABORAL"

        # Estrato (Income distribution quintiles/deciles)
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
        elif any(term in clean for term in ["carestia de comida", "alimentos", "comida", "alimentos y bebidas", "corrientazo", "morfi", "canasta alimentaria"]):
            facets["canasta"] = "ALIMENTOS"
        if "salud" in clean:
            facets["rubro"] = "SALUD"

        # ----------------------------------------------------
        # 5. Extract Root Concept & Controlled Ambiguities
        # ----------------------------------------------------
        has_pib = bool(re.search(r"\bpib\b", clean) or "producto interno bruto" in clean)

        # Ambiguous Controlled Scenarios Upfront
        if "privacion y pobreza" in clean or ("privacion" in clean and "pobreza" in clean and not intent.year):
            intent.root_concept = "POBREZA"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "PRIVATION_GAP"
        elif "desigualdad del ingreso" in clean and not any(k in facets for k in ["estrato"]):
            intent.root_concept = "DISTRIBUCION_INGRESO"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "INEQUALITY_INCOME"
        elif "brecha distributiva" in clean and not any(k in facets for k in ["estrato"]):
            intent.root_concept = "DISTRIBUCION_INGRESO"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "DISTRIBUTIVE_GAP"
        elif "situacion laboral" in clean:
            intent.root_concept = "EMPLEO"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "LABOR_SITUATION"
        elif "paro y salarios" in clean or ("desempleo y salarios" in clean):
            intent.root_concept = "EMPLEO"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "UNEMPLOYMENT_AND_WAGES"
        elif "economia de" in clean and not has_pib and not any(t in clean for t in ["crecio", "crecimiento"]):
            intent.root_concept = "PIB"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "MACRO_ECONOMY"
        elif "actividad economica en" in clean and "trimestral" not in clean and not has_pib:
            intent.root_concept = "PIB"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "ECONOMIC_ACTIVITY"
        elif "inflacion sectorial" in clean:
            intent.root_concept = "IPC_GENERAL"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "SECTORAL_INFLATION"
        elif re.search(r"\bprecios en\b", clean) and not any(t in clean for t in ["alimentos", "transporte", "energia", "morfi", "consumidor"]):
            intent.root_concept = "IPC_GENERAL"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "GENERAL_PRICES"
        elif "cuentas fiscales" in clean:
            intent.root_concept = "DEUDA_PUBLICA"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "FISCAL_ACCOUNTS"
        elif "situacion hacendaria" in clean:
            intent.root_concept = "DEUDA_PUBLICA"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "FISCAL_HEALTH"
        elif "sector externo en" in clean:
            intent.root_concept = "CUENTA_CORRIENTE"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "EXTERNAL_SECTOR"
        elif "comercio internacional y pagos" in clean:
            intent.root_concept = "CUENTA_CORRIENTE"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "INTERNATIONAL_TRADE_PAYMENTS"
        elif (
            "emisiones de gases de efecto invernadero en" in clean
            and not any(t in clean for t in ["sin", "excluyendo", "con uso"])
            and not (intent.polarity_info and intent.polarity_info.polarity_type == PolarityType.INCLUSION_EXCLUSION)
        ):
            intent.root_concept = "EMISIONES_GEI_LULUCF"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "EMISSIONS_LULUCF_CHOICE"
        elif "matriz energetica y contaminacion" in clean:
            intent.root_concept = "EMISIONES_GEI_LULUCF"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "ENERGY_POLLUTION"
        elif "situacion socioeconomica y bienestar" in clean:
            intent.root_concept = "POBREZA"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "SOCIOECONOMIC_WELLBEING"
        elif "panorama macroeconomico y fiscal" in clean:
            intent.root_concept = "PIB"
            intent.is_ambiguous_measure = True
            intent.ambiguous_candidate = "MACRO_FISCAL_PANORAMA"

        # Sector Público & Finanzas Públicas (checked first so "... % del PIB" does not shadow)
        elif any(term in clean for term in ["deuda", "endeudamiento"]):
            intent.root_concept = "DEUDA_PUBLICA"
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
        elif any(term in clean for term in ["ingresos tributarios", "recaudacion tributaria", "recaudacion", "tributar", "carga tributaria", "presion fiscal", "dian", "cuantos impuestos", "impuestos", "el fisco"]):
            intent.root_concept = "INGRESOS_TRIBUTARIOS"
        elif "gasto social" in clean:
            intent.root_concept = "GASTO_SOCIAL"
        elif "gasto publico en educacion" in clean or ("gasto" in clean and "educacion" in clean):
            intent.root_concept = "GASTO_EDUCACION"

        # Sector Externo (checked first so "... % del PIB" does not shadow)
        elif "balanza comercial" in clean:
            intent.root_concept = "BALANZA_COMERCIAL"
        elif any(term in clean for term in ["cuenta corriente", "transacciones corrientes", "deficit externo en cuenta corriente", "balanza en cuenta corriente"]):
            if "costa rica" in clean and "balanza de pagos" not in clean:
                intent.root_concept = "CUENTA_CORRIENTE_740"
            else:
                intent.root_concept = "CUENTA_CORRIENTE"
        elif "inversion extranjera" in clean or re.search(r"\bied\b", clean):
            intent.root_concept = "INVERSION_EXTRANJERA_DIRECTA"
        elif any(term in clean for term in [
            "terminos de intercambio",
            "relacion de precios del comercio exterior",
            "terminos del comercio exterior",
            "exportaciones versus importaciones",
            "lo que vendemos versus lo que compramos",
        ]):
            intent.root_concept = "TERMINOS_INTERCAMBIO"

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
        elif any(term in clean for term in ["agua dulce", "recursos hidricos", "extraccion de agua"]):
            intent.root_concept = "AGUA_DULCE"

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

        elif "corrientazo" in clean or "alimentos y bebidas" in clean or "canasta alimentaria" in clean or "morfi" in clean or "carestia de la comida" in clean:
            intent.root_concept = "IPC_ALIMENTOS"
            facets["canasta"] = "ALIMENTOS"
        elif ("inflacion de alimentos" in clean or any(term in clean for term in ["doce meses", "interanual", "carestia de comida"])) and not has_pib:
            intent.root_concept = "INFLACION_ALIMENTOS"
        elif "alimentos" in clean and any(term in clean for term in ["ipc", "inflacion", "precios"]):
            intent.root_concept = "INFLACION_ALIMENTOS" if "inflacion" in clean else "IPC_ALIMENTOS"
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

        # Cuentas Nacionales & PIB
        elif ("per capita" in clean and (has_pib or "riqueza" in clean)) or "pib per capita" in clean or "por habitante" in clean or "riqueza por cabeza" in clean:
            intent.root_concept = "PIB_PER_CAPITA"
        elif ("trimestral" in clean and (has_pib or "actividad economica" in clean or "desempeno economico" in clean)) or "crecimiento interanual trimestral" in clean:
            intent.root_concept = "PIB_TRIMESTRAL"
        elif ("corrientes" in clean or "moneda nacional" in clean) and has_pib:
            intent.root_concept = "PIB_CORRIENTE"
        elif has_pib or any(term in clean for term in ["crecio la economia", "crecimiento del pib", "crecimiento de la economia", "aparato productivo"]):
            intent.root_concept = "PIB"

        # Pobreza Brecha
        elif "brecha de pobreza" in clean or ("brecha" in clean and "pobreza" in clean and "salarial" not in clean):
            intent.root_concept = "POBREZA_BRECHA"
            if "area" not in facets:
                facets["area"] = "NACIONAL"

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
            intent.root_concept = "DISTRIBUCION_INGRESO"

        # Mercado Laboral & Pobreza & Brecha Salarial
        elif "brecha salarial" in clean:
            intent.root_concept = "BRECHA_SALARIAL"
        elif any(term in clean for term in ["cabros", "desocupacion de los pibes", "chavos sin chamba"]) and any(term in clean for term in ["sin pega", "desempleo", "desocupacion", "paro", "sin chamba"]):
            intent.root_concept = "DESEMPLEO_JUVENIL_15_24"
            facets["edad"] = "JUVENTUD"
        elif any(term in clean for term in [
            "desempleo juvenil",
            "desempleo de los jovenes",
            "desempleo de mujeres jovenes",
            "desempleo juvenil masculino",
            "jovenes sin chamba",
        ]):
            intent.root_concept = "DESEMPLEO_JUVENIL"
            facets["edad"] = "JUVENTUD"
        elif any(term in clean for term in ["chamba", "camello", "sin pega", "sin laburo", "jale"]):
            intent.root_concept = "EMPLEO"
            if "sexo" not in facets:
                facets["sexo"] = "TOTAL" if self.catalog_profile == "legacy_50" else "AMBOS"
        elif any(term in clean for term in ["pobreza", "miseria", "indigencia", "no tienen un sope", "malaria economica"]):
            intent.root_concept = "POBREZA"
            if "area" not in facets:
                facets["area"] = "NACIONAL"
            if "femenina" in clean and "edad" not in facets and facets.get("area") == "NACIONAL" and not intent.year:
                intent.is_ambiguous_measure = True
                intent.ambiguous_candidate = "FEMININITY_INDEX"
        elif any(term in clean for term in ["desempleo", "desocupacion", "paro", "desocupacion abierta"]):
            intent.root_concept = "EMPLEO"
            if "sexo" not in facets:
                facets["sexo"] = "TOTAL" if self.catalog_profile == "legacy_50" else "AMBOS"
            if "urbano" in clean and "edad" not in facets and not intent.year:
                intent.is_ambiguous_measure = True
                intent.ambiguous_candidate = "URBAN_UNEMPLOYMENT"

        # Income Modifiers & Deconstruction
        elif any(term in clean for term in ["salario", "sueldo", "plata", "guita", "lana", "lucas", "ingreso", "ingresos", "remuneracion", "remuneraciones", "billete"]):
            if any(term in clean for term in ["minima", "minimo", "por ley", "sueldo basico", "salario basico", "basico de ley", "basico"]):
                intent.root_concept = "SALARIO_MINIMO"
            elif any(term in clean for term in ["hogar", "hogares", "familias", "familia", "por cabeza", "per capita"]) and not has_pib:
                intent.root_concept = "INGRESO_HOGARES"
            elif "laboral" in clean:
                intent.root_concept = "INGRESO_LABORAL"
            elif facets.get("edad") == "JUVENTUD":
                intent.root_concept = "SALARIO"
            elif any(term in clean for term in ["laburantes", "trabajadores", "trabajadores rasos", "asalariados", "medio", "remuneraciones", "promedio"]):
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
