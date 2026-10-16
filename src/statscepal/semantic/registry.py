"""Metadata registry and typed relationship graph for the vertical slice and 200-question suite."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.models import (
    MeasureType,
    RelationshipType,
    TemporalAvailabilityStatus,
)

if TYPE_CHECKING:
    from statscepal.catalog.store import CatalogStore


class IndicatorMetadata:
    """Rich metadata for an indicator in the semantic knowledge graph."""

    def __init__(
        self,
        indicator_id: int,
        name: str,
        concept: str,
        measure_type: str | MeasureType,
        unit: str,
        supported_facets: set[str],
        relationships: dict[int, RelationshipType] | None = None,
    ):
        self.indicator_id = indicator_id
        self.name = name
        self.concept = concept
        self.measure_type = measure_type.value if isinstance(measure_type, MeasureType) else measure_type
        self.unit = unit
        self.supported_facets = supported_facets
        self.relationships = relationships or {}


# Default official dimensions and members for the core 25 indicators
DEFAULT_OFFICIAL_DIMENSIONS: dict[int, list[Dimension]] = {
    3342: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=1361,
            name="Pobreza extrema y pobreza",
            members=[
                Member(id=501, name="Pobreza extrema"),
                Member(id=502, name="Pobreza"),
            ],
        ),
        Dimension(
            id=43039,
            name="Tipo de etnia",
            members=[
                Member(id=43040, name="Afrodescendiente"),
                Member(id=43041, name="Indígena"),
                Member(id=43042, name="No indígena ni afrodescendiente"),
                Member(id=43043, name="Total"),
            ],
        ),
    ],
    3341: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=43054,
            name="Grupo de edad",
            members=[
                Member(id=43059, name="0 a 14 años"),
                Member(id=43058, name="15 a 24 años"),
                Member(id=43060, name="65 años y más"),
            ],
        ),
        Dimension(
            id=500,
            name="Tipo de pobreza",
            members=[
                Member(id=501, name="Pobreza extrema / indigencia"),
                Member(id=502, name="Total pobreza"),
            ],
        ),
    ],
    3328: [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=500,
            name="Tipo de pobreza",
            members=[
                Member(id=501, name="Pobreza extrema / indigencia"),
                Member(id=502, name="Total pobreza"),
            ],
        ),
    ],
    3329: [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=500,
            name="Tipo de pobreza",
            members=[
                Member(id=501, name="Pobreza extrema / indigencia"),
                Member(id=502, name="Total pobreza"),
            ],
        ),
    ],
    3330: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=266, name="Mujeres")],
        ),
    ],
    3340: [
        Dimension(
            id=600,
            name="Estrato de ingreso",
            members=[
                Member(id=601, name="Primer quintil"),
                Member(id=602, name="Segundo quintil"),
                Member(id=603, name="Tercer quintil"),
                Member(id=604, name="Cuarto quintil"),
                Member(id=605, name="Quinto quintil"),
            ],
        ),
    ],
    3339: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
    ],
    3345: [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
    ],
    2928: [
        Dimension(
            id=700,
            name="Rubro de gasto",
            members=[Member(id=701, name="Índice general")],
        ),
    ],
    2929: [
        Dimension(
            id=79565,
            name="Canasta de bienes",
            members=[Member(id=79578, name="Alimentos y bebidas no alcohólicas")],
        ),
    ],
    2930: [
        Dimension(
            id=79565,
            name="Canasta de bienes",
            members=[Member(id=79580, name="Transporte y energía")],
        ),
    ],
}


# Static registry for the 25 official indicators and vertical slice domain
VERTICAL_SLICE_INDICATORS: dict[int, IndicatorMetadata] = {
    # 1. Pobreza por área
    3328: IndicatorMetadata(
        indicator_id=3328,
        name="Población en situación de pobreza extrema y pobreza, por área",
        concept="POBREZA",
        measure_type=MeasureType.INCIDENCIA_PORCENTUAL,
        unit="%",
        supported_facets={"area", "severidad"},
        relationships={
            3341: RelationshipType.BREAKDOWN_OF,
            3342: RelationshipType.BREAKDOWN_OF,
            3329: RelationshipType.ALTERNATIVE_MEASURE,
            3330: RelationshipType.ALTERNATIVE_MEASURE,
            3337: RelationshipType.ALTERNATIVE_MEASURE,
            4322: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 2. Pobreza por sexo y edad
    3341: IndicatorMetadata(
        indicator_id=3341,
        name="Tasa de incidencia de la pobreza según sexo y edad",
        concept="POBREZA",
        measure_type=MeasureType.INCIDENCIA_PORCENTUAL,
        unit="%",
        supported_facets={"sexo", "edad", "area", "severidad"},
        relationships={
            3328: RelationshipType.BREAKDOWN_OF,
            3330: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 2b. Pobreza por sexo, autoidentificación étnico-racial y área
    3342: IndicatorMetadata(
        indicator_id=3342,
        name="Población en situación de pobreza extrema y pobreza, por sexo, autoidentificación étnico-racial y área",
        concept="POBREZA",
        measure_type=MeasureType.INCIDENCIA_PORCENTUAL,
        unit="%",
        supported_facets={"area", "severidad", "sexo", "etnia"},
        relationships={
            3328: RelationshipType.BREAKDOWN_OF,
            3341: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 3. Brecha de pobreza
    3329: IndicatorMetadata(
        indicator_id=3329,
        name="Brecha de pobreza y pobreza extrema",
        concept="POBREZA_BRECHA",
        measure_type=MeasureType.BRECHA_PORCENTUAL,
        unit="%",
        supported_facets={"area", "severidad"},
        relationships={
            3328: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 4. Índice de feminidad
    3330: IndicatorMetadata(
        indicator_id=3330,
        name="Índice de feminidad de la pobreza",
        concept="POBREZA_FEMINIDAD",
        measure_type=MeasureType.INDICE_FEMINIDAD,
        unit="razón",
        supported_facets={"sexo"},
        relationships={
            3328: RelationshipType.ALTERNATIVE_MEASURE,
            3341: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 5. Distribución del ingreso
    3340: IndicatorMetadata(
        indicator_id=3340,
        name="Distribución del ingreso de los hogares por quintiles y deciles",
        concept="DISTRIBUCION_INGRESO",
        measure_type=MeasureType.DISTRIBUCION_INGRESO,
        unit="%",
        supported_facets={"estrato", "quintil", "decil"},
        relationships={},
    ),
    # 6. Tasa de desocupación por sexo
    127: IndicatorMetadata(
        indicator_id=127,
        name="Tasa de desocupación por sexo",
        concept="EMPLEO",
        measure_type=MeasureType.TASA_DESOCUPACION,
        unit="%",
        supported_facets={"sexo", "formalidad"},
        relationships={
            5097: RelationshipType.BREAKDOWN_OF,
            3344: RelationshipType.BREAKDOWN_OF,
            3331: RelationshipType.BREAKDOWN_OF,
            119: RelationshipType.ALTERNATIVE_MEASURE,
            340: RelationshipType.RELATED_CONCEPT,
        },
    ),
    # 7. Desempleo juvenil
    3331: IndicatorMetadata(
        indicator_id=3331,
        name="Tasa de desempleo juvenil de 15 a 24 años",
        concept="DESEMPLEO_JUVENIL",
        measure_type=MeasureType.TASA_DESOCUPACION,
        unit="%",
        supported_facets={"sexo", "edad"},
        relationships={
            127: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 8. Salario medio real
    128: IndicatorMetadata(
        indicator_id=128,
        name="Índice del salario medio real",
        concept="SALARIO_MEDIO",
        measure_type=MeasureType.INDICE_REAL,
        unit="índice 2018=100",
        supported_facets=set(),
        relationships={
            3339: RelationshipType.BREAKDOWN_OF,
            3337: RelationshipType.ALTERNATIVE_MEASURE,
            3345: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 9. Salario mínimo real
    3337: IndicatorMetadata(
        indicator_id=3337,
        name="Salario mínimo real",
        concept="SALARIO_MINIMO",
        measure_type=MeasureType.INDICE_REAL,
        unit="índice 2018=100",
        supported_facets={"area", "edad"},
        relationships={
            128: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 10. Ingreso laboral medio
    3339: IndicatorMetadata(
        indicator_id=3339,
        name="Ingreso laboral medio de la población ocupada por sexo y área",
        concept="INGRESO_LABORAL",
        measure_type=MeasureType.MONTO_MONEDA_LOCAL,
        unit="moneda local",
        supported_facets={"sexo", "area"},
        relationships={
            128: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 11. Ingreso medio per cápita hogares
    3345: IndicatorMetadata(
        indicator_id=3345,
        name="Ingreso medio per cápita de los hogares",
        concept="INGRESO_HOGARES",
        measure_type=MeasureType.MONTO_MONEDA_LOCAL,
        unit="moneda local",
        supported_facets={"area"},
        relationships={
            128: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 12. PIB total a precios constantes
    729: IndicatorMetadata(
        indicator_id=729,
        name="Producto interno bruto total anual a precios constantes",
        concept="PIB",
        measure_type=MeasureType.MONTO_MONEDA_LOCAL,
        unit="millones moneda nacional",
        supported_facets=set(),
        relationships={
            730: RelationshipType.BREAKDOWN_OF,
            731: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 13. PIB per cápita constante
    730: IndicatorMetadata(
        indicator_id=730,
        name="Producto interno bruto per cápita a precios constantes",
        concept="PIB_PER_CAPITA",
        measure_type=MeasureType.USD_PER_CAPITA,
        unit="USD",
        supported_facets=set(),
        relationships={
            729: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 14. PIB trimestral a precios constantes
    731: IndicatorMetadata(
        indicator_id=731,
        name="Producto interno bruto trimestral a precios constantes",
        concept="PIB_TRIMESTRAL",
        measure_type=MeasureType.TASA_VARIACION_INTERANUAL,
        unit="%",
        supported_facets=set(),
        relationships={
            729: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 15. IPC general
    2928: IndicatorMetadata(
        indicator_id=2928,
        name="Índice de precios al consumidor (IPC) general",
        concept="IPC_GENERAL",
        measure_type=MeasureType.INDICE_PRECIOS,
        unit="índice 2018=100",
        supported_facets={"rubro"},
        relationships={
            2929: RelationshipType.BREAKDOWN_OF,
            2930: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 16. IPC alimentos y bebidas
    2929: IndicatorMetadata(
        indicator_id=2929,
        name="Índice de precios al consumidor de alimentos y bebidas",
        concept="IPC_ALIMENTOS",
        measure_type=MeasureType.INDICE_PRECIOS,
        unit="índice 2018=100",
        supported_facets={"canasta"},
        relationships={
            2928: RelationshipType.BREAKDOWN_OF,
            365: RelationshipType.ALTERNATIVE_MEASURE,
            1684: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 17. IPC transporte y energía
    2930: IndicatorMetadata(
        indicator_id=2930,
        name="Índice de precios al consumidor de transporte y energía",
        concept="IPC_TRANSPORTE_ENERGIA",
        measure_type=MeasureType.INDICE_PRECIOS,
        unit="índice 2018=100",
        supported_facets=set(),
        relationships={
            2928: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 18. Deuda pública % PIB
    1240: IndicatorMetadata(
        indicator_id=1240,
        name="Saldo de la deuda pública del gobierno central en porcentaje del PIB",
        concept="DEUDA_PUBLICA",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
        relationships={
            1241: RelationshipType.ALTERNATIVE_MEASURE,
            1242: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 19. Balance primario % PIB
    1241: IndicatorMetadata(
        indicator_id=1241,
        name="Balance primario del gobierno central en porcentaje del PIB",
        concept="BALANCE_PRIMARIO",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
        relationships={
            1240: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 20. Ingresos tributarios % PIB
    1242: IndicatorMetadata(
        indicator_id=1242,
        name="Ingresos tributarios del gobierno central en porcentaje del PIB",
        concept="INGRESOS_TRIBUTARIOS",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
        relationships={
            1240: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 21. Cuenta corriente % PIB
    1243: IndicatorMetadata(
        indicator_id=1243,
        name="Saldo en cuenta corriente de la balanza de pagos en porcentaje del PIB",
        concept="CUENTA_CORRIENTE",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
        relationships={},
    ),
    # 22. Términos de intercambio
    1244: IndicatorMetadata(
        indicator_id=1244,
        name="Términos de intercambio de bienes FOB/CIF",
        concept="TERMINOS_INTERCAMBIO",
        measure_type=MeasureType.INDICE_PRECIOS,
        unit="índice 2018=100",
        supported_facets=set(),
        relationships={},
    ),
    # 23. GEI con LULUCF
    5681: IndicatorMetadata(
        indicator_id=5681,
        name="Emisiones totales de GEI incluyendo sector UTCUTS / con LULUCF",
        concept="EMISIONES_GEI_LULUCF",
        measure_type=MeasureType.VOLUMEN_EMISIONES,
        unit="Mt CO2 eq",
        supported_facets=set(),
        relationships={
            5682: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 24. GEI sin LULUCF
    5682: IndicatorMetadata(
        indicator_id=5682,
        name="Emisiones totales de GEI excluyendo sector UTCUTS / sin LULUCF",
        concept="EMISIONES_GEI_SIN_LULUCF",
        measure_type=MeasureType.VOLUMEN_EMISIONES,
        unit="Mt CO2 eq",
        supported_facets=set(),
        relationships={
            5681: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 25. Energías renovables %
    5683: IndicatorMetadata(
        indicator_id=5683,
        name="Participación de energías renovables en la generación eléctrica",
        concept="ENERGIA_RENOVABLE",
        measure_type=MeasureType.PORCENTAJE_GENERACION,
        unit="%",
        supported_facets=set(),
        relationships={},
    ),
    # Existing slice indicators preserved for backward compatibility
    5097: IndicatorMetadata(
        indicator_id=5097,
        name="Tasa de desempleo, por sexo y edad - 19ª CIET (%)",
        concept="EMPLEO",
        measure_type=MeasureType.TASA_DESOCUPACION,
        unit="%",
        supported_facets={"sexo", "edad"},
        relationships={
            127: RelationshipType.BREAKDOWN_OF,
        },
    ),
    119: IndicatorMetadata(
        indicator_id=119,
        name="Tasa de desocupación abierta en el área urbana, por sexo y años de educación",
        concept="EMPLEO",
        measure_type=MeasureType.TASA_DESOCUPACION_URBANA,
        unit="%",
        supported_facets={"sexo", "area", "educacion"},
        relationships={
            127: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    2203: IndicatorMetadata(
        indicator_id=2203,
        name="Producto interno bruto (PIB) anual a precios constantes en dólares",
        concept="PIB",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="Millones de USD constantes",
        supported_facets=set(),
        relationships={
            2204: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    2204: IndicatorMetadata(
        indicator_id=2204,
        name="Producto interno bruto (PIB) anual a precios corrientes en moneda nacional",
        concept="PIB_CORRIENTE",
        measure_type=MeasureType.VALOR_CORRIENTE,
        unit="Moneda nacional corriente",
        supported_facets=set(),
        relationships={
            2203: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    2206: IndicatorMetadata(
        indicator_id=2206,
        name="Producto interno bruto (PIB) per cápita a precios constantes",
        concept="PIB_PER_CAPITA",
        measure_type=MeasureType.VOLUMEN_REAL_PER_CAPITA,
        unit="USD constantes por habitante",
        supported_facets=set(),
    ),
    2447: IndicatorMetadata(
        indicator_id=2447,
        name="Producto interno bruto (PIB) trimestral",
        concept="PIB_TRIMESTRAL",
        measure_type=MeasureType.VOLUMEN_REAL_TRIMESTRAL,
        unit="Millones de USD constantes",
        supported_facets=set(),
    ),
    340: IndicatorMetadata(
        indicator_id=340,
        name="Salario mínimo real",
        concept="SALARIO",
        measure_type=MeasureType.INDICE_REAL,
        unit="Índice base 2018=100",
        supported_facets={"area", "edad"},
    ),
    3289: IndicatorMetadata(
        indicator_id=3289,
        name="Índice de Gini de concentración del ingreso",
        concept="GINI",
        measure_type=MeasureType.COEFICIENTE_CONCENTRACION,
        unit="Coeficiente (0 a 1)",
        supported_facets=set(),
    ),
    365: IndicatorMetadata(
        indicator_id=365,
        name="Índice de precios al consumidor general",
        concept="IPC_GENERAL",
        measure_type=MeasureType.INDICE_PRECIOS,
        unit="Índice base",
        supported_facets={"rubro"},
        relationships={
            1684: RelationshipType.BREAKDOWN_OF,
            2929: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    1684: IndicatorMetadata(
        indicator_id=1684,
        name="Índice de precios al consumidor, alimentos y bebidas",
        concept="IPC_ALIMENTOS",
        measure_type=MeasureType.INDICE_PRECIOS,
        unit="Índice base",
        supported_facets={"canasta"},
        relationships={
            365: RelationshipType.BREAKDOWN_OF,
            2929: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    2949: IndicatorMetadata(
        indicator_id=2949,
        name="Balanza comercial de bienes",
        concept="BALANZA_COMERCIAL",
        measure_type=MeasureType.SALDO_COMERCIAL,
        unit="Millones de USD",
        supported_facets=set(),
    ),
    740: IndicatorMetadata(
        indicator_id=740,
        name="Saldo en cuenta corriente como porcentaje del PIB",
        concept="CUENTA_CORRIENTE",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
    ),
    4231: IndicatorMetadata(
        indicator_id=4231,
        name="Inversión extranjera directa entradas netas",
        concept="INVERSION_EXTRANJERA_DIRECTA",
        measure_type=MeasureType.FLUJO_CAPITAL,
        unit="Millones de USD",
        supported_facets=set(),
    ),
    2954: IndicatorMetadata(
        indicator_id=2954,
        name="Términos de intercambio de bienes",
        concept="TERMINOS_INTERCAMBIO",
        measure_type=MeasureType.INDICE_PRECIOS_RELATIVOS,
        unit="Índice base",
        supported_facets=set(),
    ),
    4405: IndicatorMetadata(
        indicator_id=4405,
        name="Gasto social público total como porcentaje del PIB",
        concept="GASTO_SOCIAL",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
        relationships={
            4406: RelationshipType.BREAKDOWN_OF,
        },
    ),
    4406: IndicatorMetadata(
        indicator_id=4406,
        name="Gasto público en educación",
        concept="GASTO_EDUCACION",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
        relationships={
            4405: RelationshipType.BREAKDOWN_OF,
        },
    ),
    1318: IndicatorMetadata(
        indicator_id=1318,
        name="Extracción de agua dulce por habitante",
        concept="AGUA_DULCE",
        measure_type=MeasureType.VOLUMEN_PER_CAPITA,
        unit="m3 por habitante",
        supported_facets=set(),
    ),
    3344: IndicatorMetadata(
        indicator_id=3344,
        name="Tasa de desocupación según sexo y edad",
        concept="DESEMPLEO_JUVENIL",
        measure_type=MeasureType.TASA_DESOCUPACION,
        unit="%",
        supported_facets={"sexo", "edad"},
        relationships={
            127: RelationshipType.BREAKDOWN_OF,
        },
    ),
    3333: IndicatorMetadata(
        indicator_id=3333,
        name="Relación de ingresos laborales por sexo",
        concept="BRECHA_SALARIAL",
        measure_type=MeasureType.RATIO_RELATIVO,
        unit="Ratio mujeres/hombres",
        supported_facets={"sexo"},
        relationships={
            340: RelationshipType.RELATED_CONCEPT,
        },
    ),
}

# Concept to Canonical Default mappings
OFFICIAL_25_CANONICAL_DEFAULTS: dict[str, int] = {
    "POBREZA": 3328,
    "POBREZA_BRECHA": 3329,
    "POBREZA_FEMINIDAD": 3330,
    "DISTRIBUCION_INGRESO": 3340,
    "EMPLEO": 127,
    "DESEMPLEO_JUVENIL": 3331,
    "DESEMPLEO_JUVENIL_15_24": 3331,
    "SALARIO": 128,
    "SALARIO_MEDIO": 128,
    "SALARIO_REAL": 128,
    "SALARIO_MINIMO": 3337,
    "INGRESO_LABORAL": 3339,
    "INGRESO_HOGARES": 3345,
    "INGRESO_HOGAR_PER_CAPITA": 3345,
    "PIB": 729,
    "PIB_CORRIENTE": 729,
    "PIB_PER_CAPITA": 730,
    "PIB_TRIMESTRAL": 731,
    "GINI": 3289,
    "IPC_GENERAL": 2928,
    "IPC_ALIMENTOS": 2929,
    "INFLACION_ALIMENTOS": 2929,
    "IPC_TRANSPORTE_ENERGIA": 2930,
    "BALANZA_COMERCIAL": 2949,
    "CUENTA_CORRIENTE": 1243,
    "CUENTA_CORRIENTE_740": 1243,
    "INVERSION_EXTRANJERA_DIRECTA": 4231,
    "TERMINOS_INTERCAMBIO": 1244,
    "DEUDA_PUBLICA": 1240,
    "BALANCE_PRIMARIO": 1241,
    "INGRESOS_TRIBUTARIOS": 1242,
    "GASTO_SOCIAL": 4405,
    "GASTO_EDUCACION": 4406,
    "EMISIONES_GEI_LULUCF": 5681,
    "EMISIONES_GEI_SIN_LULUCF": 5682,
    "ENERGIA_RENOVABLE": 5683,
    "AGUA_DULCE": 1318,
    "BRECHA_SALARIAL": 3333,
}

LEGACY_50_CANONICAL_DEFAULTS: dict[str, int] = {
    "POBREZA": 3328,
    "POBREZA_BRECHA": 3329,
    "POBREZA_FEMINIDAD": 3330,
    "DISTRIBUCION_INGRESO": 3340,
    "EMPLEO": 127,
    "DESEMPLEO_JUVENIL": 3344,
    "DESEMPLEO_JUVENIL_15_24": 5097,
    "SALARIO": 340,
    "SALARIO_MEDIO": 128,
    "SALARIO_REAL": 128,
    "SALARIO_MINIMO": 340,
    "INGRESO_LABORAL": 3339,
    "INGRESO_HOGARES": 3345,
    "INGRESO_HOGAR_PER_CAPITA": 3345,
    "PIB": 2203,
    "PIB_CORRIENTE": 2204,
    "PIB_PER_CAPITA": 2206,
    "PIB_TRIMESTRAL": 2447,
    "GINI": 3289,
    "IPC_GENERAL": 365,
    "IPC_ALIMENTOS": 1684,
    "INFLACION_ALIMENTOS": 2929,
    "IPC_TRANSPORTE_ENERGIA": 2930,
    "BALANZA_COMERCIAL": 2949,
    "CUENTA_CORRIENTE": 1243,
    "CUENTA_CORRIENTE_740": 740,
    "INVERSION_EXTRANJERA_DIRECTA": 4231,
    "TERMINOS_INTERCAMBIO": 2954,
    "DEUDA_PUBLICA": 1240,
    "BALANCE_PRIMARIO": 1241,
    "INGRESOS_TRIBUTARIOS": 1242,
    "GASTO_SOCIAL": 4405,
    "GASTO_EDUCACION": 4406,
    "EMISIONES_GEI_LULUCF": 5681,
    "EMISIONES_GEI_SIN_LULUCF": 5682,
    "ENERGIA_RENOVABLE": 5683,
    "AGUA_DULCE": 1318,
    "BRECHA_SALARIAL": 3333,
}

CONCEPT_CANONICAL_DEFAULTS = OFFICIAL_25_CANONICAL_DEFAULTS

# Empirical observation availability for country x year x indicator
# Maps (indicator_id, country_code, year) -> (status, prev_anchor, next_anchor)
TEMPORAL_AVAILABILITY_MATRIX: dict[tuple[int, str, int], tuple[TemporalAvailabilityStatus, int | None, int | None]] = {
    # Chile (CASEN is biennial/triennial)
    (3328, "CHL", 2020): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    (3328, "CHL", 2021): (TemporalAvailabilityStatus.PERIOD_UNOBSERVED, 2020, 2022),
    (3328, "CHL", 2022): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    (3341, "CHL", 2022): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    # Mexico (ENIGH is biennial in even years)
    (3328, "MEX", 2020): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    (3328, "MEX", 2021): (TemporalAvailabilityStatus.PERIOD_UNOBSERVED, 2020, 2022),
    (3328, "MEX", 2022): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    # Brazil (PNADC is continuous annual)
    (3328, "BRA", 2021): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    (3341, "BRA", 2021): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    # Colombia (GEIH continuous)
    (127, "COL", 2021): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    (5097, "COL", 2021): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    (340, "COL", 2021): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    (2929, "COL", 2022): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    # Uruguay (ECH continuous)
    (127, "URY", 2022): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    # Argentina (EPH continuous)
    (127, "ARG", 2021): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    (127, "ARG", 2022): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    (5097, "ARG", 2021): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    # Costa Rica
    (3289, "CRI", 2022): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
    # Peru
    (3328, "PER", 2021): (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None),
}


def _normalize_temporal_status(status_raw: Any) -> TemporalAvailabilityStatus:
    if isinstance(status_raw, TemporalAvailabilityStatus):
        return status_raw
    if isinstance(status_raw, str):
        cleaned = status_raw.strip().upper()
        try:
            return TemporalAvailabilityStatus(cleaned)
        except (ValueError, KeyError):
            pass
        try:
            return TemporalAvailabilityStatus[cleaned]
        except (ValueError, KeyError):
            pass
    return TemporalAvailabilityStatus.OBSERVATION_MISSING


class SemanticRegistry:
    """Registry managing indicator metadata, relationships, and temporal calendars."""

    def __init__(
        self,
        store: CatalogStore | None = None,
        dimensions: dict[int, list[Dimension]] | None = None,
        relationships: dict[Any, Any] | None = None,
        temporal_availability: dict[tuple[int, str, int], tuple[Any, int | None, int | None]] | None = None,
        catalog_profile: str = "official_25",
    ) -> None:
        self.store = store
        self.catalog_profile = catalog_profile
        self._dimensions = dimensions or {}
        self._relationships = relationships or {}
        self._temporal_availability = temporal_availability or {}

    def get_indicator(self, indicator_id: int) -> IndicatorMetadata | None:
        """Get indicator metadata from in-memory registry or attached SQLite store."""
        if indicator_id in VERTICAL_SLICE_INDICATORS:
            return VERTICAL_SLICE_INDICATORS[indicator_id]

        if self.store is not None:
            raw = self.store.get_indicator_metadata(indicator_id)
            if raw:
                store_rels = self.store.get_relationships(indicator_id)
                typed_rels = {
                    t: (RelationshipType(r) if r in RelationshipType._value2member_map_ else RelationshipType[str(r).upper()])
                    for t, r in store_rels.items()
                }
                return IndicatorMetadata(
                    indicator_id=raw["indicator_id"],
                    name=raw["name"],
                    concept=raw["concept"],
                    measure_type=raw["measure_type"],
                    unit=raw["unit"],
                    supported_facets=raw["supported_facets"],
                    relationships=typed_rels,
                )

        return None

    def get_canonical_default(self, concept: str) -> int | None:
        """Get canonical indicator ID for a given normalized statistical concept."""
        if self.catalog_profile == "legacy_50":
            return LEGACY_50_CANONICAL_DEFAULTS.get(concept)
        return OFFICIAL_25_CANONICAL_DEFAULTS.get(concept)

    def get_dimensions(self, indicator_id: int) -> list[Dimension]:
        """Get dimensions for an indicator, checking store or custom dict."""
        if self.store is not None:
            dims = self.store.get_indicator_dimensions(indicator_id)
            if dims:
                return dims
        return self._dimensions.get(indicator_id, [])

    def get_relationships(self, indicator_id: int) -> dict[int, RelationshipType]:
        """Get all typed relationships originating from indicator_id across all sources."""
        rels: dict[int, RelationshipType] = {}

        # 1. Base metadata registry
        ind = VERTICAL_SLICE_INDICATORS.get(indicator_id)
        if ind and ind.relationships:
            for target, r in ind.relationships.items():
                r_enum = r if isinstance(r, RelationshipType) else RelationshipType(r)
                rels[target] = r_enum

        # 2. In-memory relationships overrides
        if indicator_id in self._relationships and isinstance(self._relationships[indicator_id], dict):
            for target, r in self._relationships[indicator_id].items():
                r_enum = r if isinstance(r, RelationshipType) else RelationshipType(r)
                rels[target] = r_enum

        for key, r in self._relationships.items():
            if isinstance(key, tuple) and len(key) == 2 and key[0] == indicator_id:
                target = key[1]
                r_enum = r if isinstance(r, RelationshipType) else RelationshipType(r)
                rels[target] = r_enum

        # 3. SQLite CatalogStore if attached
        if self.store is not None:
            store_rels = self.store.get_relationships(indicator_id)
            for target, r in store_rels.items():
                try:
                    r_enum = RelationshipType(r) if not isinstance(r, RelationshipType) else r
                except ValueError:
                    try:
                        r_enum = RelationshipType[str(r).upper()]
                    except KeyError:
                        continue
                rels[target] = r_enum

        return rels

    def get_target_indicators(self, indicator_id: int, rel_type: str | RelationshipType) -> list[int]:
        """Get target indicators related to indicator_id by a specific relationship type."""
        target_val = rel_type.value if isinstance(rel_type, RelationshipType) else str(rel_type).lower()
        rels = self.get_relationships(indicator_id)
        return [
            target
            for target, r in rels.items()
            if (r.value if isinstance(r, RelationshipType) else str(r)).lower() == target_val
        ]

    def check_relationship(self, indicator_a: int, indicator_b: int) -> RelationshipType | None:
        """Check the typed relationship between indicator_a and indicator_b."""
        rels = self.get_relationships(indicator_a)
        return rels.get(indicator_b)

    def check_temporal_availability(
        self,
        indicator_id: int,
        country_code: str,
        year: int,
    ) -> tuple[TemporalAvailabilityStatus, int | None, int | None]:
        """Check observation status and anchor years for an indicator, country, and year."""
        if self.store is not None:
            rec = self.store.get_temporal_record(indicator_id, country_code, year)
            if rec is not None:
                status_raw, prev_a, next_a = rec
                status_enum = _normalize_temporal_status(status_raw)
                return (status_enum, prev_a, next_a)

        key = (indicator_id, country_code, year)
        if key in self._temporal_availability:
            rec = self._temporal_availability[key]
            status_enum = _normalize_temporal_status(rec[0])
            return (status_enum, rec[1], rec[2])

        if key in TEMPORAL_AVAILABILITY_MATRIX:
            return TEMPORAL_AVAILABILITY_MATRIX[key]

        # Default: if between 2000 and 2023, assume existing
        if 2000 <= year <= 2023:
            return (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None)
        return (TemporalAvailabilityStatus.OBSERVATION_MISSING, None, None)
