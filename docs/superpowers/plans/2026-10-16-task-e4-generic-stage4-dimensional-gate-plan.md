# Task E4: Generic Stage 4 Dimensional Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `QueryParser`, `SemanticRegistry`, and `SemanticResolutionEngine` (Stage 4 Dimensional Gate) so that multidimensional breakdown detection, candidate conmutation, and dimension member binding operate 100% generically via `FacetOntology` and the SQLite-backed relational graph—with zero hardcoded facet branches (such as `"etnia"` or `{"POBREZA_TOTAL", "TOTAL", "NACIONAL"}` or `cand_id == 3342`), $p50 < 0.5\text{ ms}$ in-memory lookup latency, 100.0% Top-1 Accuracy, and 0.00% False Substitution Rate.

**Architecture:**
1. Extend `FacetOntology` (`src/statscepal/semantic/facet_ontology.py`) with `extract_facets_from_query(clean_query, thesaurus)` and complete `estrato`/`educacion`/`etnia` patterns so `QueryParser` (`src/statscepal/semantic/parser.py`) delegates ontology-driven facet extraction without hardcoded `"etnia"` branches.
2. Add bulk dimension and metadata loaders to `CatalogStore` (`src/statscepal/catalog/store.py`) and upgrade `SemanticRegistry` (`src/statscepal/semantic/registry.py`) to build an optimized in-memory index at startup from fallback seeds (`VERTICAL_SLICE_INDICATORS`, `DEFAULT_OFFICIAL_DIMENSIONS`) overlaid with SQLite (`master_indicators`, `indicator_metadata`, `indicator_dimensions`, `indicator_relationships`), automatically classifying harvested dimensions into `supported_facets` via `FacetOntology`.
3. Refactor Stage 4 of `SemanticResolutionEngine` (`src/statscepal/semantic/engine.py`) to determine unhandled facets via `self.ontology.is_critical_unhandled_facet()`, traverse `self.registry.get_relationships(canonical_id)` for `BREAKDOWN_OF` edges (both curated and inferred), and bind dimension members without any hardcoded facet or indicator ID literals.

**Tech Stack:** Python 3.10+, SQLite3, Pydantic v2, pytest.

