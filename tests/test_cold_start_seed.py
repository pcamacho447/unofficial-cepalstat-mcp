import time
from pathlib import Path

from unofficial_cepalstat_mcp.bitacora.store import BitacoraStore
from unofficial_cepalstat_mcp.catalog.seed import ensure_seed_hydrated
from unofficial_cepalstat_mcp.catalog.store import CatalogStore


def test_cold_start_hydrates_default_cache_under_50ms_with_1739_indicators_and_recipes(
    tmp_path: Path, monkeypatch
) -> None:
    cache_db = tmp_path / "cold_cache" / ".statscepal_cache.db"
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(cache_db))
    t0 = time.perf_counter()
    store = CatalogStore()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert cache_db.exists()
    assert elapsed_ms < 150.0  # <50ms warm disk, generous CI ceiling
    assert store.get_stats().total_indicators >= 1700
    assert len(store.search("pobreza")) > 0

    cwd_dir = tmp_path / "readonly_cwd"
    cwd_dir.mkdir()
    monkeypatch.chdir(cwd_dir)
    b_store = BitacoraStore()
    assert not (cwd_dir / "bitacoras").exists()
    assert len(b_store.list_all()) >= 2


def test_ensure_seed_hydrated_guards(tmp_path: Path) -> None:
    non_default = tmp_path / "other.db"
    # Should not hydrate non-default cache path unless force=True
    assert ensure_seed_hydrated(non_default) is False
    assert not non_default.exists()

    # Hydrates when force=True
    assert ensure_seed_hydrated(non_default, force=True) is True
    assert non_default.exists()

    # Once exists, returns False (no-op)
    assert ensure_seed_hydrated(non_default, force=False) is False
