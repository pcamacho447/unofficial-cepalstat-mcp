# Task E3: Automatic `BREAKDOWN_OF` Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an algorithmic graph inference engine (`src/statscepal/semantic/graph_builder.py` and CLI `statscepal catalog build-graph`) that automatically derives `BREAKDOWN_OF` relationships across indicator families when child indicators share a concept root and possess a strict superset of dimensions ($\text{facets}(B) \supsetneq \text{facets}(A)$), storing edges in SQLite with `provenance='inferred'` while preserving strict precedence for `provenance='curated'` edges and guaranteeing zero false edges on the 45 reference indicators.

**Architecture:** Extend `indicator_relationships` in `CatalogStore` (`src/statscepal/catalog/store.py`) with a `provenance TEXT DEFAULT 'curated'` column and non-destructive migration, enforcing a persistence invariant that `'inferred'` edges never overwrite `'curated'` edges. Build `GraphBuilder` in `src/statscepal/semantic/graph_builder.py` consuming `CatalogStore` and `FacetOntology` (`E2`) to normalize indicator name stems, classify harvested dimensions into canonical facet sets, infer strict-superset `BREAKDOWN_OF` edges, and emit a `GraphBuildReport`. Expose `statscepal catalog build-graph [--no-persist] [--json]` in `src/statscepal/cli.py`.

**Tech Stack:** Python 3.10+, SQLite3, Pydantic v2, re, pytest.

