"""Tests for the 25 official CEPALSTAT indicators and typed relationships in SemanticRegistry and CatalogStore."""

from pathlib import Path

from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.semantic.models import RelationshipType
from unofficial_cepalstat_mcp.semantic.registry import SemanticRegistry

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
    3324: {
        "name": "Distribución del ingreso de las personas, por quintiles y área",
        "measure_type": "DISTRIBUCION_INGRESO",
        "unit": "%",
    },
    127: {
        "name": "Tasa de desocupación por sexo",
        "measure_type": "TASA_DESOCUPACION",
        "unit": "%",
    },
    5097: {
        "name": "Tasa de desempleo, por sexo y edad - 19ª CIET (%)",
        "measure_type": "TASA_DESOCUPACION",
        "unit": "%",
    },
    341: {
        "name": "Salario medio real anual",
        "measure_type": "INDICE_REAL",
        "unit": "índice 2018=100",
    },
    340: {
        "name": "Salario mínimo real",
        "measure_type": "INDICE_REAL",
        "unit": "índice 2018=100",
    },
    2287: {
        "name": "Ingreso medio de la población ocupada, por sexo e inserción laboral",
        "measure_type": "MONTO_MONEDA_LOCAL",
        "unit": "moneda local",
    },
    2198: {
        "name": "Ingresos y gastos de los hogares a precios corrientes en moneda nacional",
        "measure_type": "MONTO_MONEDA_LOCAL",
        "unit": "moneda local",
    },
    2204: {
        "name": "Producto interno bruto (PIB) total anual a precios constantes en dólares",
        "measure_type": "VOLUMEN_REAL",
        "unit": "Millones de USD constantes",
    },
    2206: {
        "name": "Producto interno bruto (PIB) total anual por habitante a precios constantes en dólares",
        "measure_type": "VOLUMEN_REAL_PER_CAPITA",
        "unit": "USD constantes por habitante",
    },
    286: {
        "name": "Producto interno bruto trimestral por tipo del gasto a precios constantes en moneda nacional",
        "measure_type": "VOLUMEN_REAL_TRIMESTRAL",
        "unit": "Millones de moneda nacional",
    },
    2484: {
        "name": "Tasa de crecimiento anual del índice de precios al consumidor: diciembre a diciembre",
        "measure_type": "TASA_VARIACION_INTERANUAL",
        "unit": "%",
    },
    2929: {
        "name": "Tasa de crecimiento anual del índice de precios al consumidor alimentos: diciembre a diciembre",
        "measure_type": "TASA_VARIACION_INTERANUAL",
        "unit": "%",
    },
    365: {
        "name": "Índice de precios al consumidor general",
        "measure_type": "INDICE_PRECIOS",
        "unit": "Índice base",
    },
    1240: {
        "name": "Saldo de la deuda pública del gobierno central en porcentaje del PIB",
        "measure_type": "PORCENTAJE_PIB",
        "unit": "%",
    },
    1246: {
        "name": "Operaciones del gobierno (clasificación económica), en porcentajes del PIB",
        "measure_type": "PORCENTAJE_PIB",
        "unit": "%",
    },
    821: {
        "name": "Ingresos tributarios por tipo de impuestos en porcentajes del PIB",
        "measure_type": "PORCENTAJE_PIB",
        "unit": "%",
    },
    740: {
        "name": "Saldo en cuenta corriente como porcentaje del PIB",
        "measure_type": "PORCENTAJE_PIB",
        "unit": "%",
    },
    883: {
        "name": "Índices de la relación de precios del intercambio y poder de compra de las exportaciones",
        "measure_type": "INDICE_PRECIOS_RELATIVOS",
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
    3154: {
        "name": "Proporción de energía renovable en la oferta de energía primaria",
        "measure_type": "PORCENTAJE_GENERACION",
        "unit": "%",
    },
}