**Spec:** [docs/superpowers/plans/2026-10-16-epic-metadata-ingestion-generic-facet-routing.md](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-16-epic-metadata-ingestion-generic-facet-routing.md) (Section E4) and [.agents/rules/semantic-resolution-guardrails.md](file:///C:/papx/statscepal/.agents/rules/semantic-resolution-guardrails.md).

## Global Constraints
- Python 3.10+ modern typing syntax (`int | None`, `list[str]`, `dict[str, Any]`).
- All 257+ existing non-integration tests must remain passing without regression.
- False Substitution Rate must strictly equal 0.00% across the 200-question benchmark.
- Top-1 Accuracy across the 200 benchmark test cases must strictly remain 100.0%.
- Zero hardcoded `"etnia"`, `{"POBREZA_TOTAL", "TOTAL", "NACIONAL"}`, or `3342` branches in Stage 4 of `src/statscepal/semantic/engine.py`.
- Local resolution latency over the in-memory index must maintain $p50 < 0.5\text{ ms}$.
- Strict offline hermeticity: unit and CLI tests must NEVER perform live network calls.

---

## File Structure & Responsibilities

| File | Action | Responsibility |
|---|---|---|
| `src/statscepal/semantic/facet_ontology.py` | Modify | Add `extract_facets_from_query()` to `FacetOntology`; complete `estrato`, `etnia`, `educacion`, and `actividad` member/trigger patterns. |
| `src/statscepal/semantic/parser.py` | Modify | Inject `FacetOntology` into `QueryParser` and delegate ontology-driven facet extraction, removing the hardcoded `"etnia"` block. |
| `src/statscepal/catalog/store.py` | Modify | Add bulk loaders `get_all_indicator_metadata()` and `get_all_indicator_dimensions()` for fast startup indexing. |
| `src/statscepal/semantic/registry.py` | Modify | Build in-memory index at startup from fallback seeds overlaid with SQLite store; auto-derive `supported_facets` from harvested dimensions via `FacetOntology`; complete `DEFAULT_OFFICIAL_DIMENSIONS[3340]`. |
| `src/statscepal/semantic/engine.py` | Modify | Refactor Stage 4 Dimensional Gate to use `FacetOntology.is_critical_unhandled_facet()`, `registry.get_supported_facets()`, and `registry.get_relationships()` with zero hardcoded facet/indicator literals. |
| `tests/test_semantic_generic_gate.py` | Create | Unit and end-to-end tests for ontology-driven query facet extraction, SQLite-backed `SemanticRegistry` indexing, AST/source verification of zero hardcoded literals in Stage 4, and dynamic routing to uncurated SQLite-inferred breakdown indicators. |

---

### Task 1: Ontology-Driven Query Facet Extraction in `FacetOntology` & `QueryParser`

**Files:**
- Modify: `src/statscepal/semantic/facet_ontology.py`
- Modify: `src/statscepal/semantic/parser.py`
- Create: `tests/test_semantic_generic_gate.py`

**Interfaces:**
- Consumes: `Thesaurus`, `strip_accents`.
- Produces:
  - `FacetOntology.extract_facets_from_query(self, clean_query: str, thesaurus: Any = None) -> dict[str, str]`:
    - Iterates over registered `FacetDefinition` entries.
    - Checks `thesaurus.match_synset(fdef.synset_domain, clean_query)` if `thesaurus` is provided and `fdef.synset_domain` is set (only for facets not already handled or with explicit triggers).
    - Evaluates `fdef.query_triggers` (`QueryTriggerRule`) using word boundaries (`\b...\b`) when `require_word_boundary=True`.
  - Complete `member_value_patterns` in `DEFAULT_FACETS` for `estrato` (`QUINTIL_1`..`QUINTIL_5`, `DECIL_1`, `DECIL_10`, `DECIL`, `QUINTIL`, `RELACION_Q5_Q1`) and refined `query_triggers` for `etnia`, `educacion`, and `actividad` (ensuring `quintil`, `moneda`, and `actividad` triggers do not false-trigger on macroeconomic/fiscal queries).
  - `QueryParser.__init__(self, catalog_profile: str = "official_25", thesaurus: Thesaurus | None = None, ontology: FacetOntology | None = None)` delegating ontology facet extraction to `self.ontology.extract_facets_from_query(clean, self.thesaurus)` without hardcoded `"etnia"` branches.

- [ ] **Step 1: Write failing tests for ontology-driven query facet extraction and `QueryParser` delegation**

```python
# In tests/test_semantic_generic_gate.py
import inspect
from statscepal.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY
from statscepal.semantic.parser import QueryParser


def test_facet_ontology_extracts_facets_from_query_generically():
    parser = QueryParser()

    # Ethnic breakdown queries extracted via ontology
    i_etnia = parser.parse("cual es la pobreza etnica en el peru del 2020")
    assert i_etnia.facets.get("etnia") == "ETNICO_TOTAL"

    i_indigena = parser.parse("pobreza indigena en bolivia 2021")
    assert i_indigena.facets.get("etnia") == "INDIGENA"

    i_afro = parser.parse("tasa de pobreza en afrodescendientes en brasil 2022")
    assert i_afro.facets.get("etnia") == "AFRODESCENDIENTE"

    # Education breakdown query extracted via ontology
    i_edu = parser.parse("pobreza segun educacion universitaria en colombia 2021")
    assert i_edu.root_concept == "POBREZA"
    assert i_edu.facets.get("educacion") == "UNIVERSITARIA"

    # Public spending on education must remain GASTO_EDUCACION without spurious educacion facet
    i_gasto_edu = parser.parse("gasto publico en educacion en mexico 2020")
    assert i_gasto_edu.root_concept == "GASTO_EDUCACION"
    assert "educacion" not in i_gasto_edu.facets

    # Verify QueryParser.parse contains no hardcoded 'facets["etnia"]' assignment
    parse_src = inspect.getsource(QueryParser.parse)
    assert 'facets["etnia"]' not in parse_src
    assert "facets['etnia']" not in parse_src
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_semantic_generic_gate.py -k test_facet_ontology_extracts_facets_from_query_generically`
Expected: Fails because `educacion` is not extracted and `facets["etnia"]` is still hardcoded in `QueryParser.parse`.

- [ ] **Step 3: Implement `extract_facets_from_query` in `src/statscepal/semantic/facet_ontology.py` and refactor `src/statscepal/semantic/parser.py`**
- Update `DEFAULT_FACETS` in `src/statscepal/semantic/facet_ontology.py`:
  - `etnia`: include `QueryTriggerRule` for `INDIGENA`, `AFRODESCENDIENTE`, `NO_INDIGENA`, and `ETNICO_TOTAL` (`"etnica"`, `"etnico"`, `"etnicas"`, `"etnicos"`, `"etnia"`).
  - `estrato`: include `member_value_patterns` for `QUINTIL_1`..`QUINTIL_5`, `DECIL_1`, `DECIL_10`, `DECIL`, `QUINTIL`, `RELACION_Q5_Q1`.
  - `educacion`: include `QueryTriggerRule` for `UNIVERSITARIA` (`"educacion universitaria"`, `"universitaria"`, `"educacion superior"`), `SECUNDARIA` (`"educacion secundaria"`, `"secundaria completa"`), `PRIMARIA` (`"educacion primaria"`, `"primaria completa"`), `SIN_INSTRUCCION` (`"sin instruccion"`).
  - Ensure `quintil`, `moneda`, and `actividad` `query_triggers` only match explicit disaggregation phrases so they never collide with fiscal (`"gasto publico"`, `"gobierno"`), GDP (`"dolares constantes"`), or `estrato` queries.
- Implement `FacetOntology.extract_facets_from_query(self, clean_query: str, thesaurus: Any = None, facet_keys: set[str] | None = None) -> dict[str, str]`.
- In `QueryParser`: replace the hardcoded `"etnia"` block with generic delegation to `self.ontology.extract_facets_from_query(...)` (protecting `"gasto"` queries from setting `"educacion"` when `"gasto"` is the root concept).

- [ ] **Step 4: Run tests to verify passing**
Run: `uv run pytest tests/test_semantic_generic_gate.py -v`
Expected: 1 passed.

- [ ] **Step 5: Run benchmark and non-integration test suites**
Run:
```bash
uv run pytest tests/test_semantic_benchmark_200.py -v
uv run pytest -m "not integration"
```
Expected: 100% pass, 0 regressions.

- [ ] **Step 6: Commit changes**
```bash
git add src/statscepal/semantic/facet_ontology.py src/statscepal/semantic/parser.py tests/test_semantic_generic_gate.py
git commit -m "refactor(semantic): delegate query facet extraction in QueryParser to FacetOntology"
```

---

### Task 2: SQLite-Backed In-Memory Index in `CatalogStore` & `SemanticRegistry`

**Files:**
- Modify: `src/statscepal/catalog/store.py`
- Modify: `src/statscepal/semantic/registry.py`
- Modify: `tests/test_semantic_generic_gate.py`

**Interfaces:**
- Consumes: `CatalogStore`, `FacetOntology`, `DEFAULT_FACET_ONTOLOGY`.
- Produces:
  - `CatalogStore.get_all_indicator_metadata() -> dict[int, dict[str, Any]]`
  - `CatalogStore.get_all_indicator_dimensions() -> dict[int, list[Dimension]]`
  - `SemanticRegistry`:
    - `__init__(self, store: CatalogStore | None = None, dimensions: dict[int, list[Dimension]] | None = None, relationships: dict[Any, Any] | None = None, temporal_availability: ... = None, catalog_profile: str = "official_25", ontology: FacetOntology | None = None)`
    - Preloads an in-memory index (`_indicators_index`, `_dimensions_index`, `_relationships_index`) from static fallback seeds (`VERTICAL_SLICE_INDICATORS`, `DEFAULT_OFFICIAL_DIMENSIONS`), then overlays SQLite `CatalogStore` data (`master_indicators`, `indicator_metadata`, `indicator_dimensions`, `indicator_relationships`), then applies any explicit constructor overrides (`dimensions`, `relationships`).
    - Automatically classifies dimensions via `self.ontology.classify_dimension(d.id, d.name)` to enrich `supported_facets` and synthesize `IndicatorMetadata` for harvested catalog indicators not present in `VERTICAL_SLICE_INDICATORS`.
    - `get_supported_facets(self, indicator_id: int) -> set[str]`
    - `reload_from_store(self) -> None`
    - Completes `DEFAULT_OFFICIAL_DIMENSIONS[3340]` with decil, quintil ratio, and area members so `3340` resolves all `estrato` and `area` queries when dimensions are active.

- [ ] **Step 1: Write failing tests for `CatalogStore` bulk loaders and `SemanticRegistry` SQLite in-memory indexing**

```python
# In tests/test_semantic_generic_gate.py
from statscepal.catalog.store import CatalogStore
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.registry import SemanticRegistry
from statscepal.semantic.models import RelationshipType


def test_semantic_registry_builds_in_memory_index_from_sqlite_and_synthesizes_metadata(tmp_path):
    db_path = tmp_path / "reg_index.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    # Insert an uncurated catalog indicator 90001 into master_indicators
    with store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO master_indicators (indicator_id, name, theme, area, subarea, full_path)
            VALUES (90001, 'Población en situación de pobreza extrema y pobreza, por nivel educativo y área', 'Sociales', 'Pobreza', '', 'Sociales > Pobreza')
            """
        )

    # Store harvested dimensions for 90001
    store.store_indicator_dimensions(
        90001,
        [
            Dimension(
                id=326,
                name="Área geográfica",
                members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbana"), Member(id=331, name="Rural")],
            ),
            Dimension(
                id=500,
                name="Tipo de pobreza",
                members=[Member(id=501, name="Pobreza extrema"), Member(id=502, name="Total pobreza")],
            ),
            Dimension(
                id=88001,
                name="Nivel de educación",
                members=[
                    Member(id=88010, name="Primaria"),
                    Member(id=88011, name="Secundaria"),
                    Member(id=88012, name="Universitaria"),
                    Member(id=88013, name="Total"),
                ],
            ),
        ],
    )
    store.store_relationship(3328, 90001, "breakdown_of", provenance="inferred")
    store.store_relationship(90001, 3328, "breakdown_of", provenance="inferred")

    registry = SemanticRegistry(store=store)

    # 90001 is synthesized into in-memory index even though it is not in VERTICAL_SLICE_INDICATORS
    meta_90001 = registry.get_indicator(90001)
    assert meta_90001 is not None
    assert "educacion" in registry.get_supported_facets(90001)
    assert "area" in registry.get_supported_facets(90001)
    assert "severidad" in registry.get_supported_facets(90001)

    # 3328 relationships include both static curated and SQLite inferred 90001
    rels_3328 = registry.get_relationships(3328)
    assert rels_3328.get(90001) == RelationshipType.BREAKDOWN_OF
    assert rels_3328.get(3342) == RelationshipType.BREAKDOWN_OF
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_semantic_generic_gate.py -k test_semantic_registry_builds_in_memory_index_from_sqlite_and_synthesizes_metadata`
Expected: Fails because `registry.get_indicator(90001)` returns `None` and `get_supported_facets` does not exist.

- [ ] **Step 3: Implement bulk loaders in `src/statscepal/catalog/store.py` and in-memory indexing in `src/statscepal/semantic/registry.py`**
- In `src/statscepal/catalog/store.py`:
  - Add `get_all_indicator_metadata(self) -> dict[int, dict[str, Any]]`.
  - Add `get_all_indicator_dimensions(self) -> dict[int, list[Dimension]]`.
- In `src/statscepal/semantic/registry.py`:
  - Complete `DEFAULT_OFFICIAL_DIMENSIONS[3340]` with decil (`Primer decil`, `Décimo decil`, `Deciles`), ratio (`Relación quintil 5 / quintil 1`), and `326: Área geográfica` members.
  - Add `ontology: FacetOntology | None = None` to `SemanticRegistry.__init__`.
  - Build in-memory caches (`_indicators_index`, `_dimensions_index`, `_relationships_index`) from static seeds, overlay SQLite store data, synthesize `IndicatorMetadata` for harvested indicators in `master_indicators`/`indicator_dimensions`, and apply explicit constructor `dimensions`/`relationships` overrides.
  - Implement `get_supported_facets(self, indicator_id: int) -> set[str]` and `reload_from_store(self) -> None`.
  - Ensure `get_dimensions`, `get_relationships`, and `get_indicator` hit the fast in-memory index first and fall back to `self.store` on cache miss (preserving compatibility if a test writes to `store` after initializing `SemanticRegistry`).

- [ ] **Step 4: Run tests to verify passing**
Run: `uv run pytest tests/test_semantic_generic_gate.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run benchmark and non-integration test suites**
Run:
```bash
uv run pytest tests/test_semantic_benchmark_200.py -v
uv run pytest -m "not integration"
```
Expected: 100% pass, 0 regressions.

- [ ] **Step 6: Commit changes**
```bash
git add src/statscepal/catalog/store.py src/statscepal/semantic/registry.py tests/test_semantic_generic_gate.py
git commit -m "feat(semantic): preload SQLite dimensions and relationships into SemanticRegistry in-memory index"
```

---

### Task 3: Generic Stage 4 Dimensional Gate in `SemanticResolutionEngine` & End-to-End Certification

**Files:**
- Modify: `src/statscepal/semantic/engine.py`
- Modify: `tests/test_semantic_generic_gate.py`

**Interfaces:**
- Consumes: `FacetOntology`, `SemanticRegistry`, `DynamicMemberMatcher`, `QueryParser`.
- Produces:
  - `SemanticResolutionEngine.__init__(self, parser=None, registry=None, matcher=None, catalog_profile="official_25", ontology=None)`
  - Generic Stage 4 Dimensional Gate in `SemanticResolutionEngine.resolve()`:
    - Zero hardcoded `"etnia"`, `{"POBREZA_TOTAL", "TOTAL", "NACIONAL"}`, or `3342` checks.
    - Uses `self.ontology.is_critical_unhandled_facet(fk, fv)` for all implicit-aggregate vs. critical-breakdown decisions.
    - Uses `self.registry.get_supported_facets(id)` and `self.registry.get_relationships(canonical_id)` to traverse both curated and inferred `BREAKDOWN_OF` edges.

- [ ] **Step 1: Write failing tests for generic Stage 4 routing on uncurated SQLite-inferred indicators and zero hardcoded literals in `engine.py`**

```python
# In tests/test_semantic_generic_gate.py
import json
from pathlib import Path
from statscepal.catalog.harvester import CatalogHarvester
from statscepal.semantic.engine import SemanticResolutionEngine
from statscepal.semantic.graph_builder import GraphBuilder
from statscepal.semantic.models import RelationshipType, ResolutionStatus


def test_engine_stage4_has_zero_hardcoded_facet_or_indicator_literals():
    engine_src = inspect.getsource(SemanticResolutionEngine.resolve)
    assert '"etnia"' not in engine_src
    assert "'etnia'" not in engine_src
    assert "POBREZA_TOTAL" not in engine_src
    assert "3342" not in engine_src


def test_engine_routes_generically_to_sqlite_inferred_breakdown_indicator(tmp_path):
    db_path = tmp_path / "e2e_generic_gate.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    # Insert canonical 3328 and a brand-new uncurated breakdown indicator 90001 into master_indicators
    with store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO master_indicators (indicator_id, name, theme, area, subarea, full_path)
            VALUES
            (3328, 'Población en situación de pobreza extrema y pobreza, por área', 'Sociales', 'Pobreza', '', 'Sociales > Pobreza'),
            (90001, 'Población en situación de pobreza extrema y pobreza, por nivel de educación y área', 'Sociales', 'Pobreza', '', 'Sociales > Pobreza')
            """
        )

    f_3328 = json.loads(Path("tests/fixtures/dimensions/indicator_3328.json").read_text(encoding="utf-8"))
    store.store_indicator_dimensions(3328, CatalogHarvester._parse_dimensions(f_3328))
    store.store_indicator_dimensions(
        90001,
        [
            Dimension(
                id=326,
                name="Área geográfica",
                members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbana"), Member(id=331, name="Rural")],
            ),
            Dimension(
                id=1361,
                name="Pobreza extrema y pobreza",
                members=[Member(id=501, name="Pobreza extrema"), Member(id=502, name="Pobreza")],
            ),
            Dimension(
                id=88001,
                name="Nivel de educación",
                members=[
                    Member(id=88010, name="Primaria"),
                    Member(id=88011, name="Secundaria"),
                    Member(id=88012, name="Universitaria"),
                    Member(id=88013, name="Total"),
                ],
            ),
        ],
    )

    # 1. Automatically infer BREAKDOWN_OF graph edges via E3 GraphBuilder
    builder = GraphBuilder(store=store)
    build_report = builder.build_breakdown_graph(persist=True, seed_curated=False)
    assert (3328, 90001) in {(e.parent_id, e.child_id) for e in build_report.inferred_edges}

    # 2. Initialize SemanticRegistry + Engine backed by SQLite store
    registry = SemanticRegistry(store=store)
    engine = SemanticResolutionEngine(registry=registry)

    # 3. Query requesting 'educacion universitaria' must conmute 3328 -> 90001 and bind member 88012
    resp = engine.resolve("pobreza segun educacion universitaria en colombia 2021")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 90001
    assert resp.selected_candidate.swapped_from == 3328
    assert resp.selected_candidate.swap_relationship == RelationshipType.BREAKDOWN_OF

    edu_dim = next((d for d in resp.applied_filters.dimensions if d.dim_id == 88001), None)
    assert edu_dim is not None
    assert edu_dim.member_id == 88012
    assert edu_dim.member_name == "Universitaria"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_semantic_generic_gate.py -k "test_engine_"`
Expected: Fails because `engine.py` still contains `"etnia"`, `"POBREZA_TOTAL"`, and `3342` literals and iterates over `default_meta.relationships` instead of `self.registry.get_relationships(canonical_id)`.

- [ ] **Step 3: Refactor Stage 4 in `src/statscepal/semantic/engine.py`**
- Accept `ontology: FacetOntology | None = None` in `SemanticResolutionEngine.__init__` and wire it to `parser`, `registry`, and `matcher`.
- Replace all hardcoded facet/aggregate/3342 checks in Stage 4 with `self.ontology.is_critical_unhandled_facet()`, `self.registry.get_supported_facets()`, `self.registry.get_relationships()`, and `self.registry.get_dimensions()`.

- [ ] **Step 4: Run tests to verify passing**
Run: `uv run pytest tests/test_semantic_generic_gate.py tests/test_semantic_breakdowns.py -v`
Expected: All tests pass.

- [ ] **Step 5: Run full benchmark and non-integration test suites**
Run:
```bash
uv run pytest tests/test_semantic_benchmark_200.py -v
uv run pytest -m "not integration"
```
Expected: 200/200 benchmark pass (100.0% Top-1 Accuracy, 0.00% FSR, $p50 < 0.5\text{ ms}$), 260+ non-integration tests pass with 0 regressions.

- [ ] **Step 6: Commit changes**
```bash
git add src/statscepal/semantic/engine.py tests/test_semantic_generic_gate.py
git commit -m "feat(semantic): implement generic Stage 4 dimensional gate driven by FacetOntology and graph"
```

---

## Plan Self-Review Checklist
- [x] **AC1:** `src/statscepal/semantic/engine.py` Stage 4 operates entirely via `FacetOntology` and the relational graph.
- [x] **AC2:** Zero hardcoded string literals for facets (no `"etnia"` branches, no `{"POBREZA_TOTAL", "TOTAL", "NACIONAL"}`, no `3342`) in `engine.py`, `parser.py`, and `matcher.py` (enforced by automated source inspection tests).
- [x] **AC3:** `SemanticRegistry` loads dimensions, metadata, and relationships from SQLite into an optimized in-memory index at startup, using static Python dicts as fallback seeds.
- [x] **AC4:** Ethnic poverty routing (`pobreza etnica` -> `3342`), uncurated SQLite-inferred breakdown routing (`3328 -> 90001`), and all 200 benchmark test cases pass with 100.0% accuracy and 0.00% FSR.
- [x] **AC5:** Local resolution latency maintains $p50 < 0.5\text{ ms}$ over the in-memory index.
