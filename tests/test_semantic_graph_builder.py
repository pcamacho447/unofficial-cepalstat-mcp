"""Tests for semantic graph builder and relationship provenance in CatalogStore."""

from pathlib import Path
import sqlite3
from unofficial_cepalstat_mcp.catalog.store import CatalogStore


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


def test_graph_builder_extracts_stems_and_infers_breakdown_from_harvested_dims(tmp_path: Path) -> None:
    import json
    from unofficial_cepalstat_mcp.catalog.harvester import CatalogHarvester
    from unofficial_cepalstat_mcp.semantic.graph_builder import GraphBuilder

    db_path = tmp_path / "graph_infer.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    # Insert 3328 (poverty by area) and 3342 (poverty by sex, ethnicity, area) into master_indicators only
    with store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO master_indicators (indicator_id, name, theme, area, subarea, full_path)
            VALUES
            (3328, 'Población en situación de pobreza extrema y pobreza, por área', 'Sociales', 'Pobreza', '', 'Sociales > Pobreza'),
            (3342, 'Población en situación de pobreza extrema y pobreza, por sexo, autoidentificación étnico-racial y área', 'Sociales', 'Pobreza', '', 'Sociales > Pobreza')
            """
        )

    # Load harvested dimension fixtures into SQLite
    f_3328 = json.loads(Path("tests/fixtures/dimensions/indicator_3328.json").read_text(encoding="utf-8"))
    f_3342 = json.loads(Path("tests/fixtures/dimensions/indicator_3342.json").read_text(encoding="utf-8"))
    store.store_indicator_dimensions(3328, CatalogHarvester._parse_dimensions(f_3328))
    store.store_indicator_dimensions(3342, CatalogHarvester._parse_dimensions(f_3342))

    builder = GraphBuilder(store=store)
    assert (
        builder.extract_name_stem("Población en situación de pobreza extrema y pobreza, por área")
        == "poblacion en situacion de pobreza extrema y pobreza"
    )
    assert (
        builder.extract_name_stem(
            "Población en situación de pobreza extrema y pobreza, por sexo, autoidentificación étnico-racial y área"
        )
        == "poblacion en situacion de pobreza extrema y pobreza"
    )

    # Run inference WITHOUT seeding curated relationships to prove pure algorithmic discovery
    report = builder.build_breakdown_graph(persist=True, seed_curated=False)
    assert report.inferred_edges_count >= 1

    pair_ids = {(e.parent_id, e.child_id) for e in report.inferred_edges}
    assert (3328, 3342) in pair_ids

    # Verify bidirectional inferred edges in SQLite
    rels_3328 = store.get_relationships_with_provenance(3328)
    assert 3342 in rels_3328
    assert rels_3328[3342]["rel_type"] == "breakdown_of"
    assert rels_3328[3342]["provenance"] == "inferred"


def test_graph_builder_zero_false_edges_on_45_curated_indicators(tmp_path: Path) -> None:
    from unofficial_cepalstat_mcp.semantic.graph_builder import GraphBuilder
    from unofficial_cepalstat_mcp.semantic.registry import VERTICAL_SLICE_INDICATORS

    db_path = tmp_path / "graph_45.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.populate_official_indicators()

    builder = GraphBuilder(store=store)
    report = builder.build_breakdown_graph(persist=True, seed_curated=True)

    assert report.false_curated_edges == 0
    for edge in report.inferred_edges:
        if edge.parent_id in VERTICAL_SLICE_INDICATORS and edge.child_id in VERTICAL_SLICE_INDICATORS:
            curated_rels = VERTICAL_SLICE_INDICATORS[edge.parent_id].relationships
            assert edge.child_id in curated_rels


def test_cli_catalog_build_graph_ascii_and_json(tmp_path: Path, capsys, monkeypatch) -> None:
    import json
    from unofficial_cepalstat_mcp.cli import main

    db_path = tmp_path / "cli_catalog.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()
    store.populate_official_indicators()

    monkeypatch.setattr("unofficial_cepalstat_mcp.cli.CatalogStore", lambda *args, **kwargs: CatalogStore(db_path=db_path))

    # 1. ASCII output mode
    exit_code = main(["catalog", "build-graph"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "CEPALSTAT Breakdown Graph Builder" in captured.out
    assert "False curated edges:          0" in captured.out
    assert "Inferred BREAKDOWN_OF pairs:" in captured.out

    # 2. JSON output mode
    exit_code_json = main(["catalog", "build-graph", "--json"])
    assert exit_code_json == 0
    captured_json = capsys.readouterr()
    payload = json.loads(captured_json.out)
    assert payload["false_curated_edges"] == 0
    assert payload["inferred_edges_count"] >= 2
    assert "inferred_edges" in payload