EXPECTED_TYPED_RELATIONSHIPS = [
    (3328, 3341, RelationshipType.BREAKDOWN_OF),
    (3341, 3330, RelationshipType.ALTERNATIVE_MEASURE),
    (3328, 3329, RelationshipType.ALTERNATIVE_MEASURE),
    (341, 2287, RelationshipType.BREAKDOWN_OF),
    (341, 340, RelationshipType.ALTERNATIVE_MEASURE),
    (341, 2198, RelationshipType.ALTERNATIVE_MEASURE),
    (2204, 2206, RelationshipType.BREAKDOWN_OF),
    (2204, 286, RelationshipType.ALTERNATIVE_MEASURE),
    (2484, 2929, RelationshipType.BREAKDOWN_OF),
    (2484, 365, RelationshipType.BREAKDOWN_OF),
    (1240, 1246, RelationshipType.ALTERNATIVE_MEASURE),
    (1240, 821, RelationshipType.ALTERNATIVE_MEASURE),
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

    swaps_salary = registry.get_target_indicators(341, "breakdown_of")
    assert 2287 in swaps_salary

    alts_salary = registry.get_target_indicators(341, "alternative_measure")
    assert 340 in alts_salary
    assert 2198 in alts_salary

    swaps_gdp = registry.get_target_indicators(2204, "breakdown_of")
    assert 2206 in swaps_gdp

    alts_gdp = registry.get_target_indicators(2204, "alternative_measure")
    assert 286 in alts_gdp

    swaps_cpi = registry.get_target_indicators(2484, "breakdown_of")
    assert 2929 in swaps_cpi
    assert 365 in swaps_cpi

    alts_fiscal = registry.get_target_indicators(1240, "alternative_measure")
    assert 1246 in alts_fiscal
    assert 821 in alts_fiscal

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

    store_swaps_341 = store.get_target_indicators(341, "breakdown_of")
    assert 2287 in store_swaps_341

    # Test querying dimensions through store
    dims_3341 = registry.get_dimensions(3341)
    assert len(dims_3341) >= 2
    dim_names = [d.name for d in dims_3341]
    assert any("sexo" in d.lower() for d in dim_names)


def test_registry_contains_ethnic_poverty_indicator_3342():
    from unofficial_cepalstat_mcp.semantic.registry import (
        DEFAULT_OFFICIAL_DIMENSIONS,
        VERTICAL_SLICE_INDICATORS,
        RelationshipType,
    )
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


def test_default_official_dimensions_shared_dim_id_consistency():
    """Assert that whenever a dim_id is shared across indicators, its member IDs do not conflict."""
    from unofficial_cepalstat_mcp.semantic.registry import DEFAULT_OFFICIAL_DIMENSIONS

    dim_registry: dict[int, dict[int, str]] = {}
    for ind_id, dims in DEFAULT_OFFICIAL_DIMENSIONS.items():
        for d in dims:
            dim_id = d.id if hasattr(d, "id") else d["dim_id"]
            if hasattr(d, "members"):
                members_dict = {m.id: m.name for m in d.members}
            elif "members_by_value" in d:
                members_dict = {m_id: m_val for m_val, m_id in d["members_by_value"].items()}
            elif "members" in d:
                members_dict = d["members"]
            else:
                members_dict = {}

            for m_id, m_val in members_dict.items():
                if dim_id in dim_registry and m_id in dim_registry[dim_id]:
                    existing_val = dim_registry[dim_id][m_id]
                    assert existing_val == m_val, (
                        f"Conflict in dim_id={dim_id}: member_id={m_id} mapped to '{existing_val}' "
                        f"in previous indicator, but '{m_val}' in indicator {ind_id}."
                    )
                dim_registry.setdefault(dim_id, {})[m_id] = m_val


def test_vertical_slice_indicators_with_supported_facets_have_default_official_dimensions():
    """Assert all indicators in VERTICAL_SLICE_INDICATORS declaring supported_facets have dimension entries."""
    from unofficial_cepalstat_mcp.semantic.registry import (
        DEFAULT_OFFICIAL_DIMENSIONS,
        VERTICAL_SLICE_INDICATORS,
    )

    missing = []
    for ind_id, info in VERTICAL_SLICE_INDICATORS.items():
        facets = getattr(info, "supported_facets", None) or (info.get("supported_facets") if isinstance(info, dict) else None)
        if facets:
            if ind_id not in DEFAULT_OFFICIAL_DIMENSIONS:
                missing.append(ind_id)
    assert not missing, f"Indicators declare supported_facets but lack DEFAULT_OFFICIAL_DIMENSIONS: {missing}"



