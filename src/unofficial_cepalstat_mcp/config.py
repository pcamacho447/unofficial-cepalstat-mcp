"""Configuration and path management for unofficial-cepalstat-mcp."""

import os
from pathlib import Path

import platformdirs

APP_NAME = "unofficial_cepalstat_mcp"
DEFAULT_DB_FILENAME = ".statscepal_cache.db"


def get_cache_db_path() -> Path:
    """Resolve database path in priority order:

    1. UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH environment variable.
    2. STATSCEPAL_CACHE_PATH environment variable (backward-compat).
    3. Local .statscepal_cache.db in current working directory (if present).
    4. OS user cache directory via platformdirs.
    """
    env_path = os.environ.get("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH") or os.environ.get("STATSCEPAL_CACHE_PATH")
    if env_path:
        return Path(env_path)

    local_db = Path(DEFAULT_DB_FILENAME)
    if local_db.exists():
        return local_db

    cache_dir = Path(platformdirs.user_cache_dir(APP_NAME))
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / DEFAULT_DB_FILENAME
    except OSError:
        # Fallback to local path if user cache directory is unwritable
        return local_db
