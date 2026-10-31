"""Cold-start packaged seed snapshot and atomic hydration utilities."""

import gzip
import importlib.resources
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from unofficial_cepalstat_mcp.bitacora.store import BitacoraStore
from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.config import get_cache_db_path
from unofficial_cepalstat_mcp.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY
from unofficial_cepalstat_mcp.semantic.graph_builder import GraphBuilder


def export_seed_snapshot(
    source_db: Path | str | None = None,
    output_gz: Path | str | None = None,
    recipes_dir: Path | str | None = None,
) -> Path:
    """Generate a clean, compressed SQLite seed snapshot containing indicators and recipes.

    Prunes structural dimension members (Country/Year) to optimize compressed size,
    seeds curated vertical-slice indicators, infers breakdown graph relationships,
    indexes recipes from disk, rebuilds FTS5, runs VACUUM, and outputs a deterministic
    gzip archive (mtime=0).

    Args:
        source_db: Optional path to source SQLite cache database.
        output_gz: Optional output path for the compressed seed (.db.gz).
        recipes_dir: Optional path to the directory containing certified recipe markdown files.

    Returns:
        Path to the generated .db.gz archive.
    """
    src_path = Path(source_db) if source_db is not None else get_cache_db_path()
    recipes_path = Path(recipes_dir) if recipes_dir is not None else Path("bitacoras")

    if output_gz is not None:
        out_path = Path(output_gz)
    else:
        pkg_root = Path(__file__).resolve().parent.parent
        out_path = pkg_root / "data" / "seed_catalog.db.gz"

    with tempfile.TemporaryDirectory() as tmp_dir:
        stage_db = Path(tmp_dir) / "stage_seed.db"
        stage_store = CatalogStore(db_path=stage_db, auto_seed=False)
        stage_store.init_semantic_tables()

        # Copy tables from source if source exists and has rows
        has_source_indicators = False
        if src_path.exists():
            try:
                conn_src = sqlite3.connect(src_path, timeout=10.0)
                conn_src.execute("PRAGMA busy_timeout = 10000;")
                try:
                    c = conn_src.cursor()
                    c.execute("SELECT COUNT(*) FROM master_indicators")
                    cnt = c.fetchone()[0]
                    has_source_indicators = cnt > 0
                finally:
                    conn_src.close()
            except Exception:
                has_source_indicators = False

            if has_source_indicators:
                with stage_store._get_connection() as conn:
                    conn.execute("ATTACH DATABASE ? AS src", (str(src_path),))
                    tables_to_copy = [
                        "master_indicators",
                        "indicator_metadata",
                        "indicator_dimensions",
                        "dimension_members",
                        "indicator_relationships",
                        "temporal_availability",
                    ]
                    for tbl in tables_to_copy:
                        try:
                            conn.execute(f"INSERT OR REPLACE INTO {tbl} SELECT * FROM src.{tbl}")
                        except sqlite3.OperationalError:
                            pass
                    conn.execute("DETACH DATABASE src")

        if not has_source_indicators:
            stage_store.build(force=True)

        # Seed curated metadata, relationships, and dimensions
        stage_store.populate_official_indicators()

        # Infer and persist BREAKDOWN_OF relationships
        builder = GraphBuilder(store=stage_store)
        builder.build_breakdown_graph(persist=True)

        # Sync recipes from disk if directory exists
        if recipes_path.exists():
            b_store = BitacoraStore(base_dir=recipes_path, db_path=stage_db)
            b_store.sync()

        # Prune structural dimension members to maintain a compact footprint
        with stage_store._get_connection() as conn:
            cursor = conn.execute("SELECT DISTINCT dim_id, dim_name FROM indicator_dimensions")
            structural_dim_ids = set()
            for row in cursor.fetchall():
                dim_id = row["dim_id"]
                dim_name = row["dim_name"]
                if DEFAULT_FACET_ONTOLOGY.is_structural_dimension(dim_id, dim_name):
                    structural_dim_ids.add(dim_id)
            if structural_dim_ids:
                placeholders = ",".join("?" for _ in structural_dim_ids)
                conn.execute(
                    f"DELETE FROM dimension_members WHERE dim_id IN ({placeholders})",
                    tuple(structural_dim_ids),
                )
            conn.execute("VACUUM;")

        # Rebuild full-text search index
        stage_store.rebuild_fts_index()

        with stage_store._get_connection() as conn:
            conn.execute("VACUUM;")

        # Deterministic gzip compression (mtime=0)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_gz = out_path.with_suffix(f".tmp.{os.getpid()}.gz")
        try:
            with open(stage_db, "rb") as f_in, open(tmp_gz, "wb") as f_raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=f_raw, mtime=0) as gz_out:
                    shutil.copyfileobj(f_in, gz_out)
            os.replace(tmp_gz, out_path)
        except Exception:
            if tmp_gz.exists():
                try:
                    tmp_gz.unlink()
                except OSError:
                    pass
            raise

    return out_path


def ensure_seed_hydrated(target_db: Path | str, force: bool = False) -> bool:
    """Atomically hydrate SQLite cache database from packaged seed_catalog.db.gz if target does not exist.

    Args:
        target_db: Target path for the SQLite database.
        force: If True, allow hydration even if path differs from get_cache_db_path()
               or already exists.

    Returns:
        True if seed was hydrated, False otherwise.
    """
    target = Path(target_db)
    if target.exists() and not force:
        return False

    default_cache = get_cache_db_path()
    if not force and target.resolve() != default_cache.resolve():
        return False

    try:
        data_pkg = importlib.resources.files("unofficial_cepalstat_mcp.data")
        seed_res = data_pkg.joinpath("seed_catalog.db.gz")
        if not seed_res.is_file():
            return False
    except Exception:
        return False

    if target.parent:
        target.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = Path(f"{target}.{os.getpid()}.tmp")
    try:
        with seed_res.open("rb") as f_in:
            with gzip.open(f_in, "rb") as gz_in:
                with open(tmp_path, "wb") as f_out:
                    shutil.copyfileobj(gz_in, f_out)
        os.replace(tmp_path, target)
        return True
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
