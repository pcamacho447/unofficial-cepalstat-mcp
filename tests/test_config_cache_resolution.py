"""Tests for multi-platform cache resolution hierarchy and environment path overrides."""

from pathlib import Path
from unittest.mock import patch

from unofficial_cepalstat_mcp.bitacora.store import BitacoraStore
from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.config import (
    DEFAULT_DB_FILENAME,
    get_cache_db_path,
)


def test_cache_db_path_respects_env_var(monkeypatch, tmp_path):
    """Priority 1: UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH takes top precedence."""
    custom_db = tmp_path / "custom_mcp_cache.db"
    legacy_db = tmp_path / "legacy_cache.db"
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(custom_db))
    monkeypatch.setenv("STATSCEPAL_CACHE_PATH", str(legacy_db))

    resolved = get_cache_db_path()
    assert resolved == custom_db


def test_cache_db_path_respects_legacy_env_var(monkeypatch, tmp_path):
    """Priority 2: STATSCEPAL_CACHE_PATH applies if primary env var is not set."""
    custom_db = tmp_path / "legacy.db"
    monkeypatch.delenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", raising=False)
    monkeypatch.setenv("STATSCEPAL_CACHE_PATH", str(custom_db))

    resolved = get_cache_db_path()
    assert resolved == custom_db


def test_cache_db_path_falls_back_to_local_if_exists(monkeypatch, tmp_path):
    """Priority 3: Local .statscepal_cache.db in CWD if present and no env vars."""
    monkeypatch.delenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", raising=False)
    monkeypatch.delenv("STATSCEPAL_CACHE_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    local_db = tmp_path / DEFAULT_DB_FILENAME
    local_db.touch()

    resolved = get_cache_db_path()
    assert resolved == Path(DEFAULT_DB_FILENAME)
    assert resolved.exists()


def test_cache_db_path_platformdirs_fallback(monkeypatch, tmp_path):
    """Priority 4: OS user cache directory via platformdirs when no env vars and no local DB."""
    monkeypatch.delenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", raising=False)
    monkeypatch.delenv("STATSCEPAL_CACHE_PATH", raising=False)
    monkeypatch.chdir(tmp_path)  # empty directory, no local .statscepal_cache.db

    fake_cache_dir = tmp_path / "platform_cache"
    monkeypatch.setattr(
        "unofficial_cepalstat_mcp.config.platformdirs.user_cache_dir",
        lambda app_name: str(fake_cache_dir),
    )

    resolved = get_cache_db_path()
    expected = fake_cache_dir / DEFAULT_DB_FILENAME
    assert resolved == expected
    assert fake_cache_dir.is_dir()


def test_cache_db_path_unwritable_cache_dir_fallback(monkeypatch, tmp_path):
    """Fallback to local path if user cache directory creation raises OSError."""
    monkeypatch.delenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", raising=False)
    monkeypatch.delenv("STATSCEPAL_CACHE_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    fake_cache_dir = tmp_path / "non_writable_cache"
    monkeypatch.setattr(
        "unofficial_cepalstat_mcp.config.platformdirs.user_cache_dir",
        lambda app_name: str(fake_cache_dir),
    )

    with patch.object(Path, "mkdir", side_effect=PermissionError("Permission denied")):
        resolved = get_cache_db_path()
        assert resolved == Path(DEFAULT_DB_FILENAME)


def test_catalog_store_default_path_resolution(monkeypatch, tmp_path):
    """CatalogStore resolves db_path from get_cache_db_path() when db_path is None or omitted."""
    custom_db = tmp_path / "catalog_store_test.db"
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(custom_db))

    store = CatalogStore()
    assert store.db_path == custom_db

    store_none = CatalogStore(db_path=None)
    assert store_none.db_path == custom_db

    explicit_db = tmp_path / "explicit.db"
    store_explicit = CatalogStore(db_path=explicit_db)
    assert store_explicit.db_path == explicit_db


def test_bitacora_store_default_path_resolution(monkeypatch, tmp_path):
    """BitacoraStore resolves db_path from get_cache_db_path() when db_path is None or omitted."""
    custom_db = tmp_path / "bitacora_store_test.db"
    bitacoras_dir = tmp_path / "bitacoras"
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(custom_db))

    store = BitacoraStore(base_dir=bitacoras_dir)
    assert store.db_path == custom_db

    store_none = BitacoraStore(base_dir=bitacoras_dir, db_path=None)
    assert store_none.db_path == custom_db

    explicit_db = tmp_path / "explicit_bitacora.db"
    store_explicit = BitacoraStore(base_dir=bitacoras_dir, db_path=explicit_db)
    assert store_explicit.db_path == explicit_db
