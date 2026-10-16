"""Tests for the 25 official CEPALSTAT indicators and typed relationships in SemanticRegistry and CatalogStore."""

from pathlib import Path
import pytest
from statscepal.catalog.store import CatalogStore
from statscepal.semantic.models import RelationshipType
from statscepal.semantic.registry import SemanticRegistry

EXPECTED_25_INDICATORS = {
    3328: {
        "name": "Población en situación de pobreza extrema y pobreza, por área",
        "measure_type": "INCIDENCIA_PORCENTUAL",
        "unit": "%",
    },
    3341: {
        "name": "Tasa de incidencia de la pobreza según sexo y edad",
        "measure_type": "INCIDENCIA_PORCENTUAL",
        "unit": "%",
    },
    3329: {
        "name": "Brecha de pobreza y pobreza extrema",
        "measure_type": "BRECHA_PORCENTUAL",
        "unit": "%",
    },
    3330: {
        "name": "Índice de feminidad de la pobreza",
        "measure_type": "INDICE_FEMINIDAD",
        "unit": "razón",
    },
    3340: {
        "name": "Distribución del ingreso de los hogares por quintiles y deciles",
        "measure_type": "DISTRIBUCION_INGRESO",
        "unit": "%",
    },
    127: {
        "name": "Tasa de desocupación por sexo",
        "measure_type": "TASA_DESOCUPACION",
        "unit": "%",
    },
    3331: {
        "name": "Tasa de desempleo juvenil de 15 a 24 años",
        "measure_type": "TASA_DESOCUPACION",
        "unit": "%",
    },
    128: {
        "name": "Índice del salario medio real",
        "measure_type": "INDICE_REAL",
        "unit": "índice 2018=100",
    },
    3337: {
        "name": "Salario mínimo real",
        "measure_type": "INDICE_REAL",
        "unit": "índice 2018=100",
    },
    3339: {
        "name": "Ingreso laboral medio de la población ocupada por sexo y área",
        "measure_type": "MONTO_MONEDA_LOCAL",
        "unit": "moneda local",
    },
    3345: {
        "name": "Ingreso medio per cápita de los hogares",
        "measure_type": "MONTO_MONEDA_LOCAL",
        "unit": "moneda local",
    },
    729: {
        "name": "Producto interno bruto total anual a precios constantes",
        "measure_type": "MONTO_MONEDA_LOCAL",
        "unit": "millones moneda nacional",
    },
    730: {
        "name": "Producto interno bruto per cápita a precios constantes",
        "measure_type": "USD_PER_CAPITA",
        "unit": "USD",
    },
    731: {
        "name": "Producto interno bruto trimestral a precios constantes",
        "measure_type": "TASA_VARIACION_INTERANUAL",
        "unit": "%",
    },
    2928: {
        "name": "Índice de precios al consumidor (IPC) general",
        "measure_type": "INDICE_PRECIOS",
        "unit": "índice 2018=100",
    },
    2929: {
        "name": "Índice de precios al consumidor de alimentos y bebidas",
        "measure_type": "INDICE_PRECIOS",
        "unit": "índice 2018=100",
    },
    2930: {
        "name": "Índice de precios al consumidor de transporte y energía",
        "measure_type": "INDICE_PRECIOS",
        "unit": "índice 2018=100",
    },
    1240: {
        "name": "Saldo de la deuda pública del gobierno central en porcentaje del PIB",
        "measure_type": "PORCENTAJE_PIB",
        "unit": "%",
    },
    1241: {
        "name": "Balance primario del gobierno central en porcentaje del PIB",
        "measure_type": "PORCENTAJE_PIB",
        "unit": "%",
    },
    1242: {
        "name": "Ingresos tributarios del gobierno central en porcentaje del PIB",
        "measure_type": "PORCENTAJE_PIB",
        "unit": "%",
    },
    1243: {
        "name": "Saldo en cuenta corriente de la balanza de pagos en porcentaje del PIB",
        "measure_type": "PORCENTAJE_PIB",
        "unit": "%",
    },
    1244: {
        "name": "Términos de intercambio de bienes FOB/CIF",
        "measure_type": "INDICE_PRECIOS",
        "unit": "índice 2018=100",
    },
    5681: {
        "name": "Emisiones totales de GEI incluyendo sector UTCUTS / con LULUCF",
        "measure_type": "VOLUMEN_EMISIONES",
        "unit": "Mt CO2 eq",
    },
    5682: {
        "name": "Emisiones totales de GEI excluyendo sector UTCUTS / sin LULUCF",
        "measure_type": "VOLUMEN_EMISIONES",
        "unit": "Mt CO2 eq",
    },
    5683: {
        "name": "Participación de energías renovables en la generación eléctrica",
        "measure_type": "PORCENTAJE_GENERACION",
        "unit": "%",
    },
}

EXPECTED_TYPED_RELATIONSHIPS = [
    (3328, 3341, RelationshipType.BREAKDOWN_OF),
    (3341, 3330, RelationshipType.ALTERNATIVE_MEASURE),
    (3328, 3329, RelationshipType.ALTERNATIVE_MEASURE),
    (128, 3339, RelationshipType.BREAKDOWN_OF),
    (128, 3337, RelationshipType.ALTERNATIVE_MEASURE),
    (128, 3345, RelationshipType.ALTERNATIVE_MEASURE),
    (729, 730, RelationshipType.BREAKDOWN_OF),
    (729, 731, RelationshipType.ALTERNATIVE_MEASURE),
    (2928, 2929, RelationshipType.BREAKDOWN_OF),
    (2928, 2930, RelationshipType.BREAKDOWN_OF),
    (1240, 1241, RelationshipType.ALTERNATIVE_MEASURE),
    (1240, 1242, RelationshipType.ALTERNATIVE_MEASURE),
    (5681, 5682, RelationshipType.ALTERNATIVE_MEASURE),
]


