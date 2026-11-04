import importlib.resources
import sqlite3
import time
from pathlib import Path

from unofficial_cepalstat_mcp.bitacora.store import BitacoraStore
from unofficial_cepalstat_mcp.catalog.seed import ensure_seed_hydrated
from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.config import get_cache_db_path


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


def test_ensure_seed_hydrated_auto_repairs_corrupted_database(
    tmp_path: Path, monkeypatch
) -> None:
    corrupt_db = tmp_path / ".statscepal_cache.db"
    corrupt_db.write_bytes(b"corrupt header bytes not sqlite3")
    monkeypatch.setattr("unofficial_cepalstat_mcp.config.get_cache_db_path", lambda: corrupt_db)

    hydrated_path = ensure_seed_hydrated(db_path=corrupt_db)
    assert hydrated_path.exists()

    # Must be valid SQLite with >= 1700 indicators (1,739 canonical)
    conn = sqlite3.connect(hydrated_path)
    try:
        check = conn.execute("PRAGMA quick_check;").fetchall()
        assert check == [("ok",)]
        count = conn.execute("SELECT count(*) FROM master_indicators").fetchone()[0]
        assert count == 1739
    finally:
        conn.close()


def test_ensure_seed_hydrated_auto_repairs_truncated_database(
    tmp_path: Path, monkeypatch
) -> None:
    corrupt_db = tmp_path / ".statscepal_cache.db"
    # Valid header prefix but truncated without pages
    corrupt_db.write_bytes(b"SQLite format 3\x00" + b"\x00" * 84)
    monkeypatch.setattr("unofficial_cepalstat_mcp.config.get_cache_db_path", lambda: corrupt_db)

    assert ensure_seed_hydrated(corrupt_db) is True
    assert corrupt_db.exists()

    conn = sqlite3.connect(corrupt_db)
    try:
        check = conn.execute("PRAGMA quick_check;").fetchall()
        assert check == [("ok",)]
        count = conn.execute("SELECT count(*) FROM master_indicators").fetchone()[0]
        assert count == 1739
    finally:
        conn.close()


def test_ensure_seed_hydrated_cold_start_latency_under_50ms(
    tmp_path: Path, monkeypatch
) -> None:
    target_db = tmp_path / "latency_check.db"
    monkeypatch.setattr("unofficial_cepalstat_mcp.config.get_cache_db_path", lambda: target_db)

    t0 = time.perf_counter()
    hydrated = ensure_seed_hydrated(target_db)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert hydrated is True
    assert target_db.exists()
    assert elapsed_ms < 50.0


def test_seed_catalog_package_size_under_3mb() -> None:
    data_pkg = importlib.resources.files("unofficial_cepalstat_mcp.data")
    seed_res = data_pkg.joinpath("seed_catalog.db.gz")
    assert seed_res.is_file()
    size_bytes = seed_res.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    assert size_mb < 3.0


def test_get_cache_db_path_with_ensure_hydrated(tmp_path: Path, monkeypatch) -> None:
    target_db = tmp_path / "cache_dir" / ".statscepal_cache.db"
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(target_db))

    assert not target_db.exists()
    resolved = get_cache_db_path(ensure_hydrated=True)
    assert resolved == target_db
    assert target_db.exists()

    # Corrupt it and verify get_cache_db_path(ensure_hydrated=True) auto-repairs
    target_db.write_bytes(b"corrupted contents")
    resolved_repaired = get_cache_db_path(ensure_hydrated=True)
    assert resolved_repaired == target_db

    conn = sqlite3.connect(target_db)
    try:
        check = conn.execute("PRAGMA quick_check;").fetchall()
        assert check == [("ok",)]
        count = conn.execute("SELECT count(*) FROM master_indicators").fetchone()[0]
        assert count == 1739
    finally:
        conn.close()


def test_get_cache_db_path_ensure_hydrated_is_idempotent_and_preserves_data(
    tmp_path: Path, monkeypatch
) -> None:
    target_db = tmp_path / "idempotent_cache" / ".statscepal_cache.db"
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(target_db))

    # 1. Hydrate database initially
    resolved = get_cache_db_path(ensure_hydrated=True)
    assert resolved == target_db
    assert target_db.exists()

    # 2. Insert custom data / staging table into the healthy database
    conn = sqlite3.connect(target_db)
    try:
        conn.execute("CREATE TABLE staging_indicators_custom (id INTEGER PRIMARY KEY, note TEXT);")
        conn.execute("INSERT INTO staging_indicators_custom (id, note) VALUES (9999, 'staging preserve');")
        conn.commit()
    finally:
        conn.close()

    # 3. Call get_cache_db_path(ensure_hydrated=True) again
    resolved_again = get_cache_db_path(ensure_hydrated=True)
    assert resolved_again == target_db

    # 4. Verify custom data was NOT wiped or overwritten
    conn = sqlite3.connect(target_db)
    try:
        row = conn.execute("SELECT note FROM staging_indicators_custom WHERE id = 9999;").fetchone()
        assert row is not None
        assert row[0] == "staging preserve"
    finally:
        conn.close()


