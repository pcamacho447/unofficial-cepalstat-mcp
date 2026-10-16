"""Tests for CatalogHarvester and CatalogStore harvest extensions."""

import json
from pathlib import Path
import sqlite3
from datetime import datetime
import pytest
import respx
import httpx

from statscepal.catalog.harvester import CatalogHarvester
from statscepal.catalog.store import CatalogStore
from statscepal.cli import main
from statscepal.client import CepalStatClient
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


@respx.mock
def test_harvester_resumable_and_retry(tmp_path):
    db_path = tmp_path / "test_catalog_harvester.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    # Pre-populate master_indicators with 2 indicators
    with store._get_connection() as conn:
        conn.execute(
            "INSERT INTO master_indicators (indicator_id, name, theme, area, full_path) VALUES (3328, 'Pobreza', 'Social', 'Pobreza', '/Social/Pobreza')"
        )
        conn.execute(
            "INSERT INTO master_indicators (indicator_id, name, theme, area, full_path) VALUES (3342, 'Pobreza etnica', 'Social', 'Pobreza', '/Social/Pobreza')"
        )

    fixture_3328 = json.loads(Path("tests/fixtures/dimensions/indicator_3328.json").read_text(encoding="utf-8"))
    fixture_3342 = json.loads(Path("tests/fixtures/dimensions/indicator_3342.json").read_text(encoding="utf-8"))

    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/3328/dimensions").respond(
        status_code=200, json=fixture_3328
    )
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/3342/dimensions").respond(
        status_code=200, json=fixture_3342
    )

    client = CepalStatClient()
    harvester = CatalogHarvester(client=client, store=store, rate_limit_delay=0.0)

    # First run: harvests both
    progress_records = []

    def on_progress(idx, total, ind_id, status):
        progress_records.append((idx, total, ind_id, status))

    summary = harvester.harvest(resume=True, on_progress=on_progress)
    assert summary.total_target == 2
    assert summary.already_harvested == 0
    assert summary.newly_harvested == 2
    assert summary.failed_count == 0
    assert len(progress_records) == 2
    assert progress_records[0] == (1, 2, 3328, "success")
    assert progress_records[1] == (2, 2, 3342, "success")

    # Verify content hash and data stored in DB
    dims_3328 = store.get_indicator_dimensions(3328)
    assert len(dims_3328) == 5
    with store._get_connection() as conn:
        row = conn.execute(
            "SELECT content_hash, harvested_at FROM indicator_dimensions WHERE indicator_id = 3328"
        ).fetchone()
        assert row["content_hash"] is not None
        assert row["harvested_at"] is not None

    # Second run with resume=True: skips both
    summary_resume = harvester.harvest(resume=True)
    assert summary_resume.total_target == 2
    assert summary_resume.already_harvested == 2
    assert summary_resume.newly_harvested == 0
    assert summary_resume.failed_count == 0

    # Run with force=True: re-harvests both
    summary_force = harvester.harvest(resume=True, force=True)
    assert summary_force.total_target == 2
    assert summary_force.already_harvested == 0
    assert summary_force.newly_harvested == 2


@respx.mock
def test_harvester_handles_http_errors_and_continues(tmp_path):
    db_path = tmp_path / "test_catalog_err.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    with store._get_connection() as conn:
        conn.execute(
            "INSERT INTO master_indicators (indicator_id, name, theme, area, full_path) VALUES (1001, '404 Indicator', 'Social', 'Pobreza', '/Social/Pobreza')"
        )
        conn.execute(
            "INSERT INTO master_indicators (indicator_id, name, theme, area, full_path) VALUES (3328, 'Success Indicator', 'Social', 'Pobreza', '/Social/Pobreza')"
        )
        conn.execute(
            "INSERT INTO master_indicators (indicator_id, name, theme, area, full_path) VALUES (1002, '500 Indicator', 'Social', 'Pobreza', '/Social/Pobreza')"
        )

    fixture_3328 = json.loads(Path("tests/fixtures/dimensions/indicator_3328.json").read_text(encoding="utf-8"))

    # 1001 returns 404 (non-transient)
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/1001/dimensions").respond(
        status_code=404, text="Not Found"
    )
    # 3328 succeeds
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/3328/dimensions").respond(
        status_code=200, json=fixture_3328
    )
    # 1002 returns 500 (transient, retried then fails)
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/1002/dimensions").respond(
        status_code=500, text="Internal Server Error"
    )

    client = CepalStatClient()
    harvester = CatalogHarvester(client=client, store=store, rate_limit_delay=0.0, max_retries=2, retry_backoff_base=0.01)

    summary = harvester.harvest(resume=False)
    assert summary.total_target == 3
    assert summary.newly_harvested == 1
    assert summary.failed_count == 2
    assert 1001 in summary.failed_ids
    assert 1002 in summary.failed_ids


@respx.mock
def test_harvester_retries_transient_error_and_succeeds(tmp_path):
    db_path = tmp_path / "test_catalog_retry.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    with store._get_connection() as conn:
        conn.execute(
            "INSERT INTO master_indicators (indicator_id, name, theme, area, full_path) VALUES (3328, 'Pobreza', 'Social', 'Pobreza', '/Social/Pobreza')"
        )

    fixture_3328 = json.loads(Path("tests/fixtures/dimensions/indicator_3328.json").read_text(encoding="utf-8"))

    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/3328/dimensions")
    route.side_effect = [
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(200, json=fixture_3328),
    ]

    client = CepalStatClient()
    harvester = CatalogHarvester(client=client, store=store, rate_limit_delay=0.0, max_retries=3, retry_backoff_base=0.01)

    summary = harvester.harvest(resume=False)
    assert summary.total_target == 1
    assert summary.newly_harvested == 1
    assert summary.failed_count == 0
    assert route.call_count == 2


