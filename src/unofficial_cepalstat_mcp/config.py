"""Configuration and path management for unofficial-cepalstat-mcp."""

import os
from pathlib import Path

import platformdirs

APP_NAME = "unofficial_cepalstat_mcp"
DEFAULT_DB_FILENAME = ".statscepal_cache.db"


def get_cache_db_path(ensure_hydrated: bool = False) -> Path:
    """Resolve database path in priority order:

    1. UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH environment variable.
    2. STATSCEPAL_CACHE_PATH environment variable (backward-compat).
    3. Local .statscepal_cache.db in current working directory (if present).
    4. OS user cache directory via platformdirs.

    Args:
        ensure_hydrated: If True, atomically hydrate or auto-repair the database
                         from packaged seed if missing or corrupt.
    """
    env_path = os.environ.get("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH") or os.environ.get("STATSCEPAL_CACHE_PATH")
    if env_path:
        cache_path = Path(env_path)
    elif (local_db := Path(DEFAULT_DB_FILENAME)).exists():
        cache_path = local_db
    else:
        cache_dir = Path(platformdirs.user_cache_dir(APP_NAME))
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / DEFAULT_DB_FILENAME
        except OSError:
            # Fallback to local path if user cache directory is unwritable
            cache_path = local_db

    if ensure_hydrated:
        from unofficial_cepalstat_mcp.catalog.seed import ensure_seed_hydrated

        ensure_seed_hydrated(cache_path, force=False)

    return cache_path
