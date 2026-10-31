# Phase 2: Full Metadata Harvester, SQLite FTS5 Search, Graph Hardening & Cold-Start Seed Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable instant cold-start installation (`< 50 ms`), sub-2ms `SQLite FTS5` + `BM25` + synonym-expanded discovery across all 1,739 CEPALSTAT indicators, sound directed `BREAKDOWN_OF` graph inference over ODS and specialized tables, and accurate post-2023 temporal availability.

**Architecture:** Extend `CatalogHarvester` to ingest `/metadata` (`unit`, `periodicity`, `definition`) alongside `/dimensions` and derive `temporal_availability` from structural Year dimension members. Replace `CatalogStore.search()`'s unindexed `LIKE` scan with an `FTS5` virtual table (`indicators_fts`, `unicode61 remove_diacritics 2`) indexing indicator titles, thematic paths, units, and non-structural `dimension_members`, queried with sanitized Spanish stem + `Thesaurus` synonym expansion. Harden `GraphBuilder` with SDG code stripping, unit/area guards, opaque `"__raw_dim__:<name>"` tokens for unmapped dimensions, directed edges (`parent -> child`), and single-pass SQLite preloading, then package a compressed `seed_catalog.db.gz` + bundled `bitacoras` inside the wheel for atomic cold-start hydration.

