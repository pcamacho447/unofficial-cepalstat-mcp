"""Metadata registry and typed relationship graph for the vertical slice and 200-question suite."""

from __future__ import annotations

import heapq
import math
import sqlite3
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from unofficial_cepalstat_mcp.dimensions import (
    SYNTHETIC_DIMENSION_MEMBER_IDS as SYNTHETIC_DIMENSION_MEMBER_IDS,
)
from unofficial_cepalstat_mcp.dimensions import (
    Dimension,
    Member,
)
from unofficial_cepalstat_mcp.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY, FacetOntology
from unofficial_cepalstat_mcp.semantic.models import (
    AppliedDimensionFilter,
    MeasureType,
    RelationshipType,
    TemporalAvailabilityStatus,
)
from unofficial_cepalstat_mcp.semantic.parser import SPANISH_STOPWORDS
from unofficial_cepalstat_mcp.semantic.thesaurus import Thesaurus, get_default_thesaurus

_ACCENT_TRANS = str.maketrans('áéíóúüñÁÉÍÓÚÜÑ,.:;()[]{}"\'/\\-_', 'aeiouunAEIOUUN                ')
_SUFFIX_TUPLES = (
    ("ciones", "cion"),
    ("siones", "sion"),
    ("idades", "idad"),
    ("ales", "al"),
    ("ores", "or"),
    ("ados", "ad"),
    ("idos", "id"),
    ("icas", "ic"),
    ("icos", "ic"),
    ("ica", "ic"),
    ("ico", "ic"),
    ("ivas", "iv"),
    ("ivos", "iv"),
    ("iva", "iv"),
    ("ivo", "iv"),
    ("ada", "ad"),
    ("ida", "id"),
    ("ado", "ad"),
    ("ido", "id"),
    ("es", ""),
    ("os", ""),
    ("as", ""),
    ("s", ""),
)

_STEM_CACHE: dict[str, str] = {}

_COUNTRY_PREFIX_MAP: dict[str, str] = {
    "CHILE": "CHL", "BRASIL": "BRA", "BRAZIL": "BRA", "COLOMBIA": "COL",
    "MEXICO": "MEX", "ARGENTINA": "ARG", "URUGUAY": "URY", "PERU": "PER",
    "ECUADOR": "ECU", "BOLIVIA": "BOL", "PARAGUAY": "PRY", "PANAMA": "PAN",
    "GUATEMALA": "GTM", "HONDURAS": "HND", "CUBA": "CUB", "VENEZUELA": "VEN",
    "HAITI": "HTI", "JAMAICA": "JAM", "BELICE": "BLZ", "GUYANA": "GUY",
    "SURINAM": "SUR", "BAHAMAS": "BHS", "BARBADOS": "BRB",
    "COSTA RICA": "CRI", "EL SALVADOR": "SLV", "REPUBLICA DOMINICANA": "DOM",
    "TRINIDAD Y TOBAGO": "TTO",
}


def _stem_spanish(token: str) -> str:
    """Fast, deterministic Spanish suffix trimmer with memoization."""
    res = _STEM_CACHE.get(token)
    if res is not None:
        return res
    w = token
    if len(w) <= 3:
        _STEM_CACHE[token] = w
        return w
    for suf, rep in _SUFFIX_TUPLES:
        if w.endswith(suf) and len(w) - len(suf) + len(rep) >= 3:
            r = w[: -len(suf)] + rep
            _STEM_CACHE[token] = r
            return r
    _STEM_CACHE[token] = w
    return w