@respx.mock
def test_harvester_explicit_indicator_ids_and_3arg_callback(tmp_path):
    db_path = tmp_path / "test_catalog_explicit.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    fixture_3342 = json.loads(Path("tests/fixtures/dimensions/indicator_3342.json").read_text(encoding="utf-8"))
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/3342/dimensions").respond(
        status_code=200, json=fixture_3342
    )

    client = CepalStatClient()
    harvester = CatalogHarvester(client=client, store=store, rate_limit_delay=0.0)

    # 3-arg callback (idx, total, ind_id)
    callback_calls = []

    def legacy_callback(idx, total, ind_id):
        callback_calls.append((idx, total, ind_id))

    summary = harvester.harvest(indicator_ids=[3342], on_progress=legacy_callback)
    assert summary.total_target == 1
    assert summary.newly_harvested == 1
    assert len(callback_calls) == 1
    assert callback_calls[0] == (1, 1, 3342)

    # Verify members and dimensions in store
    dims = store.get_indicator_dimensions(3342)
    assert len(dims) == 6


@respx.mock
def test_cli_catalog_harvest_success(capsys, tmp_path, monkeypatch):
    db_path = tmp_path / "test_cli_harvest_success.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    with store._get_connection() as conn:
        conn.execute(
            "INSERT INTO master_indicators (indicator_id, name, theme, area, full_path) "
            "VALUES (3328, 'Pobreza', 'Social', 'Pobreza', '/Social/Pobreza')"
        )

    fixture_3328 = json.loads(Path("tests/fixtures/dimensions/indicator_3328.json").read_text(encoding="utf-8"))
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/3328/dimensions").respond(
        status_code=200, json=fixture_3328
    )

    monkeypatch.setattr("statscepal.cli.CatalogStore", lambda: store)

    exit_code = main(["catalog", "harvest", "--rate", "0.0"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "CEPALSTAT Dimension Metadata Harvester" in captured.out
    assert "Target: All catalog indicators" in captured.out
    assert "[Harvesting] (1/1) Indicator ID: 3328 - success" in captured.out
    assert "Catalog Harvest Complete" in captured.out
    assert "Total target:      1" in captured.out
    assert "Already harvested: 0" in captured.out
    assert "Newly harvested:   1" in captured.out
    assert "Failed:            0" in captured.out

    # Verify store content
    assert 3328 in store.get_harvested_indicator_ids()
    dims = store.get_indicator_dimensions(3328)
    assert len(dims) == 5


@respx.mock
def test_cli_catalog_harvest_with_ids_and_force(capsys, tmp_path, monkeypatch):
    db_path = tmp_path / "test_cli_harvest_options.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    with store._get_connection() as conn:
        conn.execute(
            "INSERT INTO master_indicators (indicator_id, name, theme, area, full_path) "
            "VALUES (3328, 'Pobreza', 'Social', 'Pobreza', '/Social/Pobreza')"
        )
        conn.execute(
            "INSERT INTO master_indicators (indicator_id, name, theme, area, full_path) "
            "VALUES (3342, 'Pobreza etnica', 'Social', 'Pobreza', '/Social/Pobreza')"
        )

    fixture_3342 = json.loads(Path("tests/fixtures/dimensions/indicator_3342.json").read_text(encoding="utf-8"))
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/3342/dimensions").respond(
        status_code=200, json=fixture_3342
    )

    monkeypatch.setattr("statscepal.cli.CatalogStore", lambda: store)

    # First run with --ids 3342
    exit_code = main(["catalog", "harvest", "--ids", "3342", "--rate", "0.0"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "Target: 1 indicator(s) [3342]" in captured.out
    assert "Newly harvested:   1" in captured.out
    assert 3342 in store.get_harvested_indicator_ids()

    # Second run without force (resume=True by default) -> already harvested: 1, newly: 0
    exit_code_resume = main(["catalog", "harvest", "--ids", "3342", "--rate", "0.0"])
    assert exit_code_resume == 0
    captured_resume = capsys.readouterr()
    assert "Already harvested: 1" in captured_resume.out
    assert "Newly harvested:   0" in captured_resume.out

    # Third run with --force -> re-harvests 3342
    exit_code_force = main(["catalog", "harvest", "--ids", "3342", "--force", "--rate", "0.0"])
    assert exit_code_force == 0
    captured_force = capsys.readouterr()
    assert "Mode:   Force re-harvest" in captured_force.out
    assert "Newly harvested:   1" in captured_force.out


def test_cli_catalog_harvest_invalid_ids(capsys, monkeypatch, tmp_path):
    store = CatalogStore(db_path=tmp_path / "test_cli_invalid.db")
    monkeypatch.setattr("statscepal.cli.CatalogStore", lambda: store)
    exit_code = main(["catalog", "harvest", "--ids", "not-a-number"])
    assert exit_code == 1



