import statistics
import time
from pathlib import Path

import pytest

from unofficial_cepalstat_mcp.catalog.models import CatalogCandidate
from unofficial_cepalstat_mcp.catalog.seed import ensure_seed_hydrated
from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.config import get_cache_db_path
from unofficial_cepalstat_mcp.dimensions import Dimension, Member
from unofficial_cepalstat_mcp.semantic.thesaurus import get_default_thesaurus


def _seeded_store(tmp_path: Path) -> CatalogStore:
    store = CatalogStore(db_path=tmp_path / "fts.db")
    with store._get_connection() as conn:
        rows = [
            (2656, "Tiempo de Trabajo no Remunerado según ingresos propios y pobreza", 0, "Género", "Género", "", "Género > Uso del tiempo", "2026-10-30"),
            (3328, "Población en situación de pobreza extrema y pobreza, por área", 40, "Sociales", "Sociales", "Pobreza", "Sociales > Pobreza", "2026-10-30"),
            (127, "Tasa de desocupación por sexo", 20, "Sociales", "Sociales", "Empleo", "Sociales > Empleo", "2026-10-30"),
            (1912, "Exportaciones totales de bienes FOB", 10, "Económicos", "Comercio Internacional y Balanza de Pagos", "", "Económicos > Comercio", "2026-10-30"),
            (2050, "Balanza de pagos", 1001, "Económicos", "Comercio Internacional y Balanza de Pagos", "Balanza de pagos", "Económicos > Balanza", "2026-10-30"),
            (821, "Ingresos tributarios por tipo de impuestos en porcentajes del PIB", 10, "Económicos", "Sector público", "", "Económicos > Fiscal", "2026-10-30"),
        ]
        conn.executemany("INSERT INTO master_indicators VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    store.store_indicator_dimensions(
        127, [Dimension(id=144, name="Sexo__ESTANDAR", members=[Member(id=266, name="Mujeres"), Member(id=265, name="Hombres")])]
    )
    store.store_indicator_dimensions(
        821, [Dimension(id=900, name="Tipo de impuesto", members=[Member(id=901, name="Impuesto al valor agregado (IVA)")])]
    )
    store.store_indicator_dimensions(
        2050, [Dimension(id=20501, name="Rubro", members=[Member(id=20502, name="Balanza de bienes")])]
    )
    store.rebuild_fts_index()
    return store


@pytest.fixture(scope="module")
def benchmark_db() -> Path:
    db_path = get_cache_db_path()
    ensure_seed_hydrated(db_path=db_path)
    return db_path


def test_fts5_finds_non_adjacent_tokens_and_dimension_members(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    assert [r.indicator_id for r in store.search("exportaciones bienes")][:1] == [1912]
    assert [r.indicator_id for r in store.search("desocupación mujeres")][:1] == [127]
    assert [r.indicator_id for r in store.search("recaudación IVA")][:1] == [821] or 821 in [r.indicator_id for r in store.search("impuestos IVA")]


def test_fts5_expands_synonyms_and_ranks_core_poverty_above_peripheral_order_zero(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    assert 127 in [r.indicator_id for r in store.search("desempleo")]
    results = store.search("pobreza", limit=5)
    assert results[0].indicator_id == 3328


def test_fts5_sanitizes_punctuation_and_operators_without_operational_error(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    for hostile in ["PIB (USD) 2020-2024", "pobreza %", "I+D", "Q5/Q1", "O'Higgins", '"" OR NOT *']:
        res = store.search(hostile)
        assert isinstance(res, list)


def test_thesaurus_expand_query_tokens() -> None:
    thesaurus = get_default_thesaurus()
    expanded_trade = thesaurus.expand_query_tokens(["balanza", "bienes"])
    assert any("fob" in term or "exportaciones" in term for term in expanded_trade)

    expanded_labor = thesaurus.expand_query_tokens(["desempleo"])
    assert any("desocupacion" in term or "paro" in term for term in expanded_labor)


def test_search_indicators_fts5_expands_synonyms_and_returns_candidates(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    candidates = store.search_indicators_fts5("balanza de bienes", limit=10)
    assert len(candidates) >= 2
    top_ids = [c.indicator_id for c in candidates]
    assert 2050 in top_ids
    assert 1912 in top_ids
    assert top_ids[0] == 2050

    top_cand = candidates[0]
    assert isinstance(top_cand, CatalogCandidate)
    assert top_cand.indicator_id == 2050
    assert top_cand.score > 0
    assert len(top_cand.dimensions) > 0
    assert top_cand.dimensions[0].name == "Rubro"


def test_search_indicators_fts5_sanitizes_punctuation_and_operators(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    hostiles = [
        "PIB (USD) 2020-2024",
        "pobreza %",
        "I+D",
        "Q5/Q1",
        "O'Higgins",
        '"" OR NOT *',
        "   ",
        "AND OR NOT",
        "()",
        "***",
        "???",
        "\"unclosed quote",
    ]
    for hostile in hostiles:
        res = store.search_indicators_fts5(hostile)
        assert isinstance(res, list)


def test_search_indicators_fts5_ranks_core_concepts_over_peripheral(tmp_path: Path) -> None:
    store = _seeded_store(tmp_path)
    results = store.search_indicators_fts5("pobreza", limit=5)
    assert len(results) >= 2
    assert results[0].indicator_id == 3328


def test_fts5_ranking_with_thesaurus_expansion_and_latency(benchmark_db: Path) -> None:
    store = CatalogStore(db_path=benchmark_db)
    # Warmup
    _ = store.search_indicators_fts5("balanza de bienes exportaciones fob", limit=10)

    start = time.perf_counter()
    candidates = store.search_indicators_fts5("balanza de bienes exportaciones fob", limit=10)
    latency_ms = (time.perf_counter() - start) * 1000

    assert len(candidates) > 0
    assert candidates[0].indicator_id == 2050
    assert latency_ms < 0.5  # Sub-millisecond SLA

    # Multi-iteration latency benchmark for p50 < 0.35ms and p95 < 1.8ms
    times: list[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = store.search_indicators_fts5("balanza de bienes exportaciones fob", limit=10)
        times.append((time.perf_counter() - t0) * 1000)

    p50 = statistics.median(times)
    p95 = statistics.quantiles(times, n=20)[18]
    assert p50 < 0.35, f"p50 latency {p50:.3f} ms exceeds 0.35 ms SLA"
    assert p95 < 1.8, f"p95 latency {p95:.3f} ms exceeds 1.8 ms SLA"