if TYPE_CHECKING:
    from unofficial_cepalstat_mcp.catalog.store import CatalogStore


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
        mandatory_filters: tuple[AppliedDimensionFilter, ...] = (),
    ):
        self.indicator_id = indicator_id
        self.name = name
        self.concept = concept
        self.measure_type = measure_type.value if isinstance(measure_type, MeasureType) else measure_type
        self.unit = unit
        self.supported_facets = supported_facets
        self.relationships = relationships or {}
        self.mandatory_filters = mandatory_filters


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
    3324: [
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
                Member(id=613, name="Relación quintil 5 / quintil 1"),
            ],
        ),
    ],
    3390: [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=600,
            name="Estrato de ingreso",
            members=[
                Member(id=610, name="Primer decil"),
                Member(id=611, name="Décimo decil"),
                Member(id=612, name="Deciles"),
            ],
        ),
    ],
    3295: [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
    ],
    2287: [
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
    2198: [],
    2484: [
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
    28: [
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
    4788: [
        Dimension(
            id=88622,
            name="Sexo",
            members=[Member(id=88623, name="Ambos sexos"), Member(id=88626, name="Hombres"), Member(id=88627, name="Mujeres")],
        ),
    ],
    4789: [
        Dimension(
            id=88622,
            name="Sexo",
            members=[Member(id=88623, name="Ambos sexos"), Member(id=88626, name="Hombres"), Member(id=88627, name="Mujeres")],
        ),
        Dimension(
            id=88628,
            name="Grupos quinquenales de edad",
            members=[
                Member(id=88630, name="0-4"),
                Member(id=88631, name="5-9"),
                Member(id=88632, name="10-14"),
                Member(id=88633, name="15-19"),
                Member(id=88634, name="20-24"),
                Member(id=88635, name="25-29"),
                Member(id=88636, name="30-34"),
                Member(id=88637, name="35-39"),
                Member(id=88638, name="40-44"),
                Member(id=88639, name="45-49"),
                Member(id=88640, name="50-54"),
                Member(id=88647, name="55-59"),
                Member(id=88648, name="60-64"),
                Member(id=88649, name="65-69"),
                Member(id=88650, name="70-74"),
                Member(id=88651, name="75-79"),
                Member(id=88644, name="80-84"),
                Member(id=88643, name="85-89"),
                Member(id=88641, name="90-94"),
                Member(id=88642, name="95-99"),
                Member(id=88629, name="100 y más"),
            ],
        ),
    ],
    4784: [
        Dimension(
            id=88622,
            name="Sexo",
            members=[Member(id=88623, name="Ambos sexos"), Member(id=88626, name="Hombres"), Member(id=88627, name="Mujeres")],
        ),
    ],
    417: [
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
            id=1435,
            name="Grandes sectores económicos",
            members=[Member(id=1436, name="Agricultura"), Member(id=1437, name="Industria"), Member(id=1438, name="Servicios")],
        ),
    ],
    122: [
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
            id=2145,
            name="Sector actividad económica",
            members=[
                Member(id=2148, name="Agricultura"),
                Member(id=2153, name="Comercio"),
                Member(id=2151, name="Construcción"),
                Member(id=2150, name="Electricidad, gas y agua"),
                Member(id=2147, name="Manufactureras"),
                Member(id=2154, name="Minería"),
                Member(id=2155, name="No especificados"),
                Member(id=2152, name="Otros servicios"),
                Member(id=2149, name="Servicios financieros"),
                Member(id=2146, name="Transporte"),
            ],
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
        Dimension(
            id=78149,
            name="Condición Indígena",
            members=[Member(id=78150, name="Indígena"), Member(id=78152, name="No Indígena"), Member(id=78154, name="Total")],
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
            members=[
                Member(id=29282, name="General"),
                Member(id=29283, name="Salud"),
                Member(id=29284, name="Transporte"),
                Member(id=29285, name="Vivienda y energía"),
            ],
        ),
    ],
    1684: [
        Dimension(
            id=79565,
            name="Canasta de bienes",
            members=[Member(id=79578, name="Alimentos y bebidas no alcohólicas")],
        ),
    ],
    2288: [
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
                Member(id=43060, name="65 años y más"),
            ],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
    ],
    5698: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
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
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
    ],
    1246: [
        Dimension(
            id=12461,
            name="Rubro",
            members=[Member(id=12462, name="Resultado primario")],
        ),
    ],
    883: [
        Dimension(
            id=8831,
            name="Rubro",
            members=[Member(id=8832, name="Relación de precios del intercambio de bienes")],
        ),
    ],
    2050: [
        Dimension(
            id=20501,
            name="Rubro",
            members=[Member(id=20502, name="Balanza de bienes")],
        ),
    ],
    286: [
        Dimension(
            id=2861,
            name="Rubro",
            members=[Member(id=2862, name="Producto interno bruto (Total)")],
        ),
    ],
    2193: [
        Dimension(
            id=21931,
            name="Rubro",
            members=[Member(id=21932, name="Producto interno bruto (Total)")],
        ),
    ],
    4410: [
        Dimension(
            id=44101,
            name="Función",
            members=[
                Member(id=44102, name="Total gasto social"),
                Member(id=44103, name="Salud"),
                Member(id=44104, name="Educación"),
                Member(id=44105, name="Protección social"),
            ],
        ),
    ],
    4185: [
        Dimension(
            id=41851,
            name="Sector",
            members=[Member(id=41852, name="Total extracción de agua")],
        ),
    ],
    821: [
        Dimension(
            id=8211,
            name="Rubro",
            members=[Member(id=8212, name="Total ingresos tributarios")],
        ),
    ],
    4145: [],
    845: [],
    2204: [],
}


# SYNTHETIC_DIMENSION_MEMBER_IDS is imported from unofficial_cepalstat_mcp.dimensions
# and re-exported here for backward compatibility.