**Spec:** [docs/superpowers/plans/2026-10-16-epic-metadata-ingestion-generic-facet-routing.md](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-16-epic-metadata-ingestion-generic-facet-routing.md) (Section E3) and [.agents/rules/semantic-resolution-guardrails.md](file:///C:/papx/statscepal/.agents/rules/semantic-resolution-guardrails.md).

## Global Constraints
- Python 3.10+ modern typing syntax (`int | None`, `list[str]`, `dict[str, Any]`).
- All 252+ existing non-integration tests must remain passing without regression.
- False Substitution Rate must strictly equal 0.00% across the 200-question benchmark.
- Top-1 Accuracy across the 200 benchmark test cases must strictly remain 100.0%.
- Zero false edges on the 45 curated reference indicators in `VERTICAL_SLICE_INDICATORS`.
- Local resolution latency over SQLite and in-memory thesaurus must maintain $p50 < 0.5\text{ ms}$.
- Strict offline hermeticity: unit and CLI tests must NEVER perform live network calls.
- Safe UTF-8 console output for Windows CP1252 environments.

---

## File Structure & Responsibilities

| File | Action | Responsibility |
|---|---|---|
| `src/statscepal/catalog/store.py` | Modify | Add `provenance TEXT DEFAULT 'curated'` to `indicator_relationships` with safe migration; enforce curated precedence in `store_relationship()`; add `get_relationships_with_provenance()` and `get_all_relationships()`. |
| `src/statscepal/semantic/graph_builder.py` | Create | Core `GraphBuilder` inference engine, stem normalizer, facet set extractor using `FacetOntology`, strict-superset `BREAKDOWN_OF` inference, curated conflict protection, and `GraphBuildReport` model. |
| `src/statscepal/cli.py` | Modify | Register `statscepal catalog build-graph [--no-persist] [--json]` subcommand and formatted ASCII / JSON diagnostic output. |
| `tests/test_semantic_graph_builder.py` | Create | Unit and integration tests for SQLite relationship provenance, curated precedence, automatic `3328 <-> 3342` / `3328 <-> 3341` inference from harvested dimensions, zero false edges on the 45 curated indicators, and CLI execution. |

---

### Task 1: Relationship Provenance Schema & Curated Precedence in `CatalogStore`

**Files:**
- Modify: `src/statscepal/catalog/store.py:110-120,410-435,520-542`
- Test: `tests/test_semantic_graph_builder.py`

**Interfaces:**
- Consumes: SQLite connection `_get_connection()` in `CatalogStore`.
- Produces:
  - `indicator_relationships` schema with `(indicator_a INTEGER, indicator_b INTEGER, rel_type TEXT, provenance TEXT DEFAULT 'curated', PRIMARY KEY (indicator_a, indicator_b))` and automatic `ALTER TABLE` migration for existing databases.
  - `store.store_relationship(indicator_a: int, indicator_b: int, rel: str, provenance: str = "curated") -> bool`:
    - If `provenance == "inferred"` and a row for `(indicator_a, indicator_b)` already exists with `provenance == "curated"`, does NOT overwrite and returns `False`.
    - Otherwise inserts/replaces the relationship and returns `True`.
  - `store.get_relationships_with_provenance(indicator_a: int) -> dict[int, dict[str, str]]`: returns `{indicator_b: {"rel_type": ..., "provenance": ...}}`.
  - `store.get_all_relationships(provenance: str | None = None) -> list[dict[str, Any]]`: returns list of `{"indicator_a": int, "indicator_b": int, "rel_type": str, "provenance": str}`.

- [ ] **Step 1: Write failing tests for relationship provenance migration and curated precedence**

```python
# In tests/test_semantic_graph_builder.py
import sqlite3
import pytest
from statscepal.catalog.store import CatalogStore


def test_store_relationship_provenance_and_curated_precedence(tmp_path):
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
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_semantic_graph_builder.py -k test_store_relationship_provenance_and_curated_precedence`
Expected: Fails with `AttributeError: 'CatalogStore' object has no attribute 'get_relationships_with_provenance'`.

- [ ] **Step 3: Implement schema migration and provenance methods in `src/statscepal/catalog/store.py`**
- In `init_semantic_tables()`:
  - Include `provenance TEXT DEFAULT 'curated'` in `CREATE TABLE IF NOT EXISTS indicator_relationships`.
  - Inspect `PRAGMA table_info(indicator_relationships)`; if `"provenance"` is not in columns, run `ALTER TABLE indicator_relationships ADD COLUMN provenance TEXT DEFAULT 'curated'` and `UPDATE indicator_relationships SET provenance = 'curated' WHERE provenance IS NULL`.
- Update `store_relationship(self, indicator_a: int, indicator_b: int, rel: str, provenance: str = "curated") -> bool`:
  - Check existing row's `provenance`; if `existing_prov == "curated"` and `provenance == "inferred"`, return `False`.
  - Otherwise execute `INSERT OR REPLACE INTO indicator_relationships (indicator_a, indicator_b, rel_type, provenance) VALUES (?, ?, ?, ?)` and return `True`.
- Add `get_relationships_with_provenance(self, indicator_a: int) -> dict[int, dict[str, str]]` and `get_all_relationships(self, provenance: str | None = None) -> list[dict[str, Any]]`.

- [ ] **Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_semantic_graph_builder.py -k test_store_relationship_provenance_and_curated_precedence`
Expected: 1 passed.

- [ ] **Step 5: Run full non-integration suite**
Run: `uv run pytest -m "not integration"`
Expected: All 253+ tests pass without regression.

- [ ] **Step 6: Commit changes**
```bash
git add src/statscepal/catalog/store.py tests/test_semantic_graph_builder.py
git commit -m "feat(catalog): add provenance tracking and curated precedence to indicator_relationships"
```

---

### Task 2: `GraphBuilder` Algorithmic `BREAKDOWN_OF` Inference Engine

**Files:**
- Create: `src/statscepal/semantic/graph_builder.py`
- Modify: `tests/test_semantic_graph_builder.py`

**Interfaces:**
- Consumes: `CatalogStore`, `DEFAULT_FACET_ONTOLOGY`, `FacetOntology`, `strip_accents`, `VERTICAL_SLICE_INDICATORS`, `RelationshipType`.
- Produces:
  - `InferredEdge(BaseModel)`:
    - `parent_id: int`
    - `child_id: int`
    - `parent_name: str`
    - `child_name: str`
    - `concept_root: str`
    - `parent_facets: list[str]`
    - `child_facets: list[str]`
    - `added_facets: list[str]`
    - `provenance: str = "inferred"`
  - `GraphBuildReport(BaseModel)`:
    - `total_indicators_analyzed: int = 0`
    - `concept_families_count: int = 0`
    - `curated_edges_count: int = 0`
    - `inferred_edges_count: int = 0`
    - `newly_persisted_edges_count: int = 0`
    - `skipped_curated_conflicts: int = 0`
    - `false_curated_edges: int = 0`
    - `inferred_edges: list[InferredEdge] = Field(default_factory=list)`
  - `GraphBuilder`:
    - `__init__(self, store: CatalogStore, ontology: FacetOntology = DEFAULT_FACET_ONTOLOGY)`
    - `extract_name_stem(name: str) -> str`:
      - Normalizes accents and lowercase via `strip_accents`.
      - Strips trailing SDG/CEPAL code suffixes (e.g. `- 19a ciet (%) ...`).
      - Splits before breakdown prepositions: `,?\s+(?:por|segun|desglosad[oa]\s+por)\s+` and returns the base stem.
    - `extract_indicator_facets(self, indicator_id: int, name: str = "") -> set[str]`:
      - Classifies harvested dimensions from `store.get_indicator_dimensions(indicator_id)` via `self.ontology.classify_dimension(d.id, d.name)` (excluding `"__structural__"` and `None`).
      - Unions with stored metadata `supported_facets` if present in `store.get_indicator_metadata(indicator_id)` or `VERTICAL_SLICE_INDICATORS`.
      - Also parses explicit breakdown clauses after `, por ` / ` por ` / `, según ` in `name` against `self.ontology` dimension name patterns so indicators with clear breakdown titles are recognized consistently.
    - `build_breakdown_graph(self, persist: bool = True, seed_curated: bool = True) -> GraphBuildReport`:
      - If `seed_curated` is True, ensures `VERTICAL_SLICE_INDICATORS` metadata and curated relationships are stored with `provenance="curated"`.
      - Collects candidate indicators from `master_indicators`, `indicator_metadata`, and `indicator_dimensions`.
      - Groups indicators into compatible concept families:
        - Indicators share a family key if they share the same normalized name stem (`extract_name_stem(name)` with length $\ge 10$) OR the same curated `(concept, measure_type, unit)`.
        - **Compatibility Guardrail:** If both indicators $A$ and $B$ have explicit metadata (`concept`, `measure_type`, `unit`), they MUST have identical `(concept, measure_type, unit)` to be compared. If their `concept`, `measure_type`, or `unit` differ, they are NEVER linked as `BREAKDOWN_OF`.
        - Furthermore, if $A$ and $B$ lack explicit `measure_type`/`unit` metadata, their normalized name stems must match and neither name may introduce a conflicting measure qualifier (e.g. `"por habitante"`, `"per capita"`, `"precios corrientes"` vs `"precios constantes"`, `"en dolares"` vs `"en moneda nacional"`, `"indice de feminidad"`, `"brecha de"`).
      - Within each family, for every pair $(A, B)$ where $\text{facets}(B) \supsetneq \text{facets}(A)$:
        - Checks if a curated relationship already exists between $A$ and $B$ with a non-`breakdown_of` type (`alternative_measure`, `related_concept`); if so, increments `skipped_curated_conflicts` and skips.
        - Otherwise records an `InferredEdge(parent_id=A, child_id=B, ...)` and, if `persist=True`, writes bidirectional `breakdown_of` edges `(A, B)` and `(B, A)` via `store.store_relationship(..., provenance="inferred")`.
      - Validates all inferred edges between any pair of the 45 curated indicators in `VERTICAL_SLICE_INDICATORS`: counts any inferred edge $(A, B)$ where $A, B \in \text{VERTICAL\_SLICE\_INDICATORS}$ that is NOT a valid `BREAKDOWN_OF` in `VERTICAL_SLICE_INDICATORS` as `false_curated_edges` (must be `0`).

- [ ] **Step 1: Write failing tests for `GraphBuilder` stem extraction, harvested dimension inference, and zero false edges on the 45 curated indicators**

```python
# In tests/test_semantic_graph_builder.py
import json
from pathlib import Path
from statscepal.catalog.harvester import CatalogHarvester
from statscepal.catalog.store import CatalogStore
from statscepal.semantic.graph_builder import GraphBuilder
from statscepal.semantic.registry import VERTICAL_SLICE_INDICATORS


def test_graph_builder_extracts_stems_and_infers_breakdown_from_harvested_dims(tmp_path):
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


def test_graph_builder_zero_false_edges_on_45_curated_indicators(tmp_path):
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
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_semantic_graph_builder.py -k "test_graph_builder"`
Expected: Fails with `ModuleNotFoundError: No module named 'statscepal.semantic.graph_builder'`.

- [ ] **Step 3: Implement `src/statscepal/semantic/graph_builder.py`**
Implement `InferredEdge`, `GraphBuildReport`, and `GraphBuilder` with stem normalization, facet extraction via `FacetOntology`, measure/unit compatibility guardrails, strict-superset `BREAKDOWN_OF` derivation, and `false_curated_edges` verification.

- [ ] **Step 4: Run tests to verify passing**
Run: `uv run pytest tests/test_semantic_graph_builder.py -v`
Expected: All tests pass.

- [ ] **Step 5: Run full non-integration and benchmark suites**
Run:
```bash
uv run pytest tests/test_semantic_benchmark_200.py -v
uv run pytest -m "not integration"
```
Expected: 100% pass, 0 regressions.

- [ ] **Step 6: Commit changes**
```bash
git add src/statscepal/semantic/graph_builder.py tests/test_semantic_graph_builder.py
git commit -m "feat(semantic): implement GraphBuilder for automatic BREAKDOWN_OF relationship inference"
```

---

### Task 3: CLI Subcommand `statscepal catalog build-graph` & End-to-End Certification

**Files:**
- Modify: `src/statscepal/cli.py`
- Modify: `src/statscepal/semantic/__init__.py`
- Modify: `tests/test_semantic_graph_builder.py`

**Interfaces:**
- Consumes: `GraphBuilder`, `CatalogStore`.
- Produces:
  - CLI command `statscepal catalog build-graph [--no-persist] [--no-seed-curated] [--json]`.
  - Exports `GraphBuilder`, `GraphBuildReport`, `InferredEdge` in `statscepal.semantic`.

- [ ] **Step 1: Write failing CLI tests for `statscepal catalog build-graph` (ASCII and `--json`)**

```python
# In tests/test_semantic_graph_builder.py
from statscepal.cli import main


def test_cli_catalog_build_graph_ascii_and_json(tmp_path, capsys, monkeypatch):
    db_path = tmp_path / "cli_graph.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.populate_official_indicators()

    monkeypatch.setattr("statscepal.cli.CatalogStore", lambda: CatalogStore(db_path=db_path))

    exit_code = main(["catalog", "build-graph"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "CEPALSTAT Breakdown Graph Builder" in out
    assert "False curated edges:       0" in out

    exit_code_json = main(["catalog", "build-graph", "--json"])
    assert exit_code_json == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["false_curated_edges"] == 0
    assert payload["inferred_edges_count"] >= 2
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_semantic_graph_builder.py -k test_cli_catalog_build_graph_ascii_and_json`
Expected: Fails because `build-graph` is not registered under `catalog_subparsers`.

- [ ] **Step 3: Implement `catalog build-graph` in `src/statscepal/cli.py` and export in `src/statscepal/semantic/__init__.py`**
- Register `build-graph` under `catalog_subparsers` with `--no-persist`, `--no-seed-curated`, and `--json`.
- Print ASCII summary report (or JSON when `--json` is passed) showing:
  - Total indicators analyzed
  - Concept families discovered
  - Curated edges count
  - Inferred `BREAKDOWN_OF` pairs count
  - Newly persisted edges count
  - Skipped curated conflicts
  - False curated edges (must be 0)
  - Sample inferred `BREAKDOWN_OF` edges (`parent_id -> child_id (+added_facets)`).

- [ ] **Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_semantic_graph_builder.py -v`
Expected: All tests in `test_semantic_graph_builder.py` pass.

- [ ] **Step 5: Run full benchmark and non-integration test suites**
Run:
```bash
uv run pytest tests/test_semantic_benchmark_200.py -v
uv run pytest -m "not integration"
```
Expected: 100% pass, 0 regressions, 0.00% FSR.

- [ ] **Step 6: Commit changes**
```bash
git add src/statscepal/cli.py src/statscepal/semantic/__init__.py tests/test_semantic_graph_builder.py
git commit -m "feat(cli): add 'statscepal catalog build-graph' command and certify E3 inference"
```

---

## Plan Self-Review Checklist
- [x] Every acceptance criterion of Epic **E3 · Automatic `BREAKDOWN_OF` Inference** is covered:
  - AC1: `src/statscepal/semantic/graph_builder.py` derives `B BREAKDOWN_OF A` when $A$ and $B$ share a concept root + compatible measure/unit and $\text{dimensions}(B) \supsetneq \text{dimensions}(A)$ in `FacetOntology` terms.
  - AC2: Inferred edges are written to `indicator_relationships` with `provenance = 'inferred'`.
  - AC3: Hand-curated edges have `provenance = 'curated'` and strictly take precedence over inferred edges.
  - AC4: Generates an edge summary report (`GraphBuildReport` + CLI `statscepal catalog build-graph`) verifying 0 false edges on the 45 reference indicators.
- [x] Strict TDD steps with exact file paths, test code, and verification commands.
- [x] 100% offline hermeticity and benchmark invariants preserved.
