"""Tests for CatalogHarvester and CatalogStore harvest extensions."""

import sqlite3
from datetime import datetime
import pytest

from statscepal.catalog.store import CatalogStore
from statscepal.dimensions import Dimension, Member


def test_store_harvest_columns_and_status(tmp_path):
    db_path = tmp_path / "test_catalog.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    # Initially empty
    assert store.get_harvested_indicator_ids() == set()
    stats = store.get_harvest_stats()
    assert stats["harvested_indicators"] == 0
    assert stats["total_dimensions"] == 0
    assert stats["total_members"] == 0

    # Store with content hash and explicit harvested_at
    dims = [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=224, name="Total nacional"), Member(id=225, name="Urbana")],
        )
    ]
    store.store_indicator_dimensions(
        indicator_id=3328,
        dimensions=dims,
        content_hash="abc123hash",
        harvested_at="2026-10-16T16:00:00Z",
    )

    assert 3328 in store.get_harvested_indicator_ids()
    updated_stats = store.get_harvest_stats()
    assert updated_stats["harvested_indicators"] == 1
    assert updated_stats["total_dimensions"] == 1
    assert updated_stats["total_members"] == 2

    # Verify column values in DB
    with store._get_connection() as conn:
        row = conn.execute(
            "SELECT harvested_at, content_hash FROM indicator_dimensions WHERE indicator_id = 3328"
        ).fetchone()
        assert row["harvested_at"] == "2026-10-16T16:00:00Z"
        assert row["content_hash"] == "abc123hash"


def test_store_harvest_columns_default_timestamp(tmp_path):
    db_path = tmp_path / "test_catalog_default_time.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    dims = [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=224, name="Total nacional")],
        )
    ]
    store.store_indicator_dimensions(
        indicator_id=3342,
        dimensions=dims,
    )

    assert 3342 in store.get_harvested_indicator_ids()
    with store._get_connection() as conn:
        row = conn.execute(
            "SELECT harvested_at, content_hash FROM indicator_dimensions WHERE indicator_id = 3342"
        ).fetchone()
        assert row["harvested_at"] is not None
        # Must parse as ISO timestamp
        dt = datetime.fromisoformat(row["harvested_at"])
        assert dt is not None
        assert row["content_hash"] is None


def test_schema_migration_adds_columns_to_existing_table(tmp_path):
    db_path = tmp_path / "legacy_catalog.db"
    conn = sqlite3.connect(db_path)
    # Create legacy table without harvested_at and content_hash
    conn.execute("""
        CREATE TABLE indicator_dimensions (
            indicator_id INTEGER,
            dim_id INTEGER,
            dim_name TEXT,
            pos INTEGER,
            PRIMARY KEY (indicator_id, dim_id)
        )
    """)
    conn.commit()
    conn.close()

    store = CatalogStore(db_path=db_path)
    # Should perform schema migration non-destructively
    store.init_semantic_tables()

    with store._get_connection() as c:
        cur = c.execute("PRAGMA table_info(indicator_dimensions)")
        col_names = {row["name"] for row in cur.fetchall()}
        assert "harvested_at" in col_names
        assert "content_hash" in col_names