def test_registry_contains_all_25_indicators():
    registry = SemanticRegistry()

    assert len(EXPECTED_25_INDICATORS) == 25
    for ind_id, expected in EXPECTED_25_INDICATORS.items():
        meta = registry.get_indicator(ind_id)
        assert meta is not None, f"Indicator {ind_id} missing from SemanticRegistry"
        assert meta.name == expected["name"]
        assert meta.measure_type == expected["measure_type"]
        assert meta.unit == expected["unit"]


def test_registry_typed_relationships_and_targets():
    registry = SemanticRegistry()

    # Query via get_target_indicators
    swaps_3328 = registry.get_target_indicators(3328, "breakdown_of")
    assert 3341 in swaps_3328

    alts_poverty = registry.get_target_indicators(3341, "alternative_measure")
    assert 3330 in alts_poverty

    alts_3328 = registry.get_target_indicators(3328, "alternative_measure")
    assert 3329 in alts_3328

    swaps_salary = registry.get_target_indicators(128, "breakdown_of")
    assert 3339 in swaps_salary

    alts_salary = registry.get_target_indicators(128, "alternative_measure")
    assert 3337 in alts_salary
    assert 3345 in alts_salary

    swaps_gdp = registry.get_target_indicators(729, "breakdown_of")
    assert 730 in swaps_gdp

    alts_gdp = registry.get_target_indicators(729, "alternative_measure")
    assert 731 in alts_gdp

    swaps_cpi = registry.get_target_indicators(2928, "breakdown_of")
    assert 2929 in swaps_cpi
    assert 2930 in swaps_cpi

    alts_fiscal = registry.get_target_indicators(1240, "alternative_measure")
    assert 1241 in alts_fiscal
    assert 1242 in alts_fiscal

    alts_env = registry.get_target_indicators(5681, "alternative_measure")
    assert 5682 in alts_env

    # Check each pair via check_relationship
    for ind_a, ind_b, expected_rel in EXPECTED_TYPED_RELATIONSHIPS:
        rel = registry.check_relationship(ind_a, ind_b)
        assert rel == expected_rel, f"Relationship {ind_a} -> {ind_b} expected {expected_rel}, got {rel}"

    # Check via get_relationships
    rels_3328 = registry.get_relationships(3328)
    assert rels_3328.get(3341) == RelationshipType.BREAKDOWN_OF
    assert rels_3328.get(3329) == RelationshipType.ALTERNATIVE_MEASURE


def test_catalog_store_persists_25_indicators_and_relationships(tmp_path: Path):
    db_path = tmp_path / "test_catalog_25.db"
    store = CatalogStore(db_path=db_path)
    store.populate_official_indicators()

    registry = SemanticRegistry(store=store)

    for ind_id, expected in EXPECTED_25_INDICATORS.items():
        meta = registry.get_indicator(ind_id)
        assert meta is not None, f"Indicator {ind_id} missing in store-backed registry"
        assert meta.name == expected["name"]
        assert meta.measure_type == expected["measure_type"]

    # Test relationships stored in SQLite
    store_rels_3328 = store.get_relationships(3328)
    assert store_rels_3328.get(3341) == "breakdown_of"
    assert store_rels_3328.get(3329) == "alternative_measure"

    store_swaps_128 = store.get_target_indicators(128, "breakdown_of")
    assert 3339 in store_swaps_128

    # Test querying dimensions through store
    dims_3341 = registry.get_dimensions(3341)
    assert len(dims_3341) >= 2
    dim_names = [d.name for d in dims_3341]
    assert any("sexo" in d.lower() for d in dim_names)


def test_registry_contains_ethnic_poverty_indicator_3342():
    from statscepal.semantic.registry import VERTICAL_SLICE_INDICATORS, DEFAULT_OFFICIAL_DIMENSIONS, RelationshipType
    assert 3342 in VERTICAL_SLICE_INDICATORS
    ind_3342 = VERTICAL_SLICE_INDICATORS[3342]
    assert ind_3342.concept == "POBREZA"
    assert "etnia" in ind_3342.supported_facets
    assert "area" in ind_3342.supported_facets
    assert 3328 in ind_3342.relationships
    assert ind_3342.relationships[3328] == RelationshipType.BREAKDOWN_OF

    # Check canonical 3328 points to 3342 as BREAKDOWN_OF
    ind_3328 = VERTICAL_SLICE_INDICATORS[3328]
    assert 3342 in ind_3328.relationships
    assert ind_3328.relationships[3342] == RelationshipType.BREAKDOWN_OF

    # Check official dimensions for 3342
    assert 3342 in DEFAULT_OFFICIAL_DIMENSIONS
    dims = DEFAULT_OFFICIAL_DIMENSIONS[3342]
    dim_names = [d.name for d in dims]
    assert any("etnia" in d.lower() for d in dim_names)