**Tech Stack:** Python >=3.10, `uv`, `sqlite3` (`FTS5`), `gzip`, `importlib.resources`, `hatchling`, `pydantic` v2, `pytest`, `mypy`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-10-30-pre-mcp-semantic-scaling-spec.md`

## Global Constraints

- Import always from `unofficial_cepalstat_mcp` (never `from statscepal`).
- Always run `uv run pytest -m "not integration"`; CI/unit tests must never make live HTTP calls (use recorded fixtures / `respx` / `pytest-mock`).
- Open every SQLite connection with `timeout=10.0` + `PRAGMA busy_timeout = 10000;` and close in `finally`.
- Preserve **0.00% FSR**, **Zero Facet Loss**, `provenance='curated'` precedence over `'inferred'`, and `forbid_interpolation=True` on `BADEHOG_SURVEY_INDICATORS`.
- Never create `statscepal.db` in repo root or unconditional `./bitacoras` directories in the caller's CWD.
- Pass `uv run mypy src/unofficial_cepalstat_mcp/`, `uv run ruff check .`, and `uv build` cleanly.

## Review Focus

1. **FTS5 syntax-error punctuation in natural queries (`"PIB (USD) 2020-2024"`, `"pobreza %"`, `"I+D"`, `"Q5/Q1"`, `"O'Higgins"`):** Raw punctuation passed to `indicators_fts MATCH ?` raises `sqlite3.OperationalError: fts5: syntax error` — query builder must extract clean alphanumeric stems before constructing `MATCH` clauses.
2. **Unmapped specialized dimension inverting `BREAKDOWN_OF` hierarchy (`"Tasa de mortalidad, por causa de muerte"` vs `"Tasa de mortalidad, por sexo"`):** `GraphBuilder.extract_indicator_facets` must emit `"__raw_dim__:<normalized_dim_name>"` for unmapped non-structural dimensions instead of dropping them to `set()`, preventing specialized tables from becoming false aggregate parents.
3. **Duplicate titles across incompatible areas/units & trailing UN SDG codes (`EN_ATM_GHGT_WLU`, `"Densidad poblacional"`):** `GraphBuilder` must strip trailing SDG series codes (`r"\s+[A-Z]{2}(?:_[A-Z0-9]+){2,}\s*$"`) on stem extraction while requiring identical `(area, normalized_unit)` before inferring any edge.
4. **2024–2026 temporal cliff & bogus survey-sampling disclaimer on annual macro series (`"inflación en Chile 2020-2025"`):** `SemanticRegistry.check_temporal_availability` must not mark `2024–2026` as `OBSERVATION_MISSING` by default on non-survey annual series, and Stage 5 sampling-gap disclaimers must be restricted to `BADEHOG_SURVEY_INDICATORS`.
5. **Atomic cold-start hydration & read-only CWD under MCP hosts:** Decompressing `seed_catalog.db.gz` into `get_cache_db_path()` must write to a temporary file in the cache directory and `os.replace()` atomically; `BitacoraStore()` with `base_dir=None` must read packaged recipes without calling `mkdir` on `./bitacoras`.

---

## File Structure

- **Modify:** `src/unofficial_cepalstat_mcp/catalog/harvester.py` — Harvest `/indicator/{id}/metadata` (`unit`, `definition`, `periodicity`) alongside `/dimensions` and extract per-indicator available years from structural Time dimensions.
- **Modify:** `src/unofficial_cepalstat_mcp/catalog/store.py` — Add `indicators_fts` `FTS5` virtual table (`unicode61 remove_diacritics 2`), `rebuild_fts_index()`, tokenized `BM25` + `Thesaurus`-expanded `search()`, `definition`/`periodicity` columns in `indicator_metadata`, and cold-start seed hydration hook.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/registry.py` & `src/unofficial_cepalstat_mcp/semantic/engine.py` — Remove hardcoded `2023` ceiling in `check_temporal_availability` and scope survey-sampling disclaimers in `engine.py` to `BADEHOG_SURVEY_INDICATORS`.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/facet_ontology.py`, `src/unofficial_cepalstat_mcp/semantic/matcher.py`, `src/unofficial_cepalstat_mcp/semantic/graph_builder.py` — Tighten bare single-word `dimension_name_patterns`, classify subnational dimensions (`division administrativa`, `municipio`, `ciudad`), exclude `__structural__` dims from `matcher.py` Group B fallback, strip SDG codes, preserve `"__raw_dim__:<name>"`, persist directed `parent -> child` edges, and preload SQLite tables once in `GraphBuilder`.
- **Create:** `src/unofficial_cepalstat_mcp/data/__init__.py` & `src/unofficial_cepalstat_mcp/catalog/seed.py` — Build (`export_seed_snapshot`) and atomically hydrate (`ensure_seed_hydrated`) `seed_catalog.db.gz` + packaged `bitacoras` recipes via `importlib.resources`.
- **Modify:** `src/unofficial_cepalstat_mcp/bitacora/store.py`, `src/unofficial_cepalstat_mcp/cli.py`, `pyproject.toml` — Stop unconditional `./bitacoras` `mkdir`, add `catalog export-seed` CLI subcommand, and include `seed_catalog.db.gz` + `bitacoras/**/*.md` in wheel artifacts.
- **Create:** `tests/test_catalog_fts5_search.py` & `tests/test_cold_start_seed.py`; **Modify:** `tests/test_catalog_harvester.py`, `tests/test_semantic_graph_builder.py`, `tests/test_semantic_facet_ontology.py`, `tests/test_semantic_matcher.py`, `tests/test_semantic_multi_year.py`, `tests/test_packaging_metadata.py`.

---

### Task 1: Metadata Harvesting (`/metadata`) & Temporal Cliff Remediation (`2024+` & `BADEHOG` Scoping)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/catalog/store.py:140-150, 577-652`
- Modify: `src/unofficial_cepalstat_mcp/catalog/harvester.py:89-180`
- Modify: `src/unofficial_cepalstat_mcp/semantic/registry.py:1518-1544`
- Modify: `src/unofficial_cepalstat_mcp/semantic/engine.py:715-880`
- Modify: `tests/test_catalog_harvester.py`
- Modify: `tests/test_semantic_multi_year.py`

**Interfaces:**
- Consumes: `Phase 1` real CEPALSTAT IDs in `VERTICAL_SLICE_INDICATORS` and `BADEHOG_SURVEY_INDICATORS`
- Produces:
  - `CatalogStore.store_indicator_metadata(..., definition: str = "", periodicity: str = "") -> None`
  - `CatalogHarvester.harvest(..., include_metadata: bool = True) -> HarvestSummary`
  - `SemanticRegistry.check_temporal_availability(self, indicator_id: int, country_code: str, year: int) -> tuple[TemporalAvailabilityStatus, int | None, int | None]` without hardcoded `2023` cliff.

