from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.dimensions import Dimension, Member


def _seeded_store(tmp_path) -> CatalogStore:
    store = CatalogStore(db_path=tmp_path / "fts.db")
    with store._get_connection() as conn:
        rows = [
            (2656, "Tiempo de Trabajo no Remunerado según ingresos propios y pobreza", 0, "Género", "Género", "", "Género > Uso del tiempo", "2026-10-30"),
            (3328, "Población en situación de pobreza extrema y pobreza, por área", 40, "Sociales", "Sociales", "Pobreza", "Sociales > Pobreza", "2026-10-30"),
            (127, "Tasa de desocupación por sexo", 20, "Sociales", "Sociales", "Empleo", "Sociales > Empleo", "2026-10-30"),
            (1912, "Exportaciones totales de bienes FOB", 10, "Económicos", "Comercio Internacional y Balanza de Pagos", "", "Económicos > Comercio", "2026-10-30"),
            (821, "Ingresos tributarios por tipo de impuestos en porcentajes del PIB", 10, "Económicos", "Sector público", "", "Económicos > Fiscal", "2026-10-30"),
        ]
        conn.executemany("INSERT INTO master_indicators VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    store.store_indicator_dimensions(
        127, [Dimension(id=144, name="Sexo__ESTANDAR", members=[Member(id=266, name="Mujeres"), Member(id=265, name="Hombres")])]
    )
    store.store_indicator_dimensions(
        821, [Dimension(id=900, name="Tipo de impuesto", members=[Member(id=901, name="Impuesto al valor agregado (IVA)")])]
    )
    store.rebuild_fts_index()
    return store


def test_fts5_finds_non_adjacent_tokens_and_dimension_members(tmp_path) -> None:
    store = _seeded_store(tmp_path)
    assert [r.indicator_id for r in store.search("exportaciones bienes")][:1] == [1912]
    assert [r.indicator_id for r in store.search("desocupación mujeres")][:1] == [127]
    assert [r.indicator_id for r in store.search("recaudación IVA")][:1] == [821] or 821 in [r.indicator_id for r in store.search("impuestos IVA")]


def test_fts5_expands_synonyms_and_ranks_core_poverty_above_peripheral_order_zero(tmp_path) -> None:
    store = _seeded_store(tmp_path)
    assert 127 in [r.indicator_id for r in store.search("desempleo")]
    results = store.search("pobreza", limit=5)
    assert results[0].indicator_id == 3328


def test_fts5_sanitizes_punctuation_and_operators_without_operational_error(tmp_path) -> None:
    store = _seeded_store(tmp_path)
    for hostile in ["PIB (USD) 2020-2024", "pobreza %", "I+D", "Q5/Q1", "O'Higgins", '"" OR NOT *']:
        res = store.search(hostile)
        assert isinstance(res, list)
