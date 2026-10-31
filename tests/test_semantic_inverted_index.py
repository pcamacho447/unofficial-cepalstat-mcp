import time

from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.semantic.parser import QueryParser
from unofficial_cepalstat_mcp.semantic.registry import SemanticRegistry


def test_registry_hydrates_1739_indicators_fast_and_indexes_candidates(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(tmp_path / ".statscepal_cache.db"))
    store = CatalogStore()
    t0 = time.perf_counter()
    reg = SemanticRegistry(store=store)
    startup_ms = (time.perf_counter() - t0) * 1000.0
    assert startup_ms < 100.0
    t1 = time.perf_counter()
    hits = reg.search_candidates(["exportaciones", "bienes"], top_k=5)
    query_ms = (time.perf_counter() - t1) * 1000.0
    assert query_ms < 0.5
    assert len(hits) > 0


def test_search_candidates_excludes_chile_only_subnational_tables_for_other_countries(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(tmp_path / ".statscepal_cache.db"))
    reg = SemanticRegistry(store=CatalogStore())
    hits_per = [ind_id for ind_id, _ in reg.search_candidates(["producto", "interno", "bruto", "actividad", "economica"], country_code="PER", top_k=10)]
    assert 4872 not in hits_per  # CHILE subnational GDP


def test_parser_recognizes_latin_america_regional_aggregates() -> None:
    parser = QueryParser()
    intent = parser.parse("exportaciones de bienes en América Latina y el Caribe 2022")
    assert "ALC" in intent.country_codes