- [ ] **Step 1: Write failing tests for `/metadata` harvesting and Review Focus #4 (`2024–2025` macro range without false survey disclaimer)**

Append to `tests/test_catalog_harvester.py` and `tests/test_semantic_multi_year.py`:
```python
# In tests/test_catalog_harvester.py
def test_harvester_persists_unit_and_periodicity_from_metadata_endpoint(tmp_path, mocker) -> None:
    store = CatalogStore(db_path=tmp_path / "h.db")
    with store._get_connection() as conn:
        conn.execute(
            "INSERT INTO master_indicators VALUES (2484, 'IPC anual', 10, 'Económicos', 'Precios', '', 'Económicos > Precios', '2026-10-30')"
        )
    client = mocker.Mock()
    client.get.side_effect = [
        {"body": {"dimensions": [{"id": 208, "name": "País__ESTANDAR", "members": [{"id": 1, "name": "Chile"}]}, {"id": 29117, "name": "Años__ESTANDAR", "members": [{"id": 2, "name": "2024"}, {"id": 3, "name": "2025"}]}]}},
        {"body": {"metadata": {"unit": "Variación anual (%)", "periodicity": "Anual", "definition": "Variación dic-dic"}}},
    ]
    summary = CatalogHarvester(client=client, store=store, rate_limit_delay=0.0).harvest(indicator_ids=[2484])
    assert summary.newly_harvested == 1
    meta = store.get_indicator_metadata(2484)
    assert meta is not None
    assert meta["unit"] == "Variación anual (%)"
    assert meta["periodicity"] == "Anual"


# In tests/test_semantic_multi_year.py
def test_macro_cpi_range_2020_2025_does_not_emit_false_survey_gap() -> None:
    engine = SemanticResolutionEngine()
    resp = engine.resolve("inflación anual en Chile 2020-2025")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.temporal_info is not None
    assert resp.temporal_info.unobserved_years == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_catalog_harvester.py tests/test_semantic_multi_year.py -k "persists_unit or 2020_2025" -v`
Expected: FAIL (`harvester` only calls `/dimensions`; `2020-2025` marks `[2024, 2025]` as unobserved survey gaps).

- [ ] **Step 3: Implement `/metadata` harvesting in `CatalogHarvester` and fix `check_temporal_availability` + Stage 5 disclaimer scoping**

1. Add `definition TEXT DEFAULT ''` and `periodicity TEXT DEFAULT ''` columns (with `PRAGMA table_info` migration) to `indicator_metadata` in `CatalogStore.init_semantic_tables()` and expose them in `store_indicator_metadata` / `get_indicator_metadata` / `get_all_indicator_metadata`.
2. In `CatalogHarvester.harvest()`, when `include_metadata=True`, fetch `/cepalstat/api/v1/indicator/{ind_id}/metadata` and persist `unit`, `definition`, and `periodicity` (preserving curated `concept` / `measure_type` if already present).
3. In `SemanticRegistry.check_temporal_availability()`, replace `2000 <= year <= 2023` with `1950 <= year <= datetime.now(timezone.utc).year` when no explicit `TEMPORAL_AVAILABILITY_MATRIX` or SQLite `temporal_availability` row exists, and in `engine.py` emit `"diseño muestral"` wording only when `target_indicator_id in BADEHOG_SURVEY_INDICATORS` (using neutral `"período sin observación registrada"` wording otherwise).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_catalog_harvester.py tests/test_semantic_multi_year.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/catalog/store.py src/unofficial_cepalstat_mcp/catalog/harvester.py src/unofficial_cepalstat_mcp/semantic/registry.py src/unofficial_cepalstat_mcp/semantic/engine.py tests/test_catalog_harvester.py tests/test_semantic_multi_year.py
git commit -m "feat(catalog): harvest indicator metadata and remove hardcoded 2023 temporal cliff"
```

---

### Task 2: SQLite `FTS5` Virtual Index, `Thesaurus` Synonym Expansion & Composite `BM25` Ranking

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/catalog/store.py:61-155, 206-262, 310-340`
- Create: `tests/test_catalog_fts5_search.py`
- Modify: `tests/test_catalog_store.py`

