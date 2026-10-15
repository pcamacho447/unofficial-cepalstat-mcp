"""Metadata registry and typed relationship graph for the vertical slice."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from statscepal.dimensions import Dimension
from statscepal.semantic.models import (
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
        measure_type: str,
        unit: str,
        supported_facets: set[str],
        relationships: dict[int, RelationshipType] | None = None,
    ):
        self.indicator_id = indicator_id
        self.name = name
        self.concept = concept
        self.measure_type = measure_type
        self.unit = unit
        self.supported_facets = supported_facets
        self.relationships = relationships or {}


# Static registry for the vertical slice domain (Poverty, Employment, Macro)
VERTICAL_SLICE_INDICATORS: dict[int, IndicatorMetadata] = {
    3328: IndicatorMetadata(
        indicator_id=3328,
        name="Población en situación de pobreza extrema y pobreza, por área",
        concept="POBREZA",
        measure_type="INCIDENCIA_PORCENTUAL",
        unit="%",
        supported_facets={"area", "severidad"},
        relationships={
            3341: RelationshipType.BREAKDOWN_OF,
            3330: RelationshipType.ALTERNATIVE_MEASURE,
            3337: RelationshipType.ALTERNATIVE_MEASURE,
            4322: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    3341: IndicatorMetadata(
        indicator_id=3341,
        name="Tasa de incidencia de la pobreza según sexo y edad",
        concept="POBREZA",
        measure_type="INCIDENCIA_PORCENTUAL",
        unit="%",
        supported_facets={"sexo", "edad", "area", "severidad"},
        relationships={
            3328: RelationshipType.BREAKDOWN_OF,
            3330: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    3330: IndicatorMetadata(
        indicator_id=3330,
        name="Índice de feminidad de la pobreza",
        concept="POBREZA",
        measure_type="RATIO_RELATIVO",
        unit="Mujeres por cada 100 hombres",
        supported_facets={"sexo"},
        relationships={
            3328: RelationshipType.ALTERNATIVE_MEASURE,
            3341: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    127: IndicatorMetadata(
        indicator_id=127,
        name="Tasa de desocupación por sexo",
        concept="EMPLEO",
        measure_type="TASA_DESOCUPACION",
        unit="%",
        supported_facets={"sexo", "formalidad"},
        relationships={
            5097: RelationshipType.BREAKDOWN_OF,
            3344: RelationshipType.BREAKDOWN_OF,
            119: RelationshipType.ALTERNATIVE_MEASURE,
            340: RelationshipType.RELATED_CONCEPT,
        },
    ),
    5097: IndicatorMetadata(
        indicator_id=5097,
        name="Tasa de desempleo, por sexo y edad - 19ª CIET (%)",
        concept="EMPLEO",
        measure_type="TASA_DESOCUPACION",
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
        measure_type="TASA_DESOCUPACION_URBANA",
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
        measure_type="VOLUMEN_REAL",
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
        measure_type="VALOR_CORRIENTE",
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
        measure_type="VOLUMEN_REAL_PER_CAPITA",
        unit="USD constantes por habitante",
        supported_facets=set(),
    ),
    2447: IndicatorMetadata(
        indicator_id=2447,
        name="Producto interno bruto (PIB) trimestral",
        concept="PIB_TRIMESTRAL",
        measure_type="VOLUMEN_REAL_TRIMESTRAL",
        unit="Millones de USD constantes",
        supported_facets=set(),
    ),
    340: IndicatorMetadata(
        indicator_id=340,
        name="Salario mínimo real",
        concept="SALARIO",
        measure_type="INDICE_REAL",
        unit="Índice base 2018=100",
        supported_facets={"area", "edad"},
    ),
    3289: IndicatorMetadata(
        indicator_id=3289,
        name="Índice de Gini de concentración del ingreso",
        concept="GINI",
        measure_type="COEFICIENTE_CONCENTRACION",
        unit="Coeficiente (0 a 1)",
        supported_facets=set(),
    ),
    365: IndicatorMetadata(
        indicator_id=365,
        name="Índice de precios al consumidor general",
        concept="IPC_GENERAL",
        measure_type="INDICE_PRECIOS",
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
        measure_type="INDICE_PRECIOS",
        unit="Índice base",
        supported_facets={"canasta"},
        relationships={
            365: RelationshipType.BREAKDOWN_OF,
            2929: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    2929: IndicatorMetadata(
        indicator_id=2929,
        name="Variación a doce meses del índice de precios al consumidor, alimentos y bebidas (%)",
        concept="INFLACION_ALIMENTOS",
        measure_type="VARIACION_PORCENTUAL_INTERANUAL",
        unit="%",
        supported_facets={"canasta"},
        relationships={
            365: RelationshipType.ALTERNATIVE_MEASURE,
            1684: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    2949: IndicatorMetadata(
        indicator_id=2949,
        name="Balanza comercial de bienes",
        concept="BALANZA_COMERCIAL",
        measure_type="SALDO_COMERCIAL",
        unit="Millones de USD",
        supported_facets=set(),
    ),
    740: IndicatorMetadata(
        indicator_id=740,
        name="Saldo en cuenta corriente como porcentaje del PIB",
        concept="CUENTA_CORRIENTE",
        measure_type="PORCENTAJE_PIB",
        unit="%",
        supported_facets=set(),
    ),
    4231: IndicatorMetadata(
        indicator_id=4231,
        name="Inversión extranjera directa entradas netas",
        concept="INVERSION_EXTRANJERA_DIRECTA",
        measure_type="FLUJO_CAPITAL",
        unit="Millones de USD",
        supported_facets=set(),
    ),
    2954: IndicatorMetadata(
        indicator_id=2954,
        name="Términos de intercambio de bienes",
        concept="TERMINOS_INTERCAMBIO",
        measure_type="INDICE_PRECIOS_RELATIVOS",
        unit="Índice base",
        supported_facets=set(),
    ),
    1240: IndicatorMetadata(
        indicator_id=1240,
        name="Saldo de la deuda pública del gobierno central en porcentaje del PIB",
        concept="DEUDA_PUBLICA",
        measure_type="PORCENTAJE_PIB",
        unit="%",
        supported_facets=set(),
    ),
    4405: IndicatorMetadata(
        indicator_id=4405,
        name="Gasto social público total como porcentaje del PIB",
        concept="GASTO_SOCIAL",
        measure_type="PORCENTAJE_PIB",
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
        measure_type="PORCENTAJE_PIB",
        unit="%",
        supported_facets=set(),
        relationships={
            4405: RelationshipType.BREAKDOWN_OF,
        },
    ),
    5681: IndicatorMetadata(
        indicator_id=5681,
        name="Emisiones de gases de efecto invernadero con uso de la tierra (LULUCF)",
        concept="EMISIONES_GEI_LULUCF",
        measure_type="VOLUMEN_EMISIONES",
        unit="Mt CO2 eq",
        supported_facets=set(),
        relationships={
            5682: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    5682: IndicatorMetadata(
        indicator_id=5682,
        name="Emisiones totales de GEI excluyendo sector UTCUTS / sin LULUCF",
        concept="EMISIONES_GEI_SIN_LULUCF",
        measure_type="VOLUMEN_EMISIONES",
        unit="Mt CO2 eq",
        supported_facets=set(),
        relationships={
            5681: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    1318: IndicatorMetadata(
        indicator_id=1318,
        name="Extracción de agua dulce por habitante",
        concept="AGUA_DULCE",
        measure_type="VOLUMEN_PER_CAPITA",
        unit="m3 por habitante",
        supported_facets=set(),
    ),
    3344: IndicatorMetadata(
        indicator_id=3344,
        name="Tasa de desocupación según sexo y edad",
        concept="DESEMPLEO_JUVENIL",
        measure_type="TASA_DESOCUPACION",
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
        measure_type="RATIO_RELATIVO",
        unit="Ratio mujeres/hombres",
        supported_facets={"sexo"},
        relationships={
            340: RelationshipType.RELATED_CONCEPT,
        },
    ),
}

# Concept to Canonical Default mapping
CONCEPT_CANONICAL_DEFAULTS: dict[str, int] = {
    "POBREZA": 3328,
    "EMPLEO": 127,
    "PIB": 2203,
    "PIB_CORRIENTE": 2204,
    "PIB_PER_CAPITA": 2206,
    "PIB_TRIMESTRAL": 2447,
    "SALARIO": 340,
    "GINI": 3289,
    "IPC_GENERAL": 365,
    "IPC_ALIMENTOS": 1684,
    "INFLACION_ALIMENTOS": 2929,
    "BALANZA_COMERCIAL": 2949,
    "CUENTA_CORRIENTE": 740,
    "INVERSION_EXTRANJERA_DIRECTA": 4231,
    "TERMINOS_INTERCAMBIO": 2954,
    "DEUDA_PUBLICA": 1240,
    "GASTO_SOCIAL": 4405,
    "GASTO_EDUCACION": 4406,
    "EMISIONES_GEI_LULUCF": 5681,
    "EMISIONES_GEI_SIN_LULUCF": 5682,
    "AGUA_DULCE": 1318,
    "DESEMPLEO_JUVENIL": 3344,
    "BRECHA_SALARIAL": 3333,
}

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
    ) -> None:
        self.store = store
        self._dimensions = dimensions or {}
        self._relationships = relationships or {}
        self._temporal_availability = temporal_availability or {}

    def get_indicator(self, indicator_id: int) -> IndicatorMetadata | None:
        return VERTICAL_SLICE_INDICATORS.get(indicator_id)

    def get_canonical_default(self, concept: str) -> int | None:
        return CONCEPT_CANONICAL_DEFAULTS.get(concept)

    def get_dimensions(self, indicator_id: int) -> list[Dimension]:
        if self.store is not None:
            dims = self.store.get_indicator_dimensions(indicator_id)
            if dims:
                return dims
        return self._dimensions.get(indicator_id, [])

    def check_relationship(self, indicator_a: int, indicator_b: int) -> RelationshipType | None:
        if self.store is not None:
            store_rels = self.store.get_relationships(indicator_a)
            if indicator_b in store_rels:
                rel_val = store_rels[indicator_b]
                if isinstance(rel_val, RelationshipType):
                    return rel_val
                try:
                    return RelationshipType(rel_val)
                except ValueError:
                    return RelationshipType[rel_val.upper()]

        if (indicator_a, indicator_b) in self._relationships:
            val = self._relationships[(indicator_a, indicator_b)]
            return val if isinstance(val, RelationshipType) else RelationshipType(val)
        if indicator_a in self._relationships and isinstance(self._relationships[indicator_a], dict):
            if indicator_b in self._relationships[indicator_a]:
                val = self._relationships[indicator_a][indicator_b]
                return val if isinstance(val, RelationshipType) else RelationshipType(val)

        ind_a = self.get_indicator(indicator_a)
        if not ind_a:
            return None
        return ind_a.relationships.get(indicator_b)

    def check_temporal_availability(
        self,
        indicator_id: int,
        country_code: str,
        year: int,
    ) -> tuple[TemporalAvailabilityStatus, int | None, int | None]:
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
