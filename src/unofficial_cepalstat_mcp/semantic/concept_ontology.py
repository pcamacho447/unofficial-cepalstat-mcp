"""Declarative Concept Models & Ontology Engine for CEPALSTAT Semantic Resolution.

Provides declarative Pydantic models for concepts, triggers, sub-concept rules,
and ambiguities, along with a high-performance precompiled matching engine.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConceptTriggerRule(BaseModel):
    """Lexical trigger rule mapping query phrases or regex patterns to a concept."""

    model_config = ConfigDict(frozen=True)

    patterns: tuple[str, ...]
    is_regex: bool = False
    exact_word_boundary: bool = True
    ambiguous_candidate: str | None = None
    requires_subterms: tuple[str, ...] = ()
    excludes_subterms: tuple[str, ...] = ()


class SubConceptRule(BaseModel):
    """Refinement rule to specialize a matched base concept into a sub-concept."""

    model_config = ConfigDict(frozen=True)

    sub_concept_key: str
    triggers: tuple[str, ...]
    is_ambiguous: bool = False
    ambiguous_candidate: str | None = None
    facet_updates: dict[str, str] = Field(default_factory=dict)


class ConceptDefinition(BaseModel):
    """Declarative specification of a canonical socioeconomic concept in CEPALSTAT."""

    model_config = ConfigDict(frozen=True)

    concept_key: str
    description: str
    domain: str
    priority: int = 100
    default_indicator_id: int | None = None
    default_facets: dict[str, str] = Field(default_factory=dict)
    triggers: tuple[ConceptTriggerRule, ...] = ()
    sub_concept_rules: tuple[SubConceptRule, ...] = ()
    controlled_ambiguities: dict[str, str] = Field(default_factory=dict)
    associated_phrases: tuple[str, ...] = ()


class ConceptMatchResult(BaseModel):
    """Outcome of resolving a natural language query to a canonical concept."""

    concept_key: str
    matched_phrase: str
    consumed_phrases: list[str] = Field(default_factory=list)
    is_ambiguous_measure: bool = False
    ambiguous_candidate: str | None = None
    suggested_facets: dict[str, str] = Field(default_factory=dict)


@dataclass(slots=True)
class _CompiledTrigger:
    concept_def: ConceptDefinition
    trigger_rule: ConceptTriggerRule
    compiled_regex: re.Pattern[str]
    priority: int
    max_pattern_len: int


@dataclass(slots=True)
class _CompiledSubRule:
    rule: SubConceptRule
    compiled_regex: re.Pattern[str]


# ==============================================================================
# Default Concept Definitions (All 22+ Canonical CEPALSTAT Concepts & Regionalisms)
# ==============================================================================

DEFAULT_CONCEPT_DEFINITIONS: list[ConceptDefinition] = [
    # --------------------------------------------------------------------------
    # Fiscal: Education & Social Spending (Priorities 170 & 160)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="GASTO_EDUCACION",
        description="Public expenditure on education",
        domain="fiscal",
        priority=170,
        default_indicator_id=460,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "gasto publico en educacion",
                    "gasto en educacion",
                    "presupuesto en educacion",
                    "presupuesto educativo",
                    "inversion publica en educacion",
                ),
            ),
            ConceptTriggerRule(
                patterns=("gasto", "presupuesto"),
                requires_subterms=("educacion", "educativo"),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="GASTO_SOCIAL",
        description="Public social expenditure (health, social protection, general)",
        domain="fiscal",
        priority=160,
        default_indicator_id=4410,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "gasto publico social",
                    "gasto social",
                    "gasto publico en salud",
                    "gasto en salud",
                    "gasto publico",
                ),
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="GASTO_SOCIAL",
                triggers=("salud", "sanitario", "atencion medica"),
                facet_updates={"funcion": "SALUD"},
            ),
            SubConceptRule(
                sub_concept_key="GASTO_SOCIAL",
                triggers=("educacion", "educativo"),
                facet_updates={"funcion": "EDUCACION"},
            ),
            SubConceptRule(
                sub_concept_key="GASTO_SOCIAL",
                triggers=("proteccion social", "seguridad social"),
                facet_updates={"funcion": "PROTECCION_SOCIAL"},
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # Fiscal: Debt, Primary Balance, Tax Revenues (Priority 150)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="DEUDA_PUBLICA",
        description="Central government public debt",
        domain="fiscal",
        priority=150,
        default_indicator_id=1240,
        associated_phrases=("gobierno central", "gobierno", "estado"),
        controlled_ambiguities={
            "cuentas fiscales": "FISCAL_ACCOUNTS",
            "situacion hacendaria": "FISCAL_HEALTH",
        },
        triggers=(
            ConceptTriggerRule(
                patterns=("cuentas fiscales",),
                ambiguous_candidate="FISCAL_ACCOUNTS",
            ),
            ConceptTriggerRule(
                patterns=("situacion hacendaria",),
                ambiguous_candidate="FISCAL_HEALTH",
            ),
            ConceptTriggerRule(
                patterns=(
                    "endeudamiento soberano",
                    "deuda publica",
                    "deuda soberana",
                    "endeudamiento del estado",
                    "deuda del gobierno",
                    "endeudamiento publico",
                    "endeudamiento",
                    "deuda",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="BALANCE_PRIMARIO",
        description="Central government primary balance / overall fiscal balance",
        domain="fiscal",
        priority=150,
        default_indicator_id=1246,
        associated_phrases=("gobierno central", "gobierno", "pago de intereses"),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "balance primario fiscal",
                    "resultado fiscal primario",
                    "balance primario",
                    "superavit primario",
                    "deficit primario",
                    "superavit fiscal",
                    "deficit fiscal",
                    "rojo fiscal",
                    "rojo primario",
                    "resultado primario",
                    "balance fiscal",
                ),
                excludes_subterms=("cuenta corriente", "comercial", "balanza", "comercio"),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="INGRESOS_TRIBUTARIOS",
        description="Central government tax revenue",
        domain="fiscal",
        priority=150,
        default_indicator_id=821,
        associated_phrases=("gobierno central", "gobierno", "el fisco"),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "ingresos tributarios",
                    "recaudacion tributaria",
                    "carga tributaria",
                    "presion fiscal tributaria",
                    "presion fiscal",
                    "cuantos impuestos",
                    "recaudacion",
                    "tributar",
                    "dian",
                    "el fisco",
                    "impuestos",
                ),
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="INGRESOS_TRIBUTARIOS_CORRIENTES",
                triggers=(
                    "moneda nacional",
                    "precios corrientes",
                    "moneda local",
                    "en pesos",
                    "en soles",
                    "en reales",
                    "nominales",
                    "nominal",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="INGRESOS_TRIBUTARIOS_CORRIENTES",
        description="Central government tax revenue in current national currency",
        domain="fiscal",
        priority=150,
        default_indicator_id=845,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "ingresos tributarios en moneda nacional",
                    "ingresos tributarios a precios corrientes",
                    "recaudacion tributaria en moneda nacional",
                    "recaudacion en precios corrientes",
                ),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # External Sector (Priorities 145 & 140)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="BALANZA_COMERCIAL",
        description="Trade balance (goods exports minus imports)",
        domain="externo",
        priority=145,
        default_indicator_id=2050,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "balanza comercial",
                    "superavit comercial",
                    "deficit comercial",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="CUENTA_CORRIENTE",
        description="Balance of payments current account",
        domain="externo",
        priority=140,
        default_indicator_id=740,
        controlled_ambiguities={
            "sector externo en": "EXTERNAL_SECTOR",
            "sector externo": "EXTERNAL_SECTOR",
            "comercio internacional y pagos": "INTERNATIONAL_TRADE_PAYMENTS",
        },
        triggers=(
            ConceptTriggerRule(
                patterns=("comercio internacional y pagos",),
                ambiguous_candidate="INTERNATIONAL_TRADE_PAYMENTS",
            ),
            ConceptTriggerRule(
                patterns=("sector externo en", "sector externo"),
                ambiguous_candidate="EXTERNAL_SECTOR",
            ),
            ConceptTriggerRule(
                patterns=(
                    "deficit externo en cuenta corriente",
                    "balanza en cuenta corriente",
                    "transacciones corrientes",
                    "cuenta corriente",
                    "deficit externo",
                ),
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="CUENTA_CORRIENTE_740",
                triggers=("costa rica",),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="INVERSION_EXTRANJERA_DIRECTA",
        description="Foreign direct investment inflows (FDI / IED)",
        domain="externo",
        priority=140,
        default_indicator_id=4231,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "inversion extranjera directa",
                    "inversion extranjera",
                    "ied",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="TERMINOS_INTERCAMBIO",
        description="Terms of trade index of goods",
        domain="externo",
        priority=140,
        default_indicator_id=883,
        associated_phrases=("bienes", "comercio exterior"),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "terminos de intercambio comercial",
                    "terminos de intercambio",
                    "intercambio comercial",
                    "relacion de precios del comercio exterior",
                    "terminos del comercio exterior",
                    "exportaciones versus importaciones",
                    "lo que vendemos versus lo que compramos",
                    "relacion de intercambio",
                ),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # Labor & Gender: Wage Gap (Priority 135)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="BRECHA_SALARIAL",
        description="Gender wage gap and labor income ratio women/men",
        domain="laboral",
        priority=135,
        default_indicator_id=2288,
        associated_phrases=(
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
            "genero",
            "mujeres",
            "hombres",
            "sexo",
            "laboral",
            "laborales",
            "salarial",
            "salariales",
            "trabajadores",
        ),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "brecha salarial",
                    "brecha de genero",
                    "brecha de ingresos",
                    "brecha de ingreso",
                    "relacion de ingreso",
                    "relacion de ingresos",
                    "relacion del ingreso",
                    "diferencia de ingresos entre",
                    "diferencia salarial entre",
                    "diferencia de salario entre",
                ),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # Environment: Renewable Energy, GHG Emissions, Freshwater (Priority 130)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="ENERGIA_RENOVABLE",
        description="Renewable electricity generation and clean energy share",
        domain="ambiental",
        priority=130,
        default_indicator_id=3154,
        associated_phrases=("generacion electrica", "electrica", "contaminamos"),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "generacion electrica renovable",
                    "porcentaje de energias limpias",
                    "proporcion de renovables",
                    "energias limpias",
                    "energia limpia",
                    "matriz electrica",
                    "luz verde",
                    "enchufes",
                    "renovables",
                    "renovable",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="EMISIONES_GEI_LULUCF",
        description="Greenhouse gas emissions including LULUCF/UTCUTS",
        domain="ambiental",
        priority=130,
        default_indicator_id=5681,
        associated_phrases=("carbono",),
        controlled_ambiguities={
            "emisiones de gases de efecto invernadero en": "EMISSIONS_LULUCF_CHOICE",
            "matriz energetica y contaminacion": "ENERGY_POLLUTION",
        },
        triggers=(
            ConceptTriggerRule(
                patterns=("matriz energetica y contaminacion",),
                ambiguous_candidate="ENERGY_POLLUTION",
            ),
            ConceptTriggerRule(
                patterns=("emisiones de gases de efecto invernadero en",),
                ambiguous_candidate="EMISSIONS_LULUCF_CHOICE",
                excludes_subterms=("sin", "excluyendo", "con uso"),
            ),
            ConceptTriggerRule(
                patterns=(
                    "emisiones de gases de efecto invernadero",
                    "gases de efecto invernadero",
                    "gases de invernadero",
                    "huella de carbono",
                    "emisiones totales",
                    "emisiones netas",
                    "emisiones brutas",
                    "emisiones",
                    "gei",
                ),
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="EMISIONES_GEI_SIN_LULUCF",
                triggers=(
                    "sin lulucf",
                    "sin utcuts",
                    "excluyendo utcuts",
                    "excluyendo sector utcuts",
                    "sin uso de la tierra",
                    "sin cambio de uso",
                    "sin considerar bosques",
                    "excluyendo el sector uso de la tierra",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="EMISIONES_GEI_SIN_LULUCF",
        description="Greenhouse gas emissions excluding LULUCF/UTCUTS",
        domain="ambiental",
        priority=130,
        default_indicator_id=5682,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "emisiones sin lulucf",
                    "emisiones sin utcuts",
                    "emisiones excluyendo utcuts",
                    "gei sin lulucf",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="AGUA_DULCE",
        description="Freshwater extraction and water resources",
        domain="ambiental",
        priority=130,
        default_indicator_id=4185,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "extraccion de agua dulce",
                    "extraccion de agua",
                    "recursos hidricos",
                    "agua dulce",
                ),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # Prices & Inflation (Priorities 125 & 120)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="IPC_TRANSPORTE_ENERGIA",
        description="Consumer price index: transport and energy fuels",
        domain="precios",
        priority=125,
        default_indicator_id=365,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "transporte y energia",
                    "combustibles",
                    "combustible",
                    "tarifas de luz",
                    "electricidad",
                    "gasolina",
                    "bencina",
                    "diesel",
                    "gasoil",
                    "nafta",
                    "transporte",
                    "energia",
                ),
                requires_subterms=(
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
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="IPC_ALIMENTOS",
        description="Consumer price index: food and non-alcoholic beverages",
        domain="precios",
        priority=126,
        default_indicator_id=2929,
        default_facets={"canasta": "ALIMENTOS"},
        associated_phrases=(
            "corrientazo",
            "alimentos y bebidas",
            "canasta alimentaria",
            "morfi",
            "carestia de la comida",
        ),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "alimentos y bebidas",
                    "canasta alimentaria",
                    "carestia de la comida",
                    "corrientazo",
                    "morfi",
                ),
            ),
            ConceptTriggerRule(
                patterns=("alimentos",),
                requires_subterms=("ipc", "precios", "precio", "costo"),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="INFLACION_ALIMENTOS",
        description="Annual 12-month food inflation rate",
        domain="precios",
        priority=125,
        default_indicator_id=2929,
        default_facets={"canasta": "ALIMENTOS"},
        associated_phrases=(
            "inflacion de alimentos",
            "doce meses",
            "interanual",
            "carestia de comida",
            "alimentos",
        ),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "inflacion de alimentos",
                    "carestia de comida",
                    "doce meses",
                ),
                excludes_subterms=("pib", "pbi"),
            ),
            ConceptTriggerRule(
                patterns=("interanual",),
                requires_subterms=("alimentos", "ipc", "canasta", "comida"),
                excludes_subterms=("pib", "pbi", "trimestral"),
            ),
            ConceptTriggerRule(
                patterns=("alimentos",),
                requires_subterms=("inflacion", "interanual", "doce meses"),
                excludes_subterms=("pib", "pbi"),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="IPC_SUBYACENTE",
        description="Core / underlying consumer price inflation",
        domain="precios",
        priority=125,
        default_indicator_id=4145,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "inflacion subyacente",
                    "precios subyacentes",
                    "ipc subyacente",
                    "inflacion basica",
                    "inflacion core",
                    "core inflation",
                    "core anual",
                    "subyacente",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="IPC_GENERAL",
        description="General Consumer Price Index (CPI) and headline inflation",
        domain="precios",
        priority=120,
        default_indicator_id=2484,
        associated_phrases=("precios",),
        controlled_ambiguities={
            "inflacion sectorial": "SECTORAL_INFLATION",
            "precios en": "GENERAL_PRICES",
        },
        triggers=(
            ConceptTriggerRule(
                patterns=("inflacion sectorial",),
                ambiguous_candidate="SECTORAL_INFLATION",
            ),
            ConceptTriggerRule(
                patterns=("precios en",),
                ambiguous_candidate="GENERAL_PRICES",
                excludes_subterms=("alimentos", "transporte", "energia", "morfi", "consumidor"),
            ),
            ConceptTriggerRule(
                patterns=(
                    "precios al consumidor",
                    "costo de la vida",
                    "costo de vida",
                    "inflacion general",
                    "tasa de inflacion",
                    "inflacion",
                    "ipc",
                ),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # Labor: Youth Unemployment & Poverty Gap (Priority 115)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="DESEMPLEO_JUVENIL",
        description="Youth unemployment rate (15-24 years)",
        domain="laboral",
        priority=115,
        default_indicator_id=5097,
        default_facets={"edad": "JUVENTUD"},
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "desempleo de mujeres jovenes",
                    "desempleo juvenil masculino",
                    "desempleo de los jovenes",
                    "desempleo juvenil",
                    "jovenes sin chamba",
                ),
            ),
            ConceptTriggerRule(
                patterns=("cabros", "desocupacion de los pibes", "chavos sin chamba"),
                requires_subterms=("sin pega", "desempleo", "desocupacion", "paro", "sin chamba"),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="POBREZA_BRECHA",
        description="Poverty gap index (FGT1)",
        domain="pobreza",
        priority=115,
        default_indicator_id=3329,
        default_facets={"area": "NACIONAL"},
        triggers=(
            ConceptTriggerRule(
                patterns=("brecha de pobreza",),
            ),
            ConceptTriggerRule(
                patterns=("brecha",),
                requires_subterms=("pobreza",),
                excludes_subterms=("salarial", "genero"),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # Inequality & Income Distribution (Priority 110)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="DISTRIBUCION_INGRESO",
        description="Income distribution by quintiles/deciles and income concentration",
        domain="pobreza",
        priority=110,
        default_indicator_id=3324,
        controlled_ambiguities={
            "desigualdad del ingreso": "INEQUALITY_INCOME",
            "brecha distributiva": "DISTRIBUTIVE_GAP",
        },
        triggers=(
            ConceptTriggerRule(
                patterns=("desigualdad del ingreso",),
                ambiguous_candidate="INEQUALITY_INCOME",
            ),
            ConceptTriggerRule(
                patterns=("brecha distributiva",),
                ambiguous_candidate="DISTRIBUTIVE_GAP",
            ),
            ConceptTriggerRule(
                patterns=(
                    "distribucion de los ingresos",
                    "distribucion del ingreso",
                    "distribucion de la lana",
                    "concentracion del ingreso",
                    "20 por ciento mas rico",
                    "reparto del billete",
                    "los de abajo",
                    "cuanta torta",
                    "quintiles",
                    "quintil",
                    "deciles",
                    "decil",
                ),
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="POBLACION",
                triggers=(
                    "poblacion",
                    "habitantes",
                    "personas",
                    "indigena",
                    "afrodescendiente",
                    "demografia",
                    "demografico",
                    "demograficos",
                ),
                facet_updates={"estrato": "QUINTIL"},
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="GINI",
        description="Gini inequality coefficient",
        domain="pobreza",
        priority=110,
        default_indicator_id=3289,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "coeficiente de gini",
                    "indice de gini",
                    "desigualdad",
                    "gini",
                ),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # National Accounts: GDP Sub-Concepts (Priority 105)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="PIB_PER_CAPITA",
        description="Gross Domestic Product per capita",
        domain="macro",
        priority=105,
        default_indicator_id=2206,
        associated_phrases=("por cabeza", "riqueza"),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "producto interno bruto per capita",
                    "producto bruto interno per capita",
                    "pib per capita",
                    "pbi per capita",
                    "pib por habitante",
                    "pbi por habitante",
                    "riqueza por cabeza",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="PIB_TRIMESTRAL",
        description="Quarterly GDP growth rate (year-on-year)",
        domain="macro",
        priority=105,
        default_indicator_id=286,
        associated_phrases=(
            "trimestral",
            "crecimiento interanual trimestral",
            "actividad economica",
            "desempeno economico",
        ),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "crecimiento interanual trimestral",
                    "pib trimestral",
                    "pbi trimestral",
                ),
            ),
            ConceptTriggerRule(
                patterns=("actividad economica", "desempeno economico"),
                requires_subterms=("trimestral",),
            ),
            ConceptTriggerRule(
                patterns=("trimestral",),
                requires_subterms=("actividad economica", "desempeno economico", "pib", "pbi"),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="PIB_CORRIENTE",
        description="Gross Domestic Product in current national currency",
        domain="macro",
        priority=105,
        default_indicator_id=2193,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "pib a precios corrientes",
                    "pbi a precios corrientes",
                    "pib en moneda nacional",
                    "pbi en moneda nacional",
                    "pib corriente",
                    "pbi corriente",
                ),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # Labor: Wages & Income (Priority 105)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="SALARIO_MINIMO",
        description="Real minimum wage index",
        domain="laboral",
        priority=105,
        default_indicator_id=340,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "salario minimo de ley",
                    "sueldo basico de ley",
                    "salario minimo",
                    "sueldo minimo",
                    "salario basico",
                    "sueldo basico",
                    "basico de ley",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="INGRESO_HOGARES",
        description="Household income per capita",
        domain="laboral",
        priority=105,
        default_indicator_id=2198,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "ingreso de los hogares",
                    "ingreso de hogares",
                    "ingresos familiares",
                    "ingreso familiar",
                    "ingreso por hogar",
                ),
                excludes_subterms=("pib", "pbi"),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="INGRESO_LABORAL",
        description="Mean monthly labor income",
        domain="laboral",
        priority=105,
        default_indicator_id=2287,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "ingresos laborales",
                    "ingreso laboral",
                    "remuneracion laboral",
                ),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="SALARIO_REAL",
        description="Real average wage index and general compensation",
        domain="laboral",
        priority=105,
        default_indicator_id=341,
        associated_phrases=(
            "salario",
            "sueldo",
            "plata",
            "guita",
            "lana",
            "lucas",
            "ingreso",
            "ingresos",
            "remuneracion",
            "remuneraciones",
            "billete",
            "por cabeza",
            "per capita",
        ),
        controlled_ambiguities={
            "remuneraciones": "INCOME_MEASURES",
            "salario": "INCOME_MEASURES",
            "sueldo": "INCOME_MEASURES",
            "plata": "INCOME_MEASURES",
            "guita": "INCOME_MEASURES",
            "lucas": "INCOME_MEASURES",
            "lana": "INCOME_MEASURES",
            "billete": "INCOME_MEASURES",
            "ingresos": "INCOME_MEASURES",
            "ingreso": "INCOME_MEASURES",
        },
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "remuneraciones medias",
                    "remuneracion media",
                    "salarios reales",
                    "sueldos reales",
                    "salario real",
                    "sueldo real",
                    "salario medio",
                    "sueldo medio",
                ),
            ),
            # Slang / unmodified income trigger flagged as ambiguous
            ConceptTriggerRule(
                patterns=(
                    "remuneraciones",
                    "remuneracion",
                    "salarios",
                    "salario",
                    "sueldos",
                    "sueldo",
                    "ingresos",
                    "ingreso",
                    "billete",
                    "lucas",
                    "guita",
                    "plata",
                    "lana",
                ),
                ambiguous_candidate="INCOME_MEASURES",
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="SALARIO_MINIMO",
                triggers=(
                    "minima",
                    "minimo",
                    "por ley",
                    "sueldo basico",
                    "salario basico",
                    "basico de ley",
                    "basico",
                ),
            ),
            SubConceptRule(
                sub_concept_key="INGRESO_HOGARES",
                triggers=("hogar", "hogares", "familias", "familia", "por cabeza", "per capita"),
            ),
            SubConceptRule(
                sub_concept_key="INGRESO_LABORAL",
                triggers=("laboral",),
            ),
            SubConceptRule(
                sub_concept_key="SALARIO_REAL",
                triggers=(
                    "salario real",
                    "sueldo real",
                    "salarios reales",
                    "real",
                    "reales",
                    "laburantes",
                    "trabajadores rasos",
                    "trabajadores",
                    "asalariados",
                    "medio",
                    "promedio",
                ),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # Macro & Labor & Poverty: Base Concepts (Priority 100)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="PIB",
        description="Gross Domestic Product (GDP / PBI)",
        domain="macro",
        priority=100,
        default_indicator_id=2204,
        associated_phrases=("final del gobierno", "de gobierno", "del gobierno"),
        controlled_ambiguities={
            "actividad economica en": "ECONOMIC_ACTIVITY",
            "actividad economica": "ECONOMIC_ACTIVITY",
            "economia de": "MACRO_ECONOMY",
            "panorama macroeconomico y fiscal": "MACRO_FISCAL_PANORAMA",
        },
        triggers=(
            ConceptTriggerRule(
                patterns=("panorama macroeconomico y fiscal",),
                ambiguous_candidate="MACRO_FISCAL_PANORAMA",
            ),
            ConceptTriggerRule(
                patterns=("actividad economica en", "actividad economica"),
                ambiguous_candidate="ECONOMIC_ACTIVITY",
                excludes_subterms=(
                    "trimestral",
                    "pib",
                    "pbi",
                    "sector",
                    "sectores",
                    "rama",
                    "ramas",
                    "ocupada",
                    "ocupadas",
                    "ocupado",
                    "ocupados",
                    "ocupacion",
                    "empleo",
                    "trabajadores",
                    "poblacion",
                ),
            ),
            ConceptTriggerRule(
                patterns=("economia de",),
                ambiguous_candidate="MACRO_ECONOMY",
                excludes_subterms=("crecio", "crecimiento", "pib", "pbi"),
            ),
            ConceptTriggerRule(
                patterns=(
                    "crecimiento de la economia",
                    "crecimiento del pib",
                    "crecimiento del pbi",
                    "producto interno bruto",
                    "producto bruto interno",
                    "consumo final del gobierno",
                    "consumo de gobierno",
                    "consumo del gobierno",
                    "crecio la economia",
                    "aparato productivo",
                    "riqueza por cabeza",
                    "por habitante",
                    "pib",
                    "pbi",
                ),
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="PIB_PER_CAPITA",
                triggers=("per capita", "por habitante", "riqueza por cabeza", "por cabeza"),
            ),
            SubConceptRule(
                sub_concept_key="PIB_TRIMESTRAL",
                triggers=("trimestral", "crecimiento interanual trimestral"),
            ),
            SubConceptRule(
                sub_concept_key="PIB_CORRIENTE",
                triggers=("corrientes", "moneda nacional", "precios corrientes"),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="EMPLEO",
        description="Employment, labor participation, and open unemployment",
        domain="laboral",
        priority=100,
        default_indicator_id=127,
        controlled_ambiguities={
            "situacion laboral": "LABOR_SITUATION",
            "paro y salarios": "UNEMPLOYMENT_AND_WAGES",
            "desempleo y salarios": "UNEMPLOYMENT_AND_WAGES",
            "urbano": "URBAN_UNEMPLOYMENT",
        },
        triggers=(
            ConceptTriggerRule(
                patterns=("situacion laboral",),
                ambiguous_candidate="LABOR_SITUATION",
            ),
            ConceptTriggerRule(
                patterns=("paro y salarios", "desempleo y salarios"),
                ambiguous_candidate="UNEMPLOYMENT_AND_WAGES",
            ),
            ConceptTriggerRule(
                patterns=(
                    "tasa de desocupacion abierta",
                    "tasa de desocupacion",
                    "desocupacion abierta",
                    "tasa de desempleo",
                    "sin laburo",
                    "sin pega",
                    "desocupacion",
                    "desempleo",
                    "camello",
                    "chamba",
                    "jale",
                    "paro",
                ),
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="EMPLEO",
                triggers=("urbano", "desocupacion urbana"),
                is_ambiguous=True,
                ambiguous_candidate="URBAN_UNEMPLOYMENT",
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="POBREZA",
        description="Poverty and extreme poverty headcount ratios",
        domain="pobreza",
        priority=100,
        default_indicator_id=3328,
        default_facets={"area": "NACIONAL"},
        controlled_ambiguities={
            "privacion y pobreza": "PRIVATION_GAP",
            "situacion socioeconomica y bienestar": "SOCIOECONOMIC_WELLBEING",
            "femenina": "FEMININITY_INDEX",
        },
        triggers=(
            ConceptTriggerRule(
                patterns=("privacion y pobreza",),
                ambiguous_candidate="PRIVATION_GAP",
            ),
            ConceptTriggerRule(
                patterns=("privacion",),
                requires_subterms=("pobreza",),
                ambiguous_candidate="PRIVATION_GAP",
            ),
            ConceptTriggerRule(
                patterns=("situacion socioeconomica y bienestar",),
                ambiguous_candidate="SOCIOECONOMIC_WELLBEING",
            ),
            ConceptTriggerRule(
                patterns=(
                    "malaria economica",
                    "no tienen un sope",
                    "linea de pobreza",
                    "pobreza extrema",
                    "miseria extrema",
                    "indigencia",
                    "pobreza",
                    "miseria",
                ),
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="POBREZA",
                triggers=("femenina",),
                is_ambiguous=True,
                ambiguous_candidate="FEMININITY_INDEX",
            ),
            SubConceptRule(
                sub_concept_key="POBREZA_BRECHA",
                triggers=("brecha",),
            ),
        ),
    ),
    ConceptDefinition(
        concept_key="OCUPACION",
        description="Employed population and occupational distribution (población ocupada)",
        domain="laboral",
        priority=105,
        default_indicator_id=417,
        associated_phrases=(
            "distribucion de la poblacion ocupada",
            "distribucion de poblacion ocupada",
            "poblacion ocupada",
        ),
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "distribucion de la poblacion ocupada",
                    "distribucion de poblacion ocupada",
                    "poblacion ocupada",
                    "personas ocupadas",
                    "tasa de ocupacion",
                    "nivel de ocupacion",
                    "ocupacion por sector",
                    "ocupacion segun sector",
                ),
                excludes_subterms=(
                    "carcelaria",
                    "carcel",
                    "penitenciaria",
                    "hotelera",
                    "camas",
                    "hospitalaria",
                    "camas uci",
                    "hacinamiento",
                ),
            ),
        ),
        sub_concept_rules=(
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("mineria", "minero", "minera"),
                facet_updates={"actividad": "MINERIA"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("comercio", "comercial"),
                facet_updates={"actividad": "COMERCIO"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("construccion",),
                facet_updates={"actividad": "CONSTRUCCION"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("transporte", "transportes"),
                facet_updates={"actividad": "TRANSPORTE"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("servicios financieros", "financiero", "financiera", "financieros"),
                facet_updates={"actividad": "FINANCIERO"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("electricidad, gas y agua", "electricidad"),
                facet_updates={"actividad": "ELECTRICIDAD"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("agricultura", "agropecuario", "agropecuaria", "agricola"),
                facet_updates={"actividad": "AGRICULTURA"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("industria", "industrial", "manufactura", "manufactureras", "manufacturas"),
                facet_updates={"actividad": "INDUSTRIA"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("otros servicios",),
                facet_updates={"actividad": "OTROS_SERVICIOS"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=("servicios", "sector terciario"),
                facet_updates={"actividad": "SERVICIOS"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=(
                    "sector de actividad",
                    "sectores de actividad",
                    "sector economico",
                    "sectores economicos",
                    "grandes sectores",
                    "rama",
                    "ramas",
                ),
                facet_updates={"actividad": "ACTIVIDAD_DESGLOSE"},
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=(
                    "categoria ocupacional",
                    "categoria de trabajo",
                ),
            ),
            SubConceptRule(
                sub_concept_key="OCUPACION",
                triggers=(
                    "insercion laboral",
                    "tipo de insercion laboral",
                ),
            ),
        ),
    ),
    # --------------------------------------------------------------------------
    # Demography: Population (Priority 90)
    # --------------------------------------------------------------------------
    ConceptDefinition(
        concept_key="POBLACION",
        description="Total population and demographic estimates",
        domain="demografia",
        priority=90,
        default_indicator_id=4788,
        triggers=(
            ConceptTriggerRule(
                patterns=(
                    "poblacion total",
                    "demograficos",
                    "demografico",
                    "demografia",
                    "habitantes",
                    "poblacion",
                ),
                excludes_subterms=(
                    "ocupada",
                    "ocupadas",
                    "ocupado",
                    "ocupados",
                    "ocupacion",
                    "desocupada",
                    "desocupadas",
                    "desocupados",
                    "activa",
                    "activas",
                    "economicamente activa",
                ),
            ),
        ),
    ),
]


# ==============================================================================
# Concept Ontology Engine
# ==============================================================================


class ConceptOntology:
    """Declarative ontology and classification registry for CEPALSTAT concepts."""

    def __init__(
        self,
        definitions: Sequence[ConceptDefinition] | Mapping[str, ConceptDefinition] | None = None,
    ) -> None:
        if definitions is None:
            self._definitions: tuple[ConceptDefinition, ...] = tuple(DEFAULT_CONCEPT_DEFINITIONS)
        elif isinstance(definitions, Mapping):
            self._definitions = tuple(definitions.values())
        else:
            self._definitions = tuple(definitions)

        self._concept_map: dict[str, ConceptDefinition] = {
            d.concept_key: d for d in self._definitions
        }

        # Index associated phrases per concept for consumed_phrases collection
        self._concept_associated_phrases: dict[str, tuple[str, ...]] = {}
        for cdef in self._definitions:
            phrases: list[str] = list(cdef.associated_phrases)
            for tr in cdef.triggers:
                if not tr.is_regex:
                    phrases.extend(tr.patterns)
                    phrases.extend(tr.requires_subterms)
            for sub in cdef.sub_concept_rules:
                phrases.extend(sub.triggers)
            # Sort descending by length so longer phrases are consumed first
            sorted_phrases = tuple(sorted(set(phrases), key=len, reverse=True))
            self._concept_associated_phrases[cdef.concept_key] = sorted_phrases

        # Precompile sub-concept rules per concept
        self._compiled_sub_rules: dict[str, list[_CompiledSubRule]] = {}
        for cdef in self._definitions:
            compiled_subs: list[_CompiledSubRule] = []
            for sub_rule in cdef.sub_concept_rules:
                if not sub_rule.triggers:
                    continue
                sorted_trigs = sorted(sub_rule.triggers, key=len, reverse=True)
                escaped_trigs = [re.escape(t) for t in sorted_trigs]
                sub_regex = re.compile(rf"\b(?:{'|'.join(escaped_trigs)})\b", re.IGNORECASE)
                compiled_subs.append(_CompiledSubRule(rule=sub_rule, compiled_regex=sub_regex))
            self._compiled_sub_rules[cdef.concept_key] = compiled_subs

        # Precompile triggers sorted by descending priority, then descending pattern length
        self._compiled_rules: list[_CompiledTrigger] = self._compile_triggers()

    def _compile_triggers(self) -> list[_CompiledTrigger]:
        raw_list: list[_CompiledTrigger] = []
        for cdef in self._definitions:
            for tr in cdef.triggers:
                if not tr.patterns:
                    continue
                sorted_patterns = sorted(tr.patterns, key=len, reverse=True)
                if tr.is_regex:
                    regex_pat = f"(?:{'|'.join(sorted_patterns)})"
                else:
                    escaped_parts = [re.escape(p) for p in sorted_patterns]
                    inner = f"(?:{'|'.join(escaped_parts)})"
                    regex_pat = rf"\b{inner}\b" if tr.exact_word_boundary else inner

                compiled = re.compile(regex_pat, re.IGNORECASE)
                raw_list.append(
                    _CompiledTrigger(
                        concept_def=cdef,
                        trigger_rule=tr,
                        compiled_regex=compiled,
                        priority=cdef.priority,
                        max_pattern_len=max(len(p) for p in tr.patterns),
                    )
                )

        # Sort rules strictly by descending priority, then descending pattern length
        raw_list.sort(key=lambda item: (-item.priority, -item.max_pattern_len))
        return raw_list

    def extract_concept(
        self,
        clean_query: str,
        thesaurus: Any | None = None,
        facets: dict[str, str] | None = None,
        year: int | None = None,
        catalog_profile: str = "official_25",
        polarity_info: Any | None = None,
    ) -> ConceptMatchResult | None:
        """Extract canonical concept, sub-concepts, and controlled ambiguities.

        Args:
            clean_query: Normalized lowercase query string without diacritics.
            thesaurus: Optional semantic thesaurus for synset queries.
            facets: Optional extracted facet mappings.
            year: Optional detected reference year for disambiguation.
            catalog_profile: Profile name ('official_25' or 'legacy_50').
            polarity_info: Optional resolved polarity metadata.

        Returns:
            ConceptMatchResult if a concept matches, otherwise None.
        """
        clean = clean_query.strip().lower()
        active_facets = dict(facets or {})

        if (
            polarity_info is None
            and thesaurus is not None
            and hasattr(thesaurus, "resolve_polarity")
        ):
            polarity_info = thesaurus.resolve_polarity(clean)

        has_pib = bool(
            re.search(r"\b(pib|pbi)\b", clean)
            or "producto interno bruto" in clean
            or "producto bruto interno" in clean
        )

        for compiled_tr in self._compiled_rules:
            m = compiled_tr.compiled_regex.search(clean)
            if not m:
                continue

            rule = compiled_tr.trigger_rule

            # Check excludes_subterms
            if rule.excludes_subterms and any(term in clean for term in rule.excludes_subterms):
                continue

            # Check requires_subterms (at least one must be present if non-empty)
            if rule.requires_subterms and not any(term in clean for term in rule.requires_subterms):
                continue

            # Match confirmed!
            cdef = compiled_tr.concept_def
            concept_key = cdef.concept_key
            matched_phrase = m.group(0)

            consumed: list[str] = [matched_phrase]
            for subterm in rule.requires_subterms:
                if subterm in clean:
                    consumed.append(subterm)

            # Check trigger-level ambiguity
            is_ambiguous = rule.ambiguous_candidate is not None
            ambiguous_candidate = rule.ambiguous_candidate

            # Apply domain-specific guards to trigger-level ambiguity
            if is_ambiguous:
                if ambiguous_candidate == "PRIVATION_GAP":
                    if "privacion y pobreza" not in clean and year is not None:
                        is_ambiguous = False
                        ambiguous_candidate = None
                elif ambiguous_candidate in ("INEQUALITY_INCOME", "DISTRIBUTIVE_GAP"):
                    if "estrato" in active_facets:
                        is_ambiguous = False
                        ambiguous_candidate = None
                elif ambiguous_candidate == "ECONOMIC_ACTIVITY":
                    if "trimestral" in clean or has_pib:
                        is_ambiguous = False
                        ambiguous_candidate = None
                        if "trimestral" in clean:
                            concept_key = "PIB_TRIMESTRAL"
                elif ambiguous_candidate == "MACRO_ECONOMY":
                    if has_pib or any(t in clean for t in ["crecio", "crecimiento"]):
                        is_ambiguous = False
                        ambiguous_candidate = None
                elif ambiguous_candidate == "EMISSIONS_LULUCF_CHOICE":
                    if (
                        polarity_info
                        and str(getattr(polarity_info, "polarity_type", ""))
                        == "INCLUSION_EXCLUSION"
                    ):
                        is_ambiguous = False
                        ambiguous_candidate = None

            # Check definition-level controlled ambiguities if not already flagged
            if not is_ambiguous and cdef.controlled_ambiguities:
                for phrase, cand in cdef.controlled_ambiguities.items():
                    if phrase in clean:
                        # Validate domain guards before flagging ambiguity
                        if cand == "FEMININITY_INDEX":
                            if (
                                year is not None
                                or "edad" in active_facets
                                or active_facets.get("area", "NACIONAL") != "NACIONAL"
                            ):
                                continue
                        elif cand == "URBAN_UNEMPLOYMENT":
                            if year is not None or "edad" in active_facets:
                                continue
                        elif cand in ("INEQUALITY_INCOME", "DISTRIBUTIVE_GAP"):
                            if "estrato" in active_facets:
                                continue
                        elif cand == "ECONOMIC_ACTIVITY":
                            if "trimestral" in clean or has_pib:
                                continue
                        elif cand == "MACRO_ECONOMY":
                            if has_pib or any(t in clean for t in ["crecio", "crecimiento"]):
                                continue
                        elif cand == "GENERAL_PRICES":
                            if not re.search(r"\bprecios en\b", clean) or any(
                                t in clean
                                for t in [
                                    "alimentos",
                                    "transporte",
                                    "energia",
                                    "morfi",
                                    "consumidor",
                                ]
                            ):
                                continue
                        elif cand == "PRIVATION_GAP":
                            if "privacion y pobreza" not in clean and year is not None:
                                continue
                        elif cand == "EMISSIONS_LULUCF_CHOICE":
                            if any(t in clean for t in ["sin", "excluyendo", "con uso"]) or (
                                polarity_info
                                and str(getattr(polarity_info, "polarity_type", ""))
                                == "INCLUSION_EXCLUSION"
                            ):
                                continue

                        is_ambiguous = True
                        ambiguous_candidate = cand
                        consumed.append(phrase)
                        break

            # Initialize suggested facets from definition defaults
            suggested_facets: dict[str, str] = dict(cdef.default_facets)

            # Special catalog_profile handling for EMPLEO default sexo facet
            if cdef.concept_key == "EMPLEO":
                suggested_facets["sexo"] = "TOTAL" if catalog_profile == "legacy_50" else "AMBOS"

            # Check sub-concept refinement rules
            sub_rules = self._compiled_sub_rules.get(cdef.concept_key, [])
            for sub in sub_rules:
                sub_m = sub.compiled_regex.search(clean)
                if sub_m:
                    sub_cand = sub.rule.ambiguous_candidate
                    # Domain guards on sub-concept ambiguity
                    sub_is_ambiguous = sub.rule.is_ambiguous or sub_cand is not None
                    if sub_cand == "URBAN_UNEMPLOYMENT" and (
                        year is not None or "edad" in active_facets
                    ):
                        sub_is_ambiguous = False
                        sub_cand = None
                    elif sub_cand == "FEMININITY_INDEX" and (
                        year is not None
                        or "edad" in active_facets
                        or active_facets.get("area", "NACIONAL") != "NACIONAL"
                    ):
                        sub_is_ambiguous = False
                        sub_cand = None

                    # Special case: CUENTA_CORRIENTE_740 only if "balanza de pagos" not in clean
                    if (
                        sub.rule.sub_concept_key == "CUENTA_CORRIENTE_740"
                        and "balanza de pagos" in clean
                    ):
                        continue

                    consumed.append(sub_m.group(0))
                    concept_key = sub.rule.sub_concept_key

                    if sub_is_ambiguous:
                        is_ambiguous = True
                        ambiguous_candidate = sub_cand
                    else:
                        # Refining to a non-ambiguous sub-concept resolves base trigger ambiguity
                        is_ambiguous = False
                        ambiguous_candidate = None

                    suggested_facets.update(sub.rule.facet_updates)
                    break

            # Polarity-based refinement for emissions (indicator 5682)
            if concept_key == "EMISIONES_GEI_LULUCF":
                if polarity_info and getattr(polarity_info, "canonical_indicator_id", None) == 5682:
                    concept_key = "EMISIONES_GEI_SIN_LULUCF"

            # Contextual facet-based refinements:
            # 1. DISTRIBUCION_INGRESO with etnia or demographic terms -> POBLACION
            if concept_key == "DISTRIBUCION_INGRESO":
                if "etnia" in active_facets or any(
                    term in clean
                    for term in [
                        "poblacion",
                        "habitantes",
                        "personas",
                        "indigena",
                        "afrodescendiente",
                        "demografia",
                        "demografico",
                        "demograficos",
                    ]
                ):
                    concept_key = "POBLACION"
                    if "estrato" not in active_facets and any(
                        term in clean for term in ["quintil", "quintiles"]
                    ):
                        suggested_facets["estrato"] = "QUINTIL"

            # 2. SALARIO_REAL with edad == JUVENTUD -> SALARIO
            if concept_key == "SALARIO_REAL" and active_facets.get("edad") == "JUVENTUD":
                concept_key = "SALARIO"
                is_ambiguous = False
                ambiguous_candidate = None

            # Collect associated concept phrases that appear in query
            for p in self._concept_associated_phrases.get(cdef.concept_key, ()):
                if p in clean and p not in consumed:
                    consumed.append(p)

            # If refined to another concept with associated phrases, add them too
            if concept_key != cdef.concept_key:
                for p in self._concept_associated_phrases.get(concept_key, ()):
                    if p in clean and p not in consumed:
                        consumed.append(p)

            # Invariant: if has_pib in query, consume standard pib phrases so they are never unconsumed tokens
            if has_pib:
                for p in ("producto interno bruto", "producto bruto interno"):
                    if p in clean and p not in consumed:
                        consumed.append(p)
                for p in ("pib", "pbi"):
                    if re.search(rf"\b{p}\b", clean) and p not in consumed:
                        consumed.append(p)

            # Deduplicate consumed phrases preserving order
            unique_consumed = list(dict.fromkeys(consumed))

            return ConceptMatchResult(
                concept_key=concept_key,
                matched_phrase=matched_phrase,
                consumed_phrases=unique_consumed,
                is_ambiguous_measure=is_ambiguous,
                ambiguous_candidate=ambiguous_candidate,
                suggested_facets=suggested_facets,
            )

        return None

    def get_definition(self, concept_key: str) -> ConceptDefinition | None:
        """Lookup concept definition by canonical key."""
        return self._concept_map.get(concept_key)

    def list_concepts(self) -> list[str]:
        """List all canonical concept keys registered in the ontology."""
        return list(self._concept_map.keys())

    def __contains__(self, concept_key: str) -> bool:
        return concept_key in self._concept_map

    def __getitem__(self, concept_key: str) -> ConceptDefinition:
        return self._concept_map[concept_key]

    def __len__(self) -> int:
        return len(self._concept_map)


# Global singleton instance with precompiled default ontology
DEFAULT_CONCEPT_ONTOLOGY = ConceptOntology()

__all__ = [
    "DEFAULT_CONCEPT_DEFINITIONS",
    "DEFAULT_CONCEPT_ONTOLOGY",
    "ConceptDefinition",
    "ConceptMatchResult",
    "ConceptOntology",
    "ConceptTriggerRule",
    "SubConceptRule",
]
