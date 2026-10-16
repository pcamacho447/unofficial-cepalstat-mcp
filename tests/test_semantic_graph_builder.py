"""Tests for semantic graph builder and relationship provenance in CatalogStore."""

from pathlib import Path
import sqlite3
from statscepal.catalog.store import CatalogStore


def test_store_relationship_provenance_and_curated_precedence(tmp_path: Path) -> None:
    db_path = tmp_path / "rel_provenance.db"
    # Simulate legacy table without provenance column
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE indicator_relationships (
            indicator_a INTEGER,
            indicator_b INTEGER,
            rel_type TEXT,
            PRIMARY KEY (indicator_a, indicator_b)
        )
        """
    )
    conn.execute(
        "INSERT INTO indicator_relationships (indicator_a, indicator_b, rel_type) VALUES (3328, 3329, 'alternative_measure')"
    )
    conn.commit()
    conn.close()

    store = CatalogStore(db_path=db_path)
    store.init_semantic_tables()

    # Legacy row should default to 'curated'
    rels_with_prov = store.get_relationships_with_provenance(3328)
    assert 3329 in rels_with_prov
    assert rels_with_prov[3329]["rel_type"] == "alternative_measure"
    assert rels_with_prov[3329]["provenance"] == "curated"

    # Attempting to overwrite a curated edge with an inferred edge must be rejected
    written = store.store_relationship(3328, 3329, "breakdown_of", provenance="inferred")
    assert written is False
    assert store.get_relationships(3328)[3329] == "alternative_measure"

    # Writing a new inferred edge where none exists succeeds
    written_new = store.store_relationship(3328, 3342, "breakdown_of", provenance="inferred")
    assert written_new is True
    rels_updated = store.get_relationships_with_provenance(3328)
    assert rels_updated[3342]["rel_type"] == "breakdown_of"
    assert rels_updated[3342]["provenance"] == "inferred"

    # Curated edge can overwrite an inferred edge
    written_curated = store.store_relationship(3328, 3342, "breakdown_of", provenance="curated")
    assert written_curated is True
    assert store.get_relationships_with_provenance(3328)[3342]["provenance"] == "curated"

    all_inferred = store.get_all_relationships(provenance="inferred")
    assert all_inferred == []
    all_curated = store.get_all_relationships(provenance="curated")
    assert len(all_curated) == 2

    # Unfiltered get_all_relationships
    assert len(store.get_all_relationships()) == 2

    # Test clear_inferred_relationships
    store.store_relationship(3328, 9999, "breakdown_of", provenance="inferred")
    assert len(store.get_all_relationships(provenance="inferred")) == 1
    assert len(store.get_all_relationships()) == 3
    deleted = store.clear_inferred_relationships()
    assert deleted == 1
    assert store.get_all_relationships(provenance="inferred") == []
    assert len(store.get_all_relationships(provenance="curated")) == 2
    assert len(store.get_all_relationships()) == 2


def test_fresh_store_relationship_default_provenance(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.db"
    store = CatalogStore(db_path=db_path)
    store.init_semantic_tables()
    store.store_relationship(101, 102, "breakdown_of")
    rels = store.get_relationships_with_provenance(101)
    assert rels[102]["provenance"] == "curated"
    assert rels[102]["rel_type"] == "breakdown_of"