# Mapping from synthetic/placeholder official_25 indicator IDs to real CEPALSTAT master_indicators IDs.
# Post-migration, all indicators use real CEPALSTAT IDs directly (empty map for backward compatibility).
EMPIRICAL_INDICATOR_ID_MAP: dict[int, int] = {}


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
            340: RelationshipType.ALTERNATIVE_MEASURE,
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
    # 5. Distribución del ingreso personas quintiles
    3324: IndicatorMetadata(
        indicator_id=3324,
        name="Distribución del ingreso de las personas, por quintiles y área",
        concept="DISTRIBUCION_INGRESO",
        measure_type=MeasureType.DISTRIBUCION_INGRESO,
        unit="%",
        supported_facets={"estrato", "quintil", "area"},
        relationships={
            3390: RelationshipType.BREAKDOWN_OF,
            3295: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 5b. Distribución del ingreso hogares deciles
    3390: IndicatorMetadata(
        indicator_id=3390,
        name="Distribución del ingreso de los hogares, por deciles y área",
        concept="DISTRIBUCION_INGRESO",
        measure_type=MeasureType.DISTRIBUCION_INGRESO,
        unit="%",
        supported_facets={"estrato", "decil", "area"},
        relationships={
            3324: RelationshipType.BREAKDOWN_OF,
            3295: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 5c. Ratio Q5/Q1
    3295: IndicatorMetadata(
        indicator_id=3295,
        name="Relación del ingreso medio del quintil 5 respecto al quintil 1",
        concept="DISTRIBUCION_INGRESO",
        measure_type=MeasureType.RATIO_RELATIVO,
        unit="ratio",
        supported_facets={"area"},
        relationships={
            3324: RelationshipType.ALTERNATIVE_MEASURE,
            3390: RelationshipType.ALTERNATIVE_MEASURE,
        },
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
            119: RelationshipType.ALTERNATIVE_MEASURE,
            340: RelationshipType.RELATED_CONCEPT,
        },
    ),
    # 7. Desempleo juvenil 19ª CIET
    5097: IndicatorMetadata(
        indicator_id=5097,
        name="Tasa de desempleo, por sexo y edad - 19ª CIET (%)",
        concept="DESEMPLEO_JUVENIL",
        measure_type=MeasureType.TASA_DESOCUPACION,
        unit="%",
        supported_facets={"sexo", "edad"},
        relationships={
            127: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 8. Salario medio real
    341: IndicatorMetadata(
        indicator_id=341,
        name="Salario medio real anual",
        concept="SALARIO_MEDIO",
        measure_type=MeasureType.INDICE_REAL,
        unit="índice 2018=100",
        supported_facets=set(),
        relationships={
            2287: RelationshipType.BREAKDOWN_OF,
            340: RelationshipType.ALTERNATIVE_MEASURE,
            2198: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 9. Salario mínimo real
    340: IndicatorMetadata(
        indicator_id=340,
        name="Salario mínimo real",
        concept="SALARIO_MINIMO",
        measure_type=MeasureType.INDICE_REAL,
        unit="índice 2018=100",
        supported_facets={"area", "edad"},
        relationships={
            341: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 10. Ingreso medio de la población ocupada
    2287: IndicatorMetadata(
        indicator_id=2287,
        name="Ingreso medio de la población ocupada, por sexo e inserción laboral",
        concept="INGRESO_LABORAL",
        measure_type=MeasureType.MONTO_MONEDA_LOCAL,
        unit="moneda local",
        supported_facets={"sexo", "area", "formalidad"},
        relationships={
            341: RelationshipType.BREAKDOWN_OF,
            5698: RelationshipType.BREAKDOWN_OF,
            2288: RelationshipType.RELATED_CONCEPT,
        },
    ),
    # 11. Ingresos y gastos de los hogares
    2198: IndicatorMetadata(
        indicator_id=2198,
        name="Ingresos y gastos de los hogares a precios corrientes en moneda nacional",
        concept="INGRESO_HOGARES",
        measure_type=MeasureType.MONTO_MONEDA_LOCAL,
        unit="moneda local",
        supported_facets=set(),
        relationships={
            341: RelationshipType.ALTERNATIVE_MEASURE,
            2287: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 11b. Ingreso ocupados etnia/área
    5698: IndicatorMetadata(
        indicator_id=5698,
        name="Ingreso medio de la población ocupada, por sexo, autoidentificación étnico-racial y área",
        concept="INGRESO_LABORAL",
        measure_type=MeasureType.MONTO_MONEDA_LOCAL,
        unit="moneda local",
        supported_facets={"sexo", "etnia", "area"},
        relationships={
            2287: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 11c. Brecha salarial mujeres/hombres
    2288: IndicatorMetadata(
        indicator_id=2288,
        name="Relación del ingreso medio entre mujeres y hombres, por grupo de edad y área",
        concept="BRECHA_SALARIAL",
        measure_type=MeasureType.RATIO_RELATIVO,
        unit="Ratio mujeres/hombres",
        supported_facets={"sexo", "edad", "area"},
        relationships={
            340: RelationshipType.RELATED_CONCEPT,
            2287: RelationshipType.RELATED_CONCEPT,
        },
    ),
    # 12. PIB total anual a precios constantes USD
    2204: IndicatorMetadata(
        indicator_id=2204,
        name="Producto interno bruto (PIB) total anual a precios constantes en dólares",
        concept="PIB",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="Millones de USD constantes",
        supported_facets={"moneda"},
        relationships={
            2206: RelationshipType.BREAKDOWN_OF,
            286: RelationshipType.ALTERNATIVE_MEASURE,
            2203: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 12b. PIB total anual a precios corrientes USD
    2203: IndicatorMetadata(
        indicator_id=2203,
        name="Producto interno bruto (PIB) total anual a precios corrientes en dólares",
        concept="PIB_CORRIENTE",
        measure_type=MeasureType.VALOR_CORRIENTE,
        unit="Millones de USD corrientes",
        supported_facets=set(),
        relationships={
            2204: RelationshipType.ALTERNATIVE_MEASURE,
            2193: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 12c. PIB total anual a precios corrientes MN
    2193: IndicatorMetadata(
        indicator_id=2193,
        name="Producto interno bruto anual (PIB) por objeto del gasto a precios corrientes en moneda nacional",
        concept="PIB_CORRIENTE",
        measure_type=MeasureType.VALOR_CORRIENTE,
        unit="Millones de moneda nacional",
        supported_facets={"rubro", "moneda"},
        relationships={
            2203: RelationshipType.ALTERNATIVE_MEASURE,
            2204: RelationshipType.ALTERNATIVE_MEASURE,
        },
        mandatory_filters=(
            AppliedDimensionFilter(
                dim_id=21931,
                dim_name="Rubro",
                member_id=21932,
                member_name="Producto interno bruto (Total)",
            ),
        ),
    ),
    # 13. PIB per cápita constante USD
    2206: IndicatorMetadata(
        indicator_id=2206,
        name="Producto interno bruto (PIB) total anual por habitante a precios constantes en dólares",
        concept="PIB_PER_CAPITA",
        measure_type=MeasureType.VOLUMEN_REAL_PER_CAPITA,
        unit="USD constantes por habitante",
        supported_facets=set(),
        relationships={
            2204: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # 14. PIB trimestral precios constantes MN
    286: IndicatorMetadata(
        indicator_id=286,
        name="Producto interno bruto trimestral por tipo del gasto a precios constantes en moneda nacional",
        concept="PIB_TRIMESTRAL",
        measure_type=MeasureType.VOLUMEN_REAL_TRIMESTRAL,
        unit="Millones de moneda nacional",
        supported_facets={"rubro"},
        relationships={
            2204: RelationshipType.ALTERNATIVE_MEASURE,
        },
        mandatory_filters=(
            AppliedDimensionFilter(
                dim_id=2861,
                dim_name="Rubro",
                member_id=2862,
                member_name="Producto interno bruto (Total)",
            ),
        ),
    ),
    # 15. IPC general variación anual
    2484: IndicatorMetadata(
        indicator_id=2484,
        name="Tasa de crecimiento anual del índice de precios al consumidor: diciembre a diciembre",
        concept="IPC_GENERAL",
        measure_type=MeasureType.TASA_VARIACION_INTERANUAL,
        unit="%",
        supported_facets={"rubro"},
        relationships={
            2929: RelationshipType.BREAKDOWN_OF,
            365: RelationshipType.BREAKDOWN_OF,
            4145: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 16. IPC alimentos variación anual
    2929: IndicatorMetadata(
        indicator_id=2929,
        name="Tasa de crecimiento anual del índice de precios al consumidor alimentos: diciembre a diciembre",
        concept="IPC_ALIMENTOS",
        measure_type=MeasureType.TASA_VARIACION_INTERANUAL,
        unit="%",
        supported_facets={"canasta"},
        relationships={
            2484: RelationshipType.BREAKDOWN_OF,
            1684: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 17. IPC general y por división (nivel)
    365: IndicatorMetadata(
        indicator_id=365,
        name="Índice de precios al consumidor general",
        concept="IPC_GENERAL",
        measure_type=MeasureType.INDICE_PRECIOS,
        unit="Índice base",
        supported_facets={"rubro"},
        relationships={
            1684: RelationshipType.BREAKDOWN_OF,
            2484: RelationshipType.ALTERNATIVE_MEASURE,
        },
        mandatory_filters=(
            AppliedDimensionFilter(
                dim_id=29281,
                dim_name="Rubro",
                member_id=29282,
                member_name="General",
            ),
        ),
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
            2484: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 17c. IPC alimentos nivel
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
    # 18. Deuda pública % PIB
    1240: IndicatorMetadata(
        indicator_id=1240,
        name="Saldo de la deuda pública del gobierno central en porcentaje del PIB",
        concept="DEUDA_PUBLICA",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
        relationships={
            1246: RelationshipType.ALTERNATIVE_MEASURE,
            821: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 19. Balance primario % PIB
    1246: IndicatorMetadata(
        indicator_id=1246,
        name="Operaciones del gobierno (clasificación económica), en porcentajes del PIB",
        concept="BALANCE_PRIMARIO",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets={"rubro"},
        relationships={
            1240: RelationshipType.ALTERNATIVE_MEASURE,
        },
        mandatory_filters=(
            AppliedDimensionFilter(
                dim_id=12461,
                dim_name="Rubro",
                member_id=12462,
                member_name="Resultado primario",
            ),
        ),
    ),
    # 20. Ingresos tributarios % PIB
    821: IndicatorMetadata(
        indicator_id=821,
        name="Ingresos tributarios por tipo de impuestos en porcentajes del PIB",
        concept="INGRESOS_TRIBUTARIOS",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets={"rubro"},
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
        supported_facets={"moneda"},
        relationships={
            821: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    # 21. Cuenta corriente % PIB
    740: IndicatorMetadata(
        indicator_id=740,
        name="Saldo en cuenta corriente como porcentaje del PIB",
        concept="CUENTA_CORRIENTE",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
        relationships={},
    ),
    # 22. Términos de intercambio
    883: IndicatorMetadata(
        indicator_id=883,
        name="Índices de la relación de precios del intercambio y poder de compra de las exportaciones",
        concept="TERMINOS_INTERCAMBIO",
        measure_type=MeasureType.INDICE_PRECIOS_RELATIVOS,
        unit="índice 2018=100",
        supported_facets={"rubro"},
        relationships={},
        mandatory_filters=(
            AppliedDimensionFilter(
                dim_id=8831,
                dim_name="Rubro",
                member_id=8832,
                member_name="Relación de precios del intercambio de bienes",
            ),
        ),
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
    3154: IndicatorMetadata(
        indicator_id=3154,
        name="Proporción de energía renovable en la oferta de energía primaria",
        concept="ENERGIA_RENOVABLE",
        measure_type=MeasureType.PORCENTAJE_GENERACION,
        unit="%",
        supported_facets=set(),
        relationships={},
    ),
    # Balanza comercial de bienes (FOB)
    2050: IndicatorMetadata(
        indicator_id=2050,
        name="Balanza de pagos",
        concept="BALANZA_COMERCIAL",
        measure_type=MeasureType.SALDO_COMERCIAL,
        unit="Millones de USD",
        supported_facets={"rubro"},
        relationships={},
        mandatory_filters=(
            AppliedDimensionFilter(
                dim_id=20501,
                dim_name="Rubro",
                member_id=20502,
                member_name="Balanza de bienes",
            ),
        ),
    ),
    # Desocupación abierta urbana
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
    # Gini
    3289: IndicatorMetadata(
        indicator_id=3289,
        name="Índice de Gini de concentración del ingreso",
        concept="GINI",
        measure_type=MeasureType.COEFICIENTE_CONCENTRACION,
        unit="Coeficiente (0 a 1)",
        supported_facets=set(),
        relationships={},
    ),
    # IED
    4231: IndicatorMetadata(
        indicator_id=4231,
        name="Inversión extranjera directa entradas netas",
        concept="INVERSION_EXTRANJERA_DIRECTA",
        measure_type=MeasureType.FLUJO_CAPITAL,
        unit="Millones de USD",
        supported_facets=set(),
        relationships={},
    ),
    # Gasto social en moneda nacional (metodología SOCX)
    4405: IndicatorMetadata(
        indicator_id=4405,
        name="Gasto social público y privado (metodología SOCX), en moneda nacional",
        concept="GASTO_SOCIAL",
        measure_type=MeasureType.MONTO_MONEDA_LOCAL,
        unit="moneda nacional",
        supported_facets=set(),
        relationships={
            4410: RelationshipType.ALTERNATIVE_MEASURE,
            460: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # Gasto público por función (COFOG) % PIB
    4410: IndicatorMetadata(
        indicator_id=4410,
        name="Gasto público por función (clasificación COFOG), en porcentajes del PIB",
        concept="GASTO_SOCIAL",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets={"funcion"},
        relationships={
            4405: RelationshipType.ALTERNATIVE_MEASURE,
            460: RelationshipType.BREAKDOWN_OF,
        },
        mandatory_filters=(
            AppliedDimensionFilter(
                dim_id=44101,
                dim_name="Función",
                member_id=44102,
                member_name="Total gasto social",
            ),
        ),
    ),
    # Gasto educación
    460: IndicatorMetadata(
        indicator_id=460,
        name="Gasto público en educación",
        concept="GASTO_EDUCACION",
        measure_type=MeasureType.PORCENTAJE_PIB,
        unit="%",
        supported_facets=set(),
        relationships={
            4410: RelationshipType.BREAKDOWN_OF,
        },
    ),
    # Extracción de agua por sector
    4185: IndicatorMetadata(
        indicator_id=4185,
        name="Extracción de agua, por sector",
        concept="AGUA_DULCE",
        measure_type=MeasureType.VOLUMEN_PER_CAPITA,
        unit="m3 por habitante",
        supported_facets={"rubro"},
        relationships={},
        mandatory_filters=(
            AppliedDimensionFilter(
                dim_id=41851,
                dim_name="Sector",
                member_id=41852,
                member_name="Total extracción de agua",
            ),
        ),
    ),
    # Demographic / Population Indicators
    417: IndicatorMetadata(
        indicator_id=417,
        name="Distribución de la población ocupada por sexo, grandes sectores de actividad económica y área",
        concept="OCUPACION",
        measure_type=MeasureType.INCIDENCIA_PORCENTUAL,
        unit="%",
        supported_facets={"sexo", "area", "actividad"},
        relationships={
            122: RelationshipType.BREAKDOWN_OF,
        },
    ),
    122: IndicatorMetadata(
        indicator_id=122,
        name="Distribución de la población ocupada por sexo,  sector de actividad económica y área",
        concept="OCUPACION",
        measure_type=MeasureType.INCIDENCIA_PORCENTUAL,
        unit="%",
        supported_facets={"sexo", "area", "actividad"},
        relationships={
            417: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
    4784: IndicatorMetadata(
        indicator_id=4784,
        name="Esperanza de vida al nacer, según sexo",
        concept="ESPERANZA_DE_VIDA",
        measure_type=MeasureType.ESPERANZA_VIDA,
        unit="años",
        supported_facets={"sexo"},
    ),
    4788: IndicatorMetadata(
        indicator_id=4788,
        name="Población total",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="miles de personas",
        supported_facets={"sexo"},
        relationships={
            4789: RelationshipType.BREAKDOWN_OF,
            28: RelationshipType.BREAKDOWN_OF,
            4968: RelationshipType.BREAKDOWN_OF,
            4969: RelationshipType.BREAKDOWN_OF,
            4639: RelationshipType.BREAKDOWN_OF,
        },
    ),
    4789: IndicatorMetadata(
        indicator_id=4789,
        name="Población, por grupos de edad, según sexo",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="miles de personas",
        supported_facets={"sexo", "edad"},
        relationships={
            4788: RelationshipType.BREAKDOWN_OF,
            28: RelationshipType.BREAKDOWN_OF,
        },
    ),
    28: IndicatorMetadata(
        indicator_id=28,
        name="Población, según área geográfica y sexo",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="miles de personas",
        supported_facets={"area", "sexo"},
        relationships={
            4788: RelationshipType.BREAKDOWN_OF,
            4968: RelationshipType.BREAKDOWN_OF,
            4969: RelationshipType.BREAKDOWN_OF,
        },
    ),
    4968: IndicatorMetadata(
        indicator_id=4968,
        name="Población indígena y no indígena según área de residencia",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="miles de personas",
        supported_facets={"area", "etnia"},
        relationships={
            4788: RelationshipType.BREAKDOWN_OF,
            28: RelationshipType.BREAKDOWN_OF,
        },
    ),
    4969: IndicatorMetadata(
        indicator_id=4969,
        name="Población afrodescendiente según área de residencia",
        concept="POBLACION",
        measure_type=MeasureType.VOLUMEN_REAL,
        unit="miles de personas",
        supported_facets={"area", "etnia"},
        relationships={
            4788: RelationshipType.BREAKDOWN_OF,
            28: RelationshipType.BREAKDOWN_OF,
        },
    ),
    4992: IndicatorMetadata(
        indicator_id=4992,
        name="Porcentaje de población indígena por área de residencia",
        concept="POBLACION",
        measure_type=MeasureType.INCIDENCIA_PORCENTUAL,
        unit="%",
        supported_facets={"area", "etnia"},
        relationships={
            28: RelationshipType.RELATED_CONCEPT,
            4968: RelationshipType.RELATED_CONCEPT,
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
    "ESPERANZA_DE_VIDA": 4784,
    "ESPERANZA_VIDA": 4784,
    "POBREZA": 3328,
    "POBREZA_BRECHA": 3329,
    "POBREZA_FEMINIDAD": 3330,
    "DISTRIBUCION_INGRESO": 3324,
    "OCUPACION": 417,
    "POBLACION_OCUPADA": 417,
    "EMPLEO": 127,
    "DESEMPLEO_JUVENIL": 5097,
    "DESEMPLEO_JUVENIL_15_24": 5097,
    "SALARIO": 341,
    "SALARIO_MEDIO": 341,
    "SALARIO_REAL": 341,
    "SALARIO_MINIMO": 340,
    "INGRESO_LABORAL": 2287,
    "INGRESO_HOGARES": 2198,
    "INGRESO_HOGAR_PER_CAPITA": 2198,
    "PIB": 2204,
    "PIB_CORRIENTE": 2193,
    "PIB_PER_CAPITA": 2206,
    "PIB_TRIMESTRAL": 286,
    "GINI": 3289,
    "IPC_GENERAL": 2484,
    "IPC_SUBYACENTE": 4145,
    "IPC_ALIMENTOS": 2929,
    "INFLACION_ALIMENTOS": 2929,
    "IPC_TRANSPORTE_ENERGIA": 365,
    "BALANZA_COMERCIAL": 2050,
    "CUENTA_CORRIENTE": 740,
    "CUENTA_CORRIENTE_740": 740,
    "INVERSION_EXTRANJERA_DIRECTA": 4231,
    "TERMINOS_INTERCAMBIO": 883,
    "DEUDA_PUBLICA": 1240,
    "BALANCE_PRIMARIO": 1246,
    "INGRESOS_TRIBUTARIOS": 821,
    "INGRESOS_TRIBUTARIOS_CORRIENTES": 845,
    "GASTO_SOCIAL": 4410,
    "GASTO_EDUCACION": 460,
    "EMISIONES_GEI_LULUCF": 5681,
    "EMISIONES_GEI_SIN_LULUCF": 5682,
    "ENERGIA_RENOVABLE": 3154,
    "AGUA_DULCE": 4185,
    "BRECHA_SALARIAL": 2288,
}

LEGACY_50_CANONICAL_DEFAULTS: dict[str, int] = {
    "POBLACION": 4788,
    "POBREZA": 3328,
    "POBREZA_BRECHA": 3329,
    "POBREZA_FEMINIDAD": 3330,
    "DISTRIBUCION_INGRESO": 3324,
    "OCUPACION": 417,
    "POBLACION_OCUPADA": 417,
    "EMPLEO": 127,
    "DESEMPLEO_JUVENIL": 5097,
    "DESEMPLEO_JUVENIL_15_24": 5097,
    "SALARIO": 340,
    "SALARIO_MEDIO": 341,
    "SALARIO_REAL": 341,
    "SALARIO_MINIMO": 340,
    "INGRESO_LABORAL": 2287,
    "INGRESO_HOGARES": 2198,
    "INGRESO_HOGAR_PER_CAPITA": 2198,
    "PIB": 2204,
    "PIB_CORRIENTE": 2203,
    "PIB_PER_CAPITA": 2206,
    "PIB_TRIMESTRAL": 286,
    "GINI": 3289,
    "IPC_GENERAL": 365,
    "IPC_SUBYACENTE": 4145,
    "IPC_ALIMENTOS": 1684,
    "INFLACION_ALIMENTOS": 2929,
    "IPC_TRANSPORTE_ENERGIA": 365,
    "BALANZA_COMERCIAL": 2050,
    "CUENTA_CORRIENTE": 740,
    "CUENTA_CORRIENTE_740": 740,
    "INVERSION_EXTRANJERA_DIRECTA": 4231,
    "TERMINOS_INTERCAMBIO": 883,
    "DEUDA_PUBLICA": 1240,
    "BALANCE_PRIMARIO": 1246,
    "INGRESOS_TRIBUTARIOS": 821,
    "INGRESOS_TRIBUTARIOS_CORRIENTES": 845,
    "GASTO_SOCIAL": 4410,
    "GASTO_EDUCACION": 460,
    "EMISIONES_GEI_LULUCF": 5681,
    "EMISIONES_GEI_SIN_LULUCF": 5682,
    "ENERGIA_RENOVABLE": 3154,
    "AGUA_DULCE": 4185,
    "BRECHA_SALARIAL": 2288,
}

CONCEPT_CANONICAL_DEFAULTS = OFFICIAL_25_CANONICAL_DEFAULTS

BADEHOG_SURVEY_INDICATORS: tuple[int, ...] = (
    3328,
    3329,
    3330,
    3341,
    3342,
    3289,
    3324,
    3390,
    2287,
    2288,
    5698,
    417,
    122,
)

QUINQUENNIAL_DEMOGRAPHIC_INDICATORS: frozenset[int] = frozenset({
    4789,
    4793,
    4795,
})

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
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "CHL", 2023)] = (
        TemporalAvailabilityStatus.PERIOD_UNOBSERVED,
        2022,
        2024,
    )
    TEMPORAL_AVAILABILITY_MATRIX[(_badehog_id, "CHL", 2024)] = (
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
        thesaurus: Thesaurus | None = None,
    ) -> None:
        if store is None and catalog_profile == "full_catalog":
            from unofficial_cepalstat_mcp.catalog.store import CatalogStore
            store = CatalogStore()
        self.store = store
        self.catalog_profile = catalog_profile
        self.ontology = ontology or DEFAULT_FACET_ONTOLOGY
        self.thesaurus = thesaurus or get_default_thesaurus()
        self._dimensions = dimensions or {}
        self._relationships = relationships or {}
        self._temporal_availability = temporal_availability or {}

        self._indicators_cache: dict[int, IndicatorMetadata] = {}
        self._dimensions_cache: dict[int, list[Dimension]] = {}
        self._relationships_cache: dict[int, dict[int, RelationshipType]] = {}
        self._relationship_provenance: dict[tuple[int, int], str] = {}
        self._inverted_index: dict[str, list[tuple[int, float]]] = {}
        self._restricted_country_scope: dict[int, set[str]] = {}
        self._synonym_stem_map: dict[str, list[str]] = {}
        self._title_word_counts: dict[int, int] = {}
        self._headline_indicators: set[int] = set()
        self._order_nums: dict[int, int] = {}
        self._ranking_factors: dict[int, float] = {}

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
                mandatory_filters=v.mandatory_filters,
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
        master_indicators: list[dict[str, Any]] = []
        if self.store is not None:
            # Dimensions overlay: overriding fallback seeds for indicators present in SQLite
            store_dims = self.store.get_all_indicator_dimensions(include_structural=False)
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
            dim_class_cache: dict[tuple[int, str], str | None] = {}
            for ind_id, meta in self._indicators_cache.items():
                dims = self._dimensions_cache.get(ind_id, [])
                for d in dims:
                    dim_key = (d.id, d.name)
                    if dim_key not in dim_class_cache:
                        dim_class_cache[dim_key] = self.ontology.classify_dimension(d.id, d.name)
                    f = dim_class_cache[dim_key]
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

        # 4. Build In-Memory Inverted Index & Restricted Country Scope
        subarea_by_ind = (
            {int(row["indicator_id"]): str(row.get("subarea") or "") for row in master_indicators}
            if master_indicators
            else {}
        )
        area_by_ind = (
            {int(row["indicator_id"]): str(row.get("area") or "") for row in master_indicators}
            if master_indicators
            else {}
        )
        area_is_cam = {
            ar: ("centroamerica" in ar.lower().translate(_ACCENT_TRANS))
            for ar in set(area_by_ind.values())
            if ar
        }

        order_nums: dict[int, int] = {}
        if master_indicators:
            for row in master_indicators:
                ind_id = int(row["indicator_id"])
                o_num = row.get("order_num")
                if o_num is not None:
                    try:
                        order_nums[ind_id] = int(o_num)
                    except (ValueError, TypeError):
                        pass
        self._order_nums = order_nums

        headline_ids = set(OFFICIAL_25_CANONICAL_DEFAULTS.values()) | set(LEGACY_50_CANONICAL_DEFAULTS.values())
        for ind_id, o_num in self._order_nums.items():
            if o_num <= 20:
                headline_ids.add(ind_id)
        self._headline_indicators = headline_ids

        self._restricted_country_scope = {}
        cleaned_names_by_ind: dict[int, str] = {}
        title_word_counts: dict[int, int] = {}
        for ind_id, meta in self._indicators_cache.items():
            name_clean = meta.name.upper().translate(_ACCENT_TRANS)
            cleaned_names_by_ind[ind_id] = name_clean.lower()
            title_word_counts[ind_id] = len(name_clean.split())
            parts = name_clean.split(None, 2)
            c_code = None
            if parts:
                fw = parts[0].rstrip(":( ")
                c_code = _COUNTRY_PREFIX_MAP.get(fw)
                if not c_code and len(parts) >= 2 and fw in {"COSTA", "EL", "REPUBLICA", "TRINIDAD"}:
                    c_code = _COUNTRY_PREFIX_MAP.get(f"{parts[0]} {parts[1]}".rstrip(":( "))
            if c_code:
                self._restricted_country_scope[ind_id] = {c_code}
                continue

            ar = area_by_ind.get(ind_id, "")
            if area_is_cam.get(ar, False):
                self._restricted_country_scope[ind_id] = {
                    "BLZ", "CRI", "SLV", "GTM", "HND", "NIC", "PAN", "MEX", "CAM"
                }

        self._title_word_counts = title_word_counts

        # Precompute static Tier-2 ranking factors (damping, headline boost, verbose penalty)
        ranking_factors: dict[int, float] = {}
        for ind_id, wc in title_word_counts.items():
            damping = 1.0 / (1.0 + 0.3 * max(0, wc - 6) / 6.0)
            hl_boost = 1.35 if ind_id in self._headline_indicators else 1.0
            o_num = self._order_nums.get(ind_id)
            penalty = 0.85 if (o_num is not None and o_num >= 100 and wc > 15) else 1.0
            ranking_factors[ind_id] = damping * hl_boost * penalty
        self._ranking_factors = ranking_factors

        sub_stems = {
            sub: [
                _stem_spanish(t)
                for t in sub.lower().translate(_ACCENT_TRANS).split()
                if t not in SPANISH_STOPWORDS and not t.isdigit() and len(t) >= 2
            ]
            for sub in set(subarea_by_ind.values())
            if sub
        }
        ar_stems = {
            ar: [
                _stem_spanish(t)
                for t in ar.lower().translate(_ACCENT_TRANS).split()
                if t not in SPANISH_STOPWORDS and not t.isdigit() and len(t) >= 2
            ]
            for ar in set(area_by_ind.values())
            if ar
        }
        mem_stems = {
            m.name: [
                _stem_spanish(t)
                for t in m.name.lower().translate(_ACCENT_TRANS).split()
                if t not in SPANISH_STOPWORDS and not t.isdigit() and len(t) >= 2
            ]
            for dims in self._dimensions_cache.values()
            for d in dims
            for m in d.members
            if m.name
        }

        ind_term_weights: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for ind_id, meta in self._indicators_cache.items():
            # 1. Name stems (weight: 3.0)
            seen_name = set()
            for tok in cleaned_names_by_ind[ind_id].split():
                if tok in SPANISH_STOPWORDS or tok.isdigit() or len(tok) < 2:
                    continue
                seen_name.add(_stem_spanish(tok))
            for st in seen_name:
                ind_term_weights[ind_id][st] += 3.0

            # 2. Subarea stems (weight: 1.8)
            sub = subarea_by_ind.get(ind_id, "")
            for st in sub_stems.get(sub, ()):
                ind_term_weights[ind_id][st] += 1.8

            # 3. Area stems (weight: 1.2)
            ar = area_by_ind.get(ind_id, "")
            for st in ar_stems.get(ar, ()):
                ind_term_weights[ind_id][st] += 1.2

            # 4. Dimension members stems (weight: 1.5)
            dims = self._dimensions_cache.get(ind_id, [])
            for d in dims:
                for m in d.members:
                    for st in mem_stems.get(m.name, ()):
                        ind_term_weights[ind_id][st] += 1.5

        num_docs = len(self._indicators_cache) or 1
        doc_freq: dict[str, int] = defaultdict(int)
        for tws in ind_term_weights.values():
            for st in tws:
                doc_freq[st] += 1

        idf_by_stem = {
            st: math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0) + 1.0
            for st, df in doc_freq.items()
        }
        inv_index: dict[str, list[tuple[int, float]]] = defaultdict(list)
        for ind_id, tws in ind_term_weights.items():
            for st, tw in tws.items():
                inv_index[st].append((ind_id, tw * idf_by_stem[st]))

        self._inverted_index = inv_index

        # Pre-index Thesaurus synonym stems for fast query expansion
        synonym_stems: dict[str, list[str]] = {}
        for synsets in self.thesaurus.synsets.values():
            for s in synsets:
                all_terms = list(s.synonyms) + ([s.canonical_term] if s.canonical_term else [])
                token_stems = set()
                for term in all_terms:
                    for w in term.lower().translate(_ACCENT_TRANS).split():
                        token_stems.add(_stem_spanish(w))
                stem_list = list(token_stems)
                for term in all_terms:
                    for w in term.lower().translate(_ACCENT_TRANS).split():
                        synonym_stems[w] = stem_list
                        synonym_stems[_stem_spanish(w)] = stem_list
        self._synonym_stem_map = synonym_stems

    def search_candidates(
        self,
        concept_tokens: Sequence[str],
        facets: Mapping[str, str] | None = None,
        country_code: str | None = None,
        top_k: int = 10,
    ) -> list[tuple[int, float]]:
        """Search top candidate indicators using IDF-weighted stem coverage + Thesaurus expansion."""
        if not concept_tokens:
            return []

        # 1. Expand query tokens with pre-indexed Thesaurus synonym stems
        query_stems: dict[str, tuple[float, str]] = {}
        for tok in concept_tokens:
            norm_tok = tok.lower().translate(_ACCENT_TRANS).strip()
            if not norm_tok:
                continue
            st = _stem_spanish(norm_tok)
            prev_weight = query_stems.get(st, (0.0, ""))[0]
            query_stems[st] = (max(prev_weight, 1.0), tok)
            for exp_st in self._synonym_stem_map.get(norm_tok, ()):
                if exp_st not in query_stems:
                    query_stems[exp_st] = (0.7, tok)
            for exp_st in self._synonym_stem_map.get(st, ()):
                if exp_st not in query_stems:
                    query_stems[exp_st] = (0.7, tok)

        # 2. Score candidates by accumulating inverted index weights and token coverage
        candidate_scores: dict[int, float] = defaultdict(float)
        matched_concept_tokens: dict[int, set[str]] = defaultdict(set)

        for st, (q_weight, orig_tok) in query_stems.items():
            postings = self._inverted_index.get(st)
            if not postings:
                continue
            for ind_id, idf_weight in postings:
                # Check restricted country scope (Review Focus #3)
                if country_code is not None and ind_id in self._restricted_country_scope:
                    if country_code not in self._restricted_country_scope[ind_id]:
                        continue
                candidate_scores[ind_id] += idf_weight * q_weight
                matched_concept_tokens[ind_id].add(orig_tok)

        if not candidate_scores:
            return []

        # Coordination matching: boost candidates covering multiple distinct concept tokens
        if len(concept_tokens) > 1:
            for ind_id, covered in matched_concept_tokens.items():
                ratio = len(covered) / len(concept_tokens)
                candidate_scores[ind_id] *= (1.0 + 3.0 * ratio)

        # 3. Facet bonus (boost indicators supporting requested facets)
        if facets:
            for ind_id in list(candidate_scores.keys()):
                meta = self._indicators_cache.get(ind_id)
                if meta:
                    for f_key in facets:
                        if f_key in meta.supported_facets:
                            candidate_scores[ind_id] += 2.0

        # 4. Length damping and headline indicator prioritization
        for ind_id in candidate_scores:
            factor = self._ranking_factors.get(ind_id)
            if factor is None:
                wc = self._title_word_counts.get(ind_id, 6)
                damping = 1.0 / (1.0 + 0.3 * max(0, wc - 6) / 6.0)
                hl_boost = 1.35 if ind_id in self._headline_indicators else 1.0
                o_num = self._order_nums.get(ind_id)
                penalty = 0.85 if (o_num is not None and o_num >= 100 and wc > 15) else 1.0
                factor = damping * hl_boost * penalty
                self._ranking_factors[ind_id] = factor
            candidate_scores[ind_id] *= factor

        # 5. Return top_k sorted descending
        return heapq.nlargest(top_k, candidate_scores.items(), key=lambda item: item[1])

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
            self._dimensions_cache[indicator_id] = dims
            return dims
        res = self._dimensions.get(indicator_id, [])
        self._dimensions_cache[indicator_id] = res
        return res

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
        key = (indicator_id, country_code, year)
        if key in self._temporal_availability:
            rec = self._temporal_availability[key]
            if not isinstance(rec[0], TemporalAvailabilityStatus):
                rec = (_normalize_temporal_status(rec[0]), rec[1], rec[2])
                self._temporal_availability[key] = rec
            return rec

        if self.store is not None:
            store_rec = self.store.get_temporal_record(indicator_id, country_code, year)
            if store_rec is not None:
                status_raw, prev_a, next_a = store_rec
                status_enum = _normalize_temporal_status(status_raw)
                cached_rec = (status_enum, prev_a, next_a)
                self._temporal_availability[key] = cached_rec
                return cached_rec

        if key in TEMPORAL_AVAILABILITY_MATRIX:
            res_matrix = TEMPORAL_AVAILABILITY_MATRIX[key]
            self._temporal_availability[key] = res_matrix
            return res_matrix

        if indicator_id in QUINQUENNIAL_DEMOGRAPHIC_INDICATORS:
            res_quinquennial: tuple[TemporalAvailabilityStatus, int | None, int | None]
            if 1950 <= year <= 2100:
                if year % 5 == 0:
                    res_quinquennial = (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None)
                else:
                    prev_anchor = year - (year % 5)
                    calc_next = prev_anchor + 5
                    next_anchor: int | None = calc_next if calc_next <= 2100 else None
                    res_quinquennial = (TemporalAvailabilityStatus.PERIOD_UNOBSERVED, prev_anchor, next_anchor)
            else:
                res_quinquennial = (TemporalAvailabilityStatus.OBSERVATION_MISSING, None, None)
            self._temporal_availability[key] = res_quinquennial
            return res_quinquennial

        # CELADE continuous annual demographic estimates and projections (1950-2100)
        if indicator_id in (4784, 4788) and 1950 <= year <= 2100:
            fallback = (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None)
            self._temporal_availability[key] = fallback
            return fallback

        # Default: if between 1950 and current UTC year, assume existing
        current_year = datetime.now(timezone.utc).year
        if 1950 <= year <= current_year:
            fallback = (TemporalAvailabilityStatus.OBSERVATION_EXISTING, None, None)
        else:
            fallback = (TemporalAvailabilityStatus.OBSERVATION_MISSING, None, None)
        self._temporal_availability[key] = fallback
        return fallback