**Interfaces:**
- Consumes: `get_default_thesaurus()` from `unofficial_cepalstat_mcp.semantic.thesaurus`; `DEFAULT_FACET_ONTOLOGY` from `unofficial_cepalstat_mcp.semantic.facet_ontology`
- Produces:
  - `CatalogStore.rebuild_fts_index(self) -> int`
  - `CatalogStore.search(self, query: str = "", theme: str | None = None, area: str | None = None, limit: int = 20) -> list[CatalogIndicator]` backed by `indicators_fts` (`unicode61 remove_diacritics 2`) with `BM25` ranking, non-adjacent multi-token matching, Spanish plural/gender prefix matching, `Thesaurus` synonym expansion, and punctuation sanitization.

- [ ] **Step 1: Write failing `FTS5` discovery tests (including Review Focus #1 punctuation safety, non-adjacent words, synonyms, member labels, and ranking)**

Create `tests/test_catalog_fts5_search.py`:
```python
from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.dimensions import Dimension, Member


def _seeded_store(tmp_path) -> CatalogStore:
    store = CatalogStore(db_path=tmp_path / "fts.db")
    with store._get_connection() as conn:
        rows = [
            (2656, "Tiempo de Trabajo no Remunerado según ingresos propios y pobreza", 0, "Género", "Género", "", "Género > Uso del tiempo", "2026-10-30"),
            (3328, "Población en situación de pobreza extrema y pobreza, por área", 40, "Sociales", "Sociales", "Pobreza", "Sociales > Pobreza", "2026-10-30"),
            (127, "Tasa de desocupación por sexo", 20, "Sociales", "Sociales", "Empleo", "Sociales > Empleo", "2026-10-30"),
            (1912, "Exportaciones totales de bienes FOB", 10, "Económicos", "Comercio Internacional y Balanza de Pagos", "", "Económicos > Comercio", "2026-10-30"),
            (821, "Ingresos tributarios por tipo de impuestos en porcentajes del PIB", 10, "Económicos", "Sector público", "", "Económicos > Fiscal", "2026-10-30"),
        ]
        conn.executemany("INSERT INTO master_indicators VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    store.store_indicator_dimensions(
        127, [Dimension(id=144, name="Sexo__ESTANDAR", members=[Member(id=266, name="Mujeres"), Member(id=265, name="Hombres")])]
    )
    store.store_indicator_dimensions(
        821, [Dimension(id=900, name="Tipo de impuesto", members=[Member(id=901, name="Impuesto al valor agregado (IVA)")])]
    )
    store.rebuild_fts_index()
    return store


def test_fts5_finds_non_adjacent_tokens_and_dimension_members(tmp_path) -> None:
    store = _seeded_store(tmp_path)
    assert [r.indicator_id for r in store.search("exportaciones bienes")][:1] == [1912]
    assert [r.indicator_id for r in store.search("desocupación mujeres")][:1] == [127]
    assert [r.indicator_id for r in store.search("recaudación IVA")][:1] == [821] or 821 in [r.indicator_id for r in store.search("impuestos IVA")]


def test_fts5_expands_synonyms_and_ranks_core_poverty_above_peripheral_order_zero(tmp_path) -> None:
    store = _seeded_store(tmp_path)
    assert 127 in [r.indicator_id for r in store.search("desempleo")]
    results = store.search("pobreza", limit=5)
    assert results[0].indicator_id == 3328


def test_fts5_sanitizes_punctuation_and_operators_without_operational_error(tmp_path) -> None:
    store = _seeded_store(tmp_path)
    for hostile in ["PIB (USD) 2020-2024", "pobreza %", "I+D", "Q5/Q1", "O'Higgins", '"" OR NOT *']:
        res = store.search(hostile)
        assert isinstance(res, list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_catalog_fts5_search.py -v`
Expected: FAIL (`AttributeError: 'CatalogStore' object has no attribute 'rebuild_fts_index'`).

- [ ] **Step 3: Implement `indicators_fts` (`FTS5`), `rebuild_fts_index()`, and `BM25` + synonym-expanded `CatalogStore.search()`**

1. In `CatalogStore._init_db()`, create:
   ```sql
   CREATE VIRTUAL TABLE IF NOT EXISTS indicators_fts USING fts5(
       indicator_id UNINDEXED,
       name,
       subarea,
       area,
       theme,
       unit,
       member_labels,
       tokenize='unicode61 remove_diacritics 2'
   );
   ```
2. Implement `rebuild_fts_index(self) -> int` (and update single-indicator FTS row inside `store_indicator_dimensions` / `store_indicator_metadata` / `build`): populate `member_labels` by concatenating distinct non-structural (`not DEFAULT_FACET_ONTOLOGY.is_structural_dimension(d_id, d_name)`) member names per `indicator_id`.
3. Implement `_build_fts_match_query(query: str) -> str`:
   - Strip accents, extract `[a-z0-9]{2,}` tokens (ignoring Spanish stopwords `de, del, la, el, los, las, en, por, segun, para, con, sin, a, y, o` and 4-digit years), so hostile punctuation never reaches FTS5 syntax.
   - For each token, generate `(token* OR stem* OR syn1* ...)` using Spanish plural/gender stem + matching `Thesaurus` synset/domain terms (`desempleo <-> desocupacion`, `inflacion <-> precios consumidor ipc`, `pib <-> producto interno bruto`), joined with `AND` (falling back to `OR` when `AND` returns 0 rows).
   - Rank with `bm25(indicators_fts, 0.0, 10.0, 4.0, 3.0, 1.5, 2.0, 2.5)` (higher weight on `name` and `subarea`, breaking ties by `indicator_id ASC`, never `order_num ASC`).

- [ ] **Step 4: Run `FTS5` and catalog store tests**

Run: `uv run pytest tests/test_catalog_fts5_search.py tests/test_catalog_store.py tests/test_catalog_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/catalog/store.py tests/test_catalog_fts5_search.py tests/test_catalog_store.py
git commit -m "feat(catalog): upgrade CatalogStore.search to SQLite FTS5 BM25 with synonym and member indexing"
```

---

### Task 3: `GraphBuilder` & `FacetOntology` Hardening at 1,739-Indicator Scale

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/facet_ontology.py:160-215, 351-805`
- Modify: `src/unofficial_cepalstat_mcp/semantic/matcher.py:81-145, 210-230`
- Modify: `src/unofficial_cepalstat_mcp/semantic/graph_builder.py:76-415`
- Modify: `tests/test_semantic_graph_builder.py`
- Modify: `tests/test_semantic_facet_ontology.py`
- Modify: `tests/test_semantic_matcher.py`

**Interfaces:**
- Consumes: `CatalogStore.get_all_indicator_dimensions()`, `get_all_indicator_metadata()`, `get_all_relationships()`
- Produces:
  - `GraphBuilder.extract_name_stem(name: str) -> str` stripping trailing UN SDG series codes (`EN_ATM_GHGT_WLU`, `SL_TLF_UEM_19ICLS`) and unit parentheticals.
  - `GraphBuilder.extract_indicator_facets(...) -> set[str]` preserving unmapped non-structural dimensions as `"__raw_dim__:<norm_dim_name>"`.
  - Directed `breakdown_of` persistence (`parent -> child` only, never `child -> parent`) and single-pass bulk preloading (`0` per-pair SQLite connections).

- [ ] **Step 1: Write failing tests for Review Focus #2 and #3 (opaque unknown dimensions, SDG stem grouping, duplicate-title cross-area rejection, directed edges, and structural exclusion in `matcher.py`)**

Append to `tests/test_semantic_graph_builder.py` and `tests/test_semantic_matcher.py`:
```python
# In tests/test_semantic_graph_builder.py
def test_unmapped_dimension_does_not_become_false_parent_and_edges_are_directed(tmp_path) -> None:
    store = CatalogStore(db_path=tmp_path / "gb.db")
    with store._get_connection() as conn:
        conn.executemany(
            "INSERT INTO master_indicators VALUES (?, ?, 1, 'Sociales', 'Demográficos', '', 'Sociales > Demográficos', '2026-10-30')",
            [
                (9001, "Tasa de mortalidad, por causa de muerte"),
                (9002, "Tasa de mortalidad, por sexo"),
                (9003, "Tasa de mortalidad"),
                (9010, "Tasa de desempleo (%) SL_TLF_UEM"),
                (9011, "Tasa de desempleo, por sexo (%) SL_TLF_UEM_SEX"),
            ],
        )
    store.store_indicator_dimensions(9001, [Dimension(id=7001, name="Causa de muerte", members=[Member(id=1, name="Cardiovascular")])])
    store.store_indicator_dimensions(9002, [Dimension(id=144, name="Sexo__ESTANDAR", members=[Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")])])
    store.store_indicator_dimensions(9011, [Dimension(id=144, name="Sexo__ESTANDAR", members=[Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")])])
    report = GraphBuilder(store=store).build_breakdown_graph(persist=True, seed_curated=False)
    edges = {(e.parent_id, e.child_id) for e in report.inferred_edges}
    assert (9001, 9002) not in edges  # Cause of death is NOT parent of sex!
    assert (9003, 9002) in edges
    assert (9010, 9011) in edges      # Trailing SDG codes stripped!
    assert 9002 in store.get_relationships(9003)
    assert 9003 not in store.get_relationships(9002)  # Strictly directed parent -> child!


# In tests/test_semantic_matcher.py
def test_matcher_group_b_excludes_structural_country_and_year_dimensions() -> None:
    matcher = DynamicMemberMatcher()
    dims = [Dimension(id=208, name="País__ESTANDAR", members=[Member(id=1, name="Urbano")])]
    ok, matched, unhandled = matcher.match_facets_to_dimensions(3328, dims, {"area": "URBANO"})
    assert matched == []
    assert "area" in unhandled
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_graph_builder.py tests/test_semantic_matcher.py -v`
Expected: FAIL (`(9001, 9002)` falsely inferred, `(9010, 9011)` missed due to `SL_TLF_UEM`, `9003 in store.get_relationships(9002)` bidirectional, and `matcher` binds `País__ESTANDAR`).

- [ ] **Step 3: Harden `FacetOntology`, `DynamicMemberMatcher`, and `GraphBuilder`**

1. In `FacetOntology`:
   - Qualify bare single-word `dimension_name_patterns` (`"nivel"` -> `"nivel educativo"`, `"anos de estudio"`, `"anos de instruccion"`; `"sector"` -> `"sector de actividad"`, `"rama de actividad"`, `"actividad economica"`; `"unidad"` -> `"tipo de moneda"`, `"unidad monetaria"`), and add `subnacional` facet (`"division administrativa"`, `"municipio"`, `"ciudad"`, `"area sub nacional"`).
2. In `DynamicMemberMatcher.match_facets_to_dimensions()`: filter out `self.ontology.is_structural_dimension(d.id, d.name)` when constructing `candidate_dims_b`.
3. In `GraphBuilder`:
   - Strip trailing UN SDG codes (`re.sub(r"\s+[a-z]{2}(?:_[a-z0-9]+){2,}\s*$", "", text)`) and trailing parenthetical units (`re.sub(r"\s*\((?:en\s+|equivalente\s+|millones\s+|miles\s+|porcentaje|%|vatios|toneladas|dolares)[^)]*\)\s*$", "", text)`) in `extract_name_stem`.
   - Preload `all_dims = self.store.get_all_indicator_dimensions()`, `all_meta = self.store.get_all_indicator_metadata()`, `all_master = {r["indicator_id"]: r for r in self.store.get_all_master_indicators()}`, and `all_rels` **once** at the start of `build_breakdown_graph`.
   - When `self.ontology.classify_dimension(d.id, d.name)` returns `None`, add `f"__raw_dim__:{strip_accents(d.name)}"` to `facets` so unmapped dimensions are never treated as empty sets.
   - Require compatible `area` (when both rows exist in `master_indicators`) and compatible normalized `unit` (when both have non-empty units) in Guardrail 2.
   - Persist **only** `self.store.store_relationship(parent.indicator_id, child.indicator_id, "breakdown_of", provenance="inferred")` (remove the reverse `child -> parent` write).

- [ ] **Step 4: Run graph, ontology, matcher, and 200-benchmark tests**

Run: `uv run pytest tests/test_semantic_graph_builder.py tests/test_semantic_facet_ontology.py tests/test_semantic_matcher.py tests/test_semantic_benchmark_200.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/facet_ontology.py src/unofficial_cepalstat_mcp/semantic/matcher.py src/unofficial_cepalstat_mcp/semantic/graph_builder.py tests/test_semantic_graph_builder.py tests/test_semantic_facet_ontology.py tests/test_semantic_matcher.py
git commit -m "fix(semantic): harden GraphBuilder for 1739 indicators with directed edges and opaque dimensions"
```

---

### Task 4: Cold-Start Packaged Seed Snapshot (`seed_catalog.db.gz` + Bundled `bitacoras`) & Wheel Packaging

**Files:**
- Create: `src/unofficial_cepalstat_mcp/data/__init__.py`
- Create: `src/unofficial_cepalstat_mcp/catalog/seed.py`
- Modify: `src/unofficial_cepalstat_mcp/catalog/store.py:37-47`
- Modify: `src/unofficial_cepalstat_mcp/bitacora/store.py:14-40`
- Modify: `src/unofficial_cepalstat_mcp/cli.py:220-260, 575-620`
- Modify: `pyproject.toml:69-72`
- Create: `tests/test_cold_start_seed.py`
- Modify: `tests/test_packaging_metadata.py`

**Interfaces:**
- Consumes: `CatalogStore`, `BitacoraStore`, `GraphBuilder`
- Produces:
  - `export_seed_snapshot(source_db: Path, output_gz: Path | None = None, recipes_dir: Path | None = None) -> Path` in `unofficial_cepalstat_mcp.catalog.seed` (pruning structural Country/Year rows from `dimension_members` to keep the compressed seed `< 400 KB`, rebuilding `indicators_fts`, syncing `recipes`, running `VACUUM`, and gzipping with `mtime=0`).
  - `ensure_seed_hydrated(target_db: Path) -> bool` in `unofficial_cepalstat_mcp.catalog.seed` (atomically decompressing `seed_catalog.db.gz` to `f"{target_db}.{os.getpid()}.tmp"` + `os.replace` only when `target_db` does not yet exist and `target_db == get_cache_db_path()`).
  - `CatalogStore.__init__(..., auto_seed: bool | None = None)` (`True` by default when `db_path is None`, `False` when explicit `db_path` is passed in unit tests unless opted in).
  - `BitacoraStore.__init__` without unconditional `mkdir` on `./bitacoras` (creating directory only inside `save_recipe()`).

- [ ] **Step 1: Write failing tests for Review Focus #5 (atomic cold-start seed hydration, zero CWD `bitacoras/` side effect, and wheel artifact inclusion)**

Create `tests/test_cold_start_seed.py`:
```python
import time
from pathlib import Path

from unofficial_cepalstat_mcp.bitacora.store import BitacoraStore
from unofficial_cepalstat_mcp.catalog.seed import ensure_seed_hydrated
from unofficial_cepalstat_mcp.catalog.store import CatalogStore


def test_cold_start_hydrates_default_cache_under_50ms_with_1739_indicators_and_recipes(
    tmp_path: Path, monkeypatch
) -> None:
    cache_db = tmp_path / "cold_cache" / ".statscepal_cache.db"
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(cache_db))
    t0 = time.perf_counter()
    store = CatalogStore()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert cache_db.exists()
    assert elapsed_ms < 150.0  # <50ms warm disk, generous CI ceiling
    assert store.get_stats().total_indicators >= 1700
    assert len(store.search("pobreza")) > 0

    cwd_dir = tmp_path / "readonly_cwd"
    cwd_dir.mkdir()
    monkeypatch.chdir(cwd_dir)
    b_store = BitacoraStore()
    assert not (cwd_dir / "bitacoras").exists()
    assert len(b_store.list_all()) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cold_start_seed.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'unofficial_cepalstat_mcp.catalog.seed'`).

- [ ] **Step 3: Implement `catalog/seed.py`, generate `src/unofficial_cepalstat_mcp/data/seed_catalog.db.gz`, fix `BitacoraStore.__init__`, and configure `pyproject.toml`**

1. Implement `export_seed_snapshot` and `ensure_seed_hydrated` in `src/unofficial_cepalstat_mcp/catalog/seed.py`:
   - `export_seed_snapshot` copies `master_indicators`, `VERTICAL_SLICE_INDICATORS` curated metadata/dimensions/relationships, `GraphBuilder.build_breakdown_graph(persist=True)` edges, `BitacoraStore.sync_from_disk()` recipes, and `rebuild_fts_index()` into a clean SQLite file, runs `VACUUM`, and writes deterministic `gzip.GzipFile(..., mtime=0)` to `src/unofficial_cepalstat_mcp/data/seed_catalog.db.gz`.
   - `ensure_seed_hydrated(target_db)` checks `not target_db.exists()`, reads `seed_catalog.db.gz` via `importlib.resources.files("unofficial_cepalstat_mcp.data")`, writes to `target_db.with_suffix(f".{os.getpid()}.tmp")`, calls `os.replace(tmp, target_db)`, and returns `True`.
2. In `CatalogStore.__init__`: when `auto_seed` is `True` (or `auto_seed is None and db_path is None`), call `ensure_seed_hydrated(self.db_path)` before `self._init_db()`.
3. In `BitacoraStore.__init__`: call `ensure_seed_hydrated(self.db_path)` when `db_path is None`, and move `self.base_dir.mkdir(parents=True, exist_ok=True)` out of `__init__` into any write/export method so read-only MCP startup creates zero directories in CWD.
4. Add `catalog export-seed` subcommand to `cli.py`, generate `src/unofficial_cepalstat_mcp/data/seed_catalog.db.gz` from `.statscepal_cache.db` + `bitacoras/`, verify `[tool.hatch.build.targets.wheel]` includes `src/unofficial_cepalstat_mcp/data/seed_catalog.db.gz`, and add a wheel-inspection assertion in `tests/test_packaging_metadata.py`.

- [ ] **Step 4: Run cold-start, packaging, wheel build, `mypy`, and full offline test suite**

Run: `uv build && uv run ruff check . && uv run mypy src/unofficial_cepalstat_mcp/ && uv run pytest -m "not integration" -q`
Expected: Wheel builds with `seed_catalog.db.gz` included, `0` `mypy` errors, all offline tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/unofficial_cepalstat_mcp/data/ src/unofficial_cepalstat_mcp/catalog/ src/unofficial_cepalstat_mcp/bitacora/store.py src/unofficial_cepalstat_mcp/cli.py tests/test_cold_start_seed.py tests/test_packaging_metadata.py
git commit -m "feat(catalog): bundle compressed cold-start SQLite seed snapshot in wheel"
```
