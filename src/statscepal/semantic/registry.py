"""Metadata registry and typed relationship graph for the vertical slice and 200-question suite."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY, FacetOntology
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
                Member(id=43040, name="Total"),
                Member(id=43044, name="Afrodescendiente"),
                Member(id=77477, name="Indígena"),
                Member(id=43043, name="No indígena ni afrodescendiente"),
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
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=600,
            name="Estrato de ingreso",
            members=[
                Member(id=601, name="Primer quintil"),
                Member(id=602, name="Segundo quintil"),
                Member(id=603, name="Tercer quintil"),
                Member(id=604, name="Cuarto quintil"),
                Member(id=605, name="Quinto quintil"),
                Member(id=610, name="Primer decil"),
                Member(id=611, name="Décimo decil"),
                Member(id=612, name="Deciles"),
                Member(id=613, name="Relación quintil 5 / quintil 1"),
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
    4788: [
        Dimension(
            id=88622,
            name="Sexo",
            members=[Member(id=88623, name="Ambos sexos"), Member(id=88626, name="Hombres"), Member(id=88627, name="Mujeres")],
        ),
    ],
    4968: [
        Dimension(
            id=48525,
            name="Area Geografica",
            members=[Member(id=48529, name="Total"), Member(id=48526, name="Urbano"), Member(id=48528, name="Rural")],
        ),
        Dimension(
            id=78149,
            name="Condición Indígena",
            members=[Member(id=78150, name="Indígena"), Member(id=78152, name="No Indígena"), Member(id=78154, name="Total")],
        ),
    ],
    4969: [
        Dimension(
            id=48525,
            name="Area Geografica",
            members=[Member(id=48529, name="Total"), Member(id=48526, name="Urbano"), Member(id=48528, name="Rural")],
        ),
        Dimension(
            id=140625,
            name="Condición Afrodescendiente",
            members=[Member(id=140626, name="Afrodescendiente"), Member(id=140627, name="No Afrodescendiente"), Member(id=140629, name="Total")],
        ),
    ],
    4992: [
        Dimension(
            id=48525,
            name="Area Geografica",
            members=[Member(id=48529, name="Total"), Member(id=48526, name="Urbano"), Member(id=48528, name="Rural")],
        ),
    ],
    4639: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=378,
            name="Quintil",
            members=[
                Member(id=380, name="Quintil 1"),
                Member(id=382, name="Quintil 2"),
                Member(id=383, name="Quintil 3"),
                Member(id=384, name="Quintil 4"),
                Member(id=381, name="Quintil 5"),
                Member(id=379, name="Total quintiles"),
            ],
        ),
        Dimension(
            id=43039,
            name="Tipo de etnia",
            members=[
                Member(id=77477, name="Indígena"),
                Member(id=43044, name="Afrodescendiente"),
                Member(id=43043, name="No indígena ni afrodescendiente"),
                Member(id=43040, name="Total"),
            ],
        ),
    ],
    127: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
    ],
    3331: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=43054,
            name="Grupo de edad",
            members=[
                Member(id=43058, name="15 a 24 años"),
            ],
        ),
    ],
    3337: [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
    ],
    5097: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
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
    ],
    119: [
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
    340: [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
    ],
    365: [
        Dimension(
            id=29281,
            name="Rubro",
            members=[Member(id=29282, name="General"), Member(id=29283, name="Salud")],
        ),
    ],
    1684: [
        Dimension(
            id=79565,
            name="Canasta de bienes",
            members=[Member(id=79578, name="Alimentos y bebidas no alcohólicas")],
        ),
    ],
    3344: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
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
    ],
    3333: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
    ],
    4145: [],
    845: [],
}


# Synthetic member IDs defined in DEFAULT_OFFICIAL_DIMENSIONS for offline Stage 4 matching
# that must not be sent as raw integer filters to the live CEPALSTAT API records endpoint.
SYNTHETIC_DIMENSION_MEMBER_IDS: frozenset[int] = frozenset({
    300, 301, 302,
    327, 330, 331,
    412, 413, 414, 415,
    501, 502,
    601, 602, 603, 604, 605, 610, 611, 612, 613,
    701,
    29282, 29283,
    79578, 79580,
})

# Mapping from synthetic/placeholder official_25 indicator IDs to real CEPALSTAT master_indicators IDs
EMPIRICAL_INDICATOR_ID_MAP: dict[int, int] = {
    2928: 2484,  # Tasa de crecimiento anual del índice de precios al consumidor: diciembre a diciembre
    2930: 4145,  # Tasa de crecimiento anual del índice de precios al consumidor subyacente: diciembre a diciembre
    4145: 4145,  # Tasa de crecimiento anual del índice de precios al consumidor subyacente: diciembre a diciembre
    845: 845,    # Ingresos tributarios en moneda nacional a precios corrientes
    729: 2204,   # Producto interno bruto (PIB) total anual a precios constantes en dólares
    730: 2206,   # Producto interno bruto (PIB) total anual por habitante a precios constantes en dólares
    731: 286,    # Producto interno bruto trimestral por tipo del gasto a precios constantes
    2447: 286,   # Producto interno bruto trimestral
    3331: 5097,  # Tasa de desempleo, por sexo y edad - 19ª CIET (%)
    3344: 5097,  # Tasa de desocupación según sexo y edad
    128: 341,    # Salario medio real anual
    3337: 340,   # Salario mínimo real
    3339: 2287,  # Ingreso medio de la población ocupada, por sexo e inserción laboral
    3345: 5698,  # Ingreso medio de la población ocupada, por sexo, autoidentificación étnico-racial y área
    3340: 3390,  # Distribución del ingreso de los hogares, por deciles y área
    1241: 1246,  # Operaciones del gobierno (clasificación económica), en porcentajes del PIB
    1242: 821,   # Ingresos tributarios por tipo de impuestos en porcentajes del PIB
    1243: 740,   # Saldo en cuenta corriente como porcentaje del producto interno bruto
    1244: 883,   # Índices de la relación de precios del intercambio y poder de compra de las exportaciones
    5683: 3154,  # Proporción de energía renovable en la oferta de energía primaria
    4406: 460,   # Gasto público en educación
    1318: 3097,  # Porcentaje de población que utiliza fuentes mejoradas de abastecimiento de agua
    3333: 2288,  # Relación del ingreso medio entre mujeres y hombres, por grupo de edad y área
    2949: 2050,  # Balanza de pagos
    2954: 883,   # Índices de la relación de precios del intercambio
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
    # 17b. IPC subyacente
    4145: IndicatorMetadata(
        indicator_id=4145,
        name="Tasa de crecimiento anual del índice de precios al consumidor subyacente: diciembre a diciembre",
        concept="IPC_SUBYACENTE",
        measure_type=MeasureType.TASA_VARIACION_INTERANUAL,
        unit="%",
        supported_facets=set(),
        relationships={
            2928: RelationshipType.ALTERNATIVE_MEASURE,
            2484: RelationshipType.ALTERNATIVE_MEASURE,
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
            845: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 20b. Ingresos tributarios en moneda nacional
    845: IndicatorMetadata(
        indicator_id=845,
        name="Ingresos tributarios por tipo de impuestos, en moneda nacional a precios corrientes (América Latina y el Caribe)",
        concept="INGRESOS_TRIBUTARIOS_CORRIENTES",
        measure_type=MeasureType.VALOR_CORRIENTE,
        unit="moneda nacional",
        supported_facets=set(),
        relationships={
            1242: RelationshipType.ALTERNATIVE_MEASURE,
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
    # Demographic / Population Indicators
    4788: IndicatorMetadata(
        indicator_id=4788,
        name="Población total",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="personas",
        supported_facets={"sexo"},
        relationships={
            4968: RelationshipType.BREAKDOWN_OF,
            4969: RelationshipType.BREAKDOWN_OF,
            4992: RelationshipType.BREAKDOWN_OF,
            4639: RelationshipType.BREAKDOWN_OF,
        },
    ),
    4968: IndicatorMetadata(
        indicator_id=4968,
        name="Población indígena y no indígena según área de residencia",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="personas",
        supported_facets={"area", "etnia"},
        relationships={
            4788: RelationshipType.BREAKDOWN_OF,
            4992: RelationshipType.BREAKDOWN_OF,
        },
    ),
    4969: IndicatorMetadata(
        indicator_id=4969,
        name="Población afrodescendiente según área de residencia",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="personas",
        supported_facets={"area", "etnia"},
        relationships={
            4788: RelationshipType.BREAKDOWN_OF,
            4992: RelationshipType.BREAKDOWN_OF,
        },
    ),
    4992: IndicatorMetadata(
        indicator_id=4992,
        name="Población según área urbana y rural",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="personas",
        supported_facets={"area"},
        relationships={
            4788: RelationshipType.BREAKDOWN_OF,
            4968: RelationshipType.BREAKDOWN_OF,
            4969: RelationshipType.BREAKDOWN_OF,
        },
    ),
    4639: IndicatorMetadata(
        indicator_id=4639,
        name="Población por quintil de ingreso y etnia",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="personas",
        supported_facets={"sexo", "estrato", "quintil", "etnia"},
        relationships={
            4788: RelationshipType.BREAKDOWN_OF,
        },
    ),
}

# Concept to Canonical Default mappings
OFFICIAL_25_CANONICAL_DEFAULTS: dict[str, int] = {
    "POBLACION": 4788,
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
    "IPC_SUBYACENTE": 4145,
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
    "INGRESOS_TRIBUTARIOS_CORRIENTES": 845,
    "GASTO_SOCIAL": 4405,
    "GASTO_EDUCACION": 4406,
    "EMISIONES_GEI_LULUCF": 5681,
    "EMISIONES_GEI_SIN_LULUCF": 5682,
    "ENERGIA_RENOVABLE": 5683,
    "AGUA_DULCE": 1318,
    "BRECHA_SALARIAL": 3333,
}

LEGACY_50_CANONICAL_DEFAULTS: dict[str, int] = {
    "POBLACION": 4788,
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
    "IPC_SUBYACENTE": 4145,
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
    "INGRESOS_TRIBUTARIOS_CORRIENTES": 845,
    "GASTO_SOCIAL": 4405,
    "GASTO_EDUCACION": 4406,
    "EMISIONES_GEI_LULUCF": 5681,
    "EMISIONES_GEI_SIN_LULUCF": 5682,
    "ENERGIA_RENOVABLE": 5683,
    "AGUA_DULCE": 1318,
    "BRECHA_SALARIAL": 3333,
}

CONCEPT_CANONICAL_DEFAULTS = OFFICIAL_25_CANONICAL_DEFAULTS

BADEHOG_SURVEY_INDICATORS: tuple[int, ...] = (
    3328,
    3329,
    3330,
    3339,
    3340,
    3341,
    3342,
    3345,
    3289,
)

# Empirical observation availability for country x year x indicator
# Maps (indicator_id, country_code, year) -> (status, prev_anchor, next_anchor)
TEMPORAL_AVAILABILITY_MATRIX: dict[tuple[int, str, int], tuple[TemporalAvailabilityStatus, int | None, int | None]] = {
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
}

for _badehog_id in BADEHOG_SURVEY_INDICATORS:
    # Chile (CASEN biennial/triennial: 2017, 2020, 2022; no 2021 survey)
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "CHL", 2020)] = (
        TemporalAvailabilityStatus.OBSERVATION_EXISTING,
        None,
        None,
    )
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "CHL", 2021)] = (
        TemporalAvailabilityStatus.PERIOD_UNOBSERVED,
        2020,
        2022,
    )
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "CHL", 2022)] = (
        TemporalAvailabilityStatus.OBSERVATION_EXISTING,
        None,
        None,
    )
    # Mexico (ENIGH biennial even years: 2020, 2022; no 2021 survey)
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "MEX", 2020)] = (
        TemporalAvailabilityStatus.OBSERVATION_EXISTING,
        None,
        None,
    )
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "MEX", 2021)] = (
        TemporalAvailabilityStatus.PERIOD_UNOBSERVED,
        2020,
        2022,
    )
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "MEX", 2022)] = (
        TemporalAvailabilityStatus.OBSERVATION_EXISTING,
        None,
        None,
    )
    # Continuous annual surveys (BRA, PER, CRI)
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "BRA", 2021)] = (
        TemporalAvailabilityStatus.OBSERVATION_EXISTING,
        None,
        None,
    )
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "PER", 2021)] = (
        TemporalAvailabilityStatus.OBSERVATION_EXISTING,
        None,
        None,
    )
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "CRI", 2022)] = (
        TemporalAvailabilityStatus.OBSERVATION_EXISTING,
        None,
        None,
    )



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
        ontology: FacetOntology | None = None,
    ) -> None:
        self.store = store
        self.catalog_profile = catalog_profile
        self.ontology = ontology or DEFAULT_FACET_ONTOLOGY
        self._dimensions = dimensions or {}
        self._relationships = relationships or {}
        self._temporal_availability = temporal_availability or {}

        self._indicators_cache: dict[int, IndicatorMetadata] = {}
        self._dimensions_cache: dict[int, list[Dimension]] = {}
        self._relationships_cache: dict[int, dict[int, RelationshipType]] = {}
        self._relationship_provenance: dict[tuple[int, int], str] = {}

        self._build_in_memory_index(explicit_dimensions=dimensions, explicit_relationships=relationships)

    def _build_in_memory_index(
        self,
        explicit_dimensions: dict[int, list[Dimension]] | None = None,
        explicit_relationships: dict[Any, Any] | None = None,
    ) -> None:
        """Build ultra-fast in-memory index from static fallback seeds overlaid with SQLite store."""
        # 1. Static Fallback Seeds
        self._indicators_cache = {
            k: IndicatorMetadata(
                indicator_id=v.indicator_id,
                name=v.name,
                concept=v.concept,
                measure_type=v.measure_type,
                unit=v.unit,
                supported_facets=set(v.supported_facets),
                relationships=dict(v.relationships),
            )
            for k, v in VERTICAL_SLICE_INDICATORS.items()
        }
        self._dimensions_cache = {k: list(v) for k, v in DEFAULT_OFFICIAL_DIMENSIONS.items()}
        self._relationships_cache = {}
        self._relationship_provenance = {}

        for k, v in VERTICAL_SLICE_INDICATORS.items():
            self._relationships_cache[k] = {}
            if v.relationships:
                for target, r in v.relationships.items():
                    r_enum = r if isinstance(r, RelationshipType) else RelationshipType(r)
                    self._relationships_cache[k][target] = r_enum
                    self._relationship_provenance[(k, target)] = "curated"

        # 2. SQLite CatalogStore Overlay (if self.store is not None)
        if self.store is not None:
            # Dimensions overlay: overriding fallback seeds for indicators present in SQLite
            store_dims = self.store.get_all_indicator_dimensions()
            for ind_id, dims in store_dims.items():
                self._dimensions_cache[ind_id] = dims

            # Indicator metadata overlay: update or create IndicatorMetadata
            store_meta = self.store.get_all_indicator_metadata()
            for ind_id, m_dict in store_meta.items():
                if ind_id in self._indicators_cache:
                    meta = self._indicators_cache[ind_id]
                    meta.name = m_dict["name"]
                    meta.concept = m_dict["concept"]
                    meta.measure_type = m_dict["measure_type"]
                    meta.unit = m_dict["unit"]
                    meta.supported_facets.update(m_dict["supported_facets"])
                else:
                    self._indicators_cache[ind_id] = IndicatorMetadata(
                        indicator_id=ind_id,
                        name=m_dict["name"],
                        concept=m_dict["concept"],
                        measure_type=m_dict["measure_type"],
                        unit=m_dict["unit"],
                        supported_facets=set(m_dict["supported_facets"]),
                        relationships={},
                    )

            # Query master_indicators from self.store: synthesize IndicatorMetadata if not present
            master_indicators = self.store.get_all_master_indicators()
            for row in master_indicators:
                ind_id = int(row["indicator_id"])
                if ind_id not in self._indicators_cache:
                    concept_val = row.get("subarea") or row.get("area") or "GENERAL"
                    self._indicators_cache[ind_id] = IndicatorMetadata(
                        indicator_id=ind_id,
                        name=str(row["name"]),
                        concept=concept_val,
                        measure_type="SERIE_ESTADISTICA",
                        unit="",
                        supported_facets=set(),
                        relationships={},
                    )

            # Classify dimensions for every indicator in _indicators_cache and union non-structural facets
            for ind_id, meta in self._indicators_cache.items():
                dims = self._dimensions_cache.get(ind_id, [])
                for d in dims:
                    f = self.ontology.classify_dimension(d.id, d.name)
                    if f and f != "__structural__":
                        meta.supported_facets.add(f)

            # Load self.store.get_all_relationships() respecting curated precedence
            store_rels = self.store.get_all_relationships()
            for rel in store_rels:
                ind_a = int(rel["indicator_a"])
                ind_b = int(rel["indicator_b"])
                raw_type = rel["rel_type"]
                prov = rel.get("provenance") or "curated"

                existing_prov = self._relationship_provenance.get((ind_a, ind_b))
                if existing_prov == "curated" and prov == "inferred":
                    continue

                try:
                    r_enum = RelationshipType(raw_type) if not isinstance(raw_type, RelationshipType) else raw_type
                except ValueError:
                    try:
                        r_enum = RelationshipType[str(raw_type).upper()]
                    except KeyError:
                        continue

                self._relationships_cache.setdefault(ind_a, {})[ind_b] = r_enum
                self._relationship_provenance[(ind_a, ind_b)] = prov
                if ind_a in self._indicators_cache:
                    self._indicators_cache[ind_a].relationships[ind_b] = r_enum
        else:
            # If store is None, still classify dimensions for indicators in fallback seeds
            for ind_id, meta in self._indicators_cache.items():
                dims = self._dimensions_cache.get(ind_id, [])
                for d in dims:
                    f = self.ontology.classify_dimension(d.id, d.name)
                    if f and f != "__structural__":
                        meta.supported_facets.add(f)

        # 3. Constructor Explicit Overrides
        dims_override = explicit_dimensions if explicit_dimensions is not None else self._dimensions
        if dims_override:
            self._dimensions_cache.update(dims_override)
            for ind_id, dims in dims_override.items():
                if ind_id in self._indicators_cache:
                    meta = self._indicators_cache[ind_id]
                    for d in dims:
                        f = self.ontology.classify_dimension(d.id, d.name)
                        if f and f != "__structural__":
                            meta.supported_facets.add(f)

        rels_override = explicit_relationships if explicit_relationships is not None else self._relationships
        if rels_override:
            for k, val in rels_override.items():
                if isinstance(val, dict):
                    ind_a = k
                    for target, r in val.items():
                        r_enum = r if isinstance(r, RelationshipType) else RelationshipType(r)
                        self._relationships_cache.setdefault(ind_a, {})[target] = r_enum
                        if ind_a in self._indicators_cache:
                            self._indicators_cache[ind_a].relationships[target] = r_enum
                elif isinstance(k, tuple) and len(k) == 2:
                    ind_a, target = k
                    r_enum = val if isinstance(val, RelationshipType) else RelationshipType(val)
                    self._relationships_cache.setdefault(ind_a, {})[target] = r_enum
                    if ind_a in self._indicators_cache:
                        self._indicators_cache[ind_a].relationships[target] = r_enum

    def reload_from_store(self) -> None:
        """Rebuild in-memory index from store."""
        self._build_in_memory_index(explicit_dimensions=self._dimensions, explicit_relationships=self._relationships)

    def get_indicator(self, indicator_id: int) -> IndicatorMetadata | None:
        """Get indicator metadata from in-memory index or attached SQLite store on cache miss."""
        if indicator_id in self._indicators_cache:
            return self._indicators_cache[indicator_id]

        if self.store is not None:
            raw = self.store.get_indicator_metadata(indicator_id)
            if raw:
                store_rels = self.store.get_relationships(indicator_id)
                typed_rels: dict[int, RelationshipType] = {}
                for t, r in store_rels.items():
                    try:
                        typed_rels[t] = RelationshipType(r) if not isinstance(r, RelationshipType) else r
                    except ValueError:
                        try:
                            typed_rels[t] = RelationshipType[str(r).upper()]
                        except KeyError:
                            pass
                meta = IndicatorMetadata(
                    indicator_id=raw["indicator_id"],
                    name=raw["name"],
                    concept=raw["concept"],
                    measure_type=raw["measure_type"],
                    unit=raw["unit"],
                    supported_facets=set(raw["supported_facets"]),
                    relationships=typed_rels,
                )
                for d in self.get_dimensions(indicator_id):
                    f = self.ontology.classify_dimension(d.id, d.name)
                    if f and f != "__structural__":
                        meta.supported_facets.add(f)
                self._indicators_cache[indicator_id] = meta
                return meta

            # Check master_indicators on miss
            with self.store._get_connection() as conn:
                try:
                    row = conn.execute(
                        "SELECT indicator_id, name, theme, area, subarea FROM master_indicators WHERE indicator_id = ?",
                        (indicator_id,),
                    ).fetchone()
                    if row:
                        subarea = row["subarea"] if "subarea" in row.keys() else ""
                        area = row["area"] if "area" in row.keys() else ""
                        concept_val = subarea or area or "GENERAL"
                        meta = IndicatorMetadata(
                            indicator_id=int(row["indicator_id"]),
                            name=str(row["name"]),
                            concept=concept_val,
                            measure_type="SERIE_ESTADISTICA",
                            unit="",
                            supported_facets=set(),
                            relationships={},
                        )
                        for d in self.get_dimensions(indicator_id):
                            f = self.ontology.classify_dimension(d.id, d.name)
                            if f and f != "__structural__":
                                meta.supported_facets.add(f)
                        self._indicators_cache[indicator_id] = meta
                        return meta
                except sqlite3.OperationalError:
                    pass

        return None

    def get_canonical_default(self, concept: str) -> int | None:
        """Get canonical indicator ID for a given normalized statistical concept."""
        if self.catalog_profile == "legacy_50":
            return LEGACY_50_CANONICAL_DEFAULTS.get(concept)
        return OFFICIAL_25_CANONICAL_DEFAULTS.get(concept)

    def get_dimensions(self, indicator_id: int) -> list[Dimension]:
        """Get dimensions for an indicator, checking in-memory cache then store."""
        if indicator_id in self._dimensions_cache:
            return self._dimensions_cache[indicator_id]
        if self.store is not None:
            dims = self.store.get_indicator_dimensions(indicator_id)
            if dims:
                self._dimensions_cache[indicator_id] = dims
                return dims
        return self._dimensions.get(indicator_id, [])

    def get_relationships(self, indicator_id: int) -> dict[int, RelationshipType]:
        """Get all typed relationships originating from indicator_id across all sources."""
        cached = self._relationships_cache.get(indicator_id)
        if cached:
            return dict(cached)

        if self.store is not None:
            store_rels = self.store.get_relationships(indicator_id)
            if store_rels:
                typed_rels: dict[int, RelationshipType] = {}
                for target, r in store_rels.items():
                    try:
                        r_enum = RelationshipType(r) if not isinstance(r, RelationshipType) else r
                    except ValueError:
                        try:
                            r_enum = RelationshipType[str(r).upper()]
                        except KeyError:
                            continue
                    typed_rels[target] = r_enum
                self._relationships_cache.setdefault(indicator_id, {}).update(typed_rels)
                return dict(self._relationships_cache[indicator_id])

        return dict(self._relationships_cache.get(indicator_id, {}))

    def get_supported_facets(self, indicator_id: int) -> set[str]:
        """Get set of supported facets for an indicator from metadata and dimensions."""
        if indicator_id in self._indicators_cache:
            return set(self._indicators_cache[indicator_id].supported_facets)

        facets: set[str] = set()
        meta = self.get_indicator(indicator_id)
        if meta and meta.supported_facets:
            facets.update(meta.supported_facets)

        for d in self.get_dimensions(indicator_id):
            f = self.ontology.classify_dimension(d.id, d.name)
            if f and f != "__structural__":
                facets.add(f)

        return facets

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
