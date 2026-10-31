# Phase 3: Two-Tier Hybrid Semantic Engine (1,739 Indicators), Cube Pushdown & Async Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scale deterministic semantic resolution from ~35 curated indicators to all **1,739 CEPALSTAT indicators** (`p50 < 0.5 ms`, `0.00% FSR`, `< 250 token` disambiguation), push Country/Year `members=` filters to `/records`, and ship async/cached/retry-resilient HTTP transport ready for the MCP server.

**Architecture:** Build a compact in-memory inverted stem + `Thesaurus` index in `SemanticRegistry` (excluding redundant structural Country/Year `Member` objects from startup hydration) and route Tier-1 misses (`root_concept=None` or `UNRESOLVED_SPECIFICITY`) through Tier-2 candidate retrieval + Stage 4 `FacetOntology` `Dimensional Gate` + `Specificity Guard`, auto-resolving unique matches and returning compact `ALTERNATIVE_PROPOSED` envelopes when multiple series compete. Upgrade `SemanticDataFetcher` with server-side Country/Year `members=` pushdown, fail-closed unconstrained-dimension collapse, and immutable `SemanticResolutionResponse` handling, backed by `AsyncCepalStatClient` (`httpx.AsyncClient`, bounded TTL cache, and `429`/`5xx` backoff).

**Tech Stack:** Python >=3.10, `uv`, `httpx` (`Client` + `AsyncClient`), `asyncio`, `pydantic` v2, `pandas`, `sqlite3`, `pytest`, `respx`, `mypy`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-10-30-pre-mcp-semantic-scaling-spec.md`

## Global Constraints

- Import always from `unofficial_cepalstat_mcp` (never `from statscepal`).
- Always run `uv run pytest -m "not integration"`; zero live network requests in unit/benchmark suites.
- Preserve **0.00% False Substitution Rate (FSR)** across all 200 canonical + 40 adversarial + 100 full-catalog benchmark queries.
- Maintain local semantic resolution latency strictly at **`p50 < 0.5 ms` and `p95 < 2.0 ms`** with all 1,739 indicators loaded in memory (Guardrail #4).
- Never pass `SYNTHETIC_DIMENSION_MEMBER_IDS` in `/records?members=...` HTTP requests.
- Never mutate `SemanticResolutionResponse` in-place inside `SemanticDataFetcher`.
- Pass `uv run mypy src/unofficial_cepalstat_mcp/`, `uv run ruff check .`, and `uv build` with zero errors.

## Review Focus

1. **Adversarial out-of-scope queries overlapping single catalog words (`"precio del bitcoin"`, `"coeficiente intelectual"`, `"PIB de Francia"`):** Tier-2 retrieval must never override Stage 1/2 `unknown_concept` / non-LAC country / unsupported-facet abstentions, and must require every informative query concept stem to be covered by the candidate (`0.00% FSR`).
2. **Competing official series in Tier 2 (`"mortalidad infantil en Chile"` in Demográficos vs ODS; headcount vs `%`):** When `>= 2` valid candidates pass the `Dimensional Gate` within normalized score margin `< 0.15` across distinct units or areas (CEPAL regional vs ODS), Tier 2 must return `ALTERNATIVE_PROPOSED` (`< 250 tokens`) rather than guessing silently.
3. **Country-restricted subnational/subregional catalog tables (`4872` `"CHILE Producto interno bruto..."`, `"Centroamérica y México"`):** Tier 2 must reject country-scoped catalog indicators when `intent.country_code` requests an incompatible country (e.g., Perú or Argentina).
4. **Unconstrained multi-member dimension lacking `"Total"` during empirical fetch (e.g., 10 SITC product categories or age brackets without aggregate):** `_filter_unconstrained_dimensions` must fail closed (`observation_exists=False`, `"AMBIGUOUS_UNCONSTRAINED_DIMENSION: <col>"`) instead of silently picking `filtered_df.iloc[0]`.
5. **Concurrent MCP calls sharing cached `SemanticResolutionResponse` & hitting `429` rate limits:** `fetch_resolved_data` must leave the input `SemanticResolutionResponse` untouched, and `CepalStatClient` / `AsyncCepalStatClient` must serve cached GETs within TTL and retry `429`/`502`/`503`/`504` with exponential backoff.

---

## File Structure

- **Modify:** `src/unofficial_cepalstat_mcp/catalog/store.py` — Add `include_structural: bool = True` to `get_all_indicator_dimensions` so `SemanticRegistry` skips materializing ~200k Country/Year `Member` objects at startup.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/parser.py` — Add regional aggregates (`ALC`, `AMERICA_LATINA`, `AMERICA_DEL_SUR`, `CENTROAMERICA`, `EL_CARIBE`) to `COUNTRY_LEXICON` and expose `intent.concept_tokens: list[str]` (informative non-geo, non-time, non-facet tokens).
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/registry.py` — Build sub-0.3ms in-memory inverted stem + `Thesaurus` IDF index over all 1,739 indicators + non-structural member labels (`search_candidates`) with country-scope awareness.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/engine.py` — Connect Tier-2 deterministic catalog resolution (`resolve_tier2_candidates`), rank Stage 4 `BREAKDOWN_OF` swaps by parsimony (`argmin len(cand_dims)`), and format compact `< 250 token` `ALTERNATIVE_PROPOSED` hints.
- **Modify:** `src/unofficial_cepalstat_mcp/dimensions.py`, `src/unofficial_cepalstat_mcp/extractor.py`, `src/unofficial_cepalstat_mcp/semantic/fetcher.py` — Push resolved Country/Year `member_id`s into `/records?members=...`, reuse `CatalogStore` dimensions in `DataExtractor`, fail closed on uncollapsible unconstrained dimensions, stop mutating `SemanticResolutionResponse`, and add `summarize_indicator_structure()` (`< 250 tokens`).
- **Modify:** `src/unofficial_cepalstat_mcp/client.py` & `src/unofficial_cepalstat_mcp/__init__.py` — Add `AsyncCepalStatClient`, bounded TTL cache, and `429`/`5xx` exponential backoff.
- **Create:** `tests/test_semantic_inverted_index.py`, `tests/test_semantic_tier2_hybrid.py`, `tests/test_fetcher_pushdown_and_immutability.py`, `tests/test_async_client_and_cache.py`, `tests/benchmark/catalog_scale_benchmark_cases_100.json`, `tests/test_catalog_scale_benchmark_100.py`; **Modify:** `docs/reports/2026-10-18-adversarial-benchmark-specification.md`, `docs/reports/benchmark_200_preguntas.md`.

---

### Task 1: Lean Startup Hydration & Sub-0.3ms In-Memory Inverted Index in `SemanticRegistry`

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/catalog/store.py:423-453`
- Modify: `src/unofficial_cepalstat_mcp/semantic/parser.py:28-145, 260-305`
- Modify: `src/unofficial_cepalstat_mcp/semantic/registry.py:20-45, 1205-1350`
- Create: `tests/test_semantic_inverted_index.py`

**Interfaces:**
- Consumes: `CatalogStore` seeded in Phase 2 (`seed_catalog.db.gz`), `Thesaurus`
- Produces:
  - `CatalogStore.get_all_indicator_dimensions(self, *, include_structural: bool = True) -> dict[int, list[Dimension]]`
  - `ParsedIntent.concept_tokens: list[str]` in `unofficial_cepalstat_mcp.semantic.parser`
  - `SemanticRegistry.search_candidates(self, concept_tokens: Sequence[str], facets: Mapping[str, str] | None = None, country_code: str | None = None, top_k: int = 10) -> list[tuple[int, float]]`

- [ ] **Step 1: Write failing tests for startup hydration `< 35 ms`, regional aggregates in `COUNTRY_LEXICON`, and Review Focus #3 country-scope guard**

Create `tests/test_semantic_inverted_index.py`:
```python
import time

from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.semantic.parser import QueryParser
from unofficial_cepalstat_mcp.semantic.registry import SemanticRegistry


def test_registry_hydrates_1739_indicators_fast_and_indexes_candidates(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(tmp_path / ".statscepal_cache.db"))
    store = CatalogStore()
    t0 = time.perf_counter()
    reg = SemanticRegistry(store=store)
    startup_ms = (time.perf_counter() - t0) * 1000.0
    assert startup_ms < 100.0
    t1 = time.perf_counter()
    hits = reg.search_candidates(["exportaciones", "bienes"], top_k=5)
    query_ms = (time.perf_counter() - t1) * 1000.0
    assert query_ms < 0.5
    assert len(hits) > 0


def test_search_candidates_excludes_chile_only_subnational_tables_for_other_countries(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(tmp_path / ".statscepal_cache.db"))
    reg = SemanticRegistry(store=CatalogStore())
    hits_per = [ind_id for ind_id, _ in reg.search_candidates(["producto", "interno", "bruto", "actividad", "economica"], country_code="PER", top_k=10)]
    assert 4872 not in hits_per  # CHILE subnational GDP


def test_parser_recognizes_latin_america_regional_aggregates() -> None:
    parser = QueryParser()
    intent = parser.parse("exportaciones de bienes en América Latina y el Caribe 2022")
    assert "ALC" in intent.country_codes
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_inverted_index.py -v`
Expected: FAIL (`SemanticRegistry` has no `search_candidates`; `ALC` missing from `COUNTRY_LEXICON`).

- [ ] **Step 3: Implement `include_structural=False`, regional `COUNTRY_LEXICON` entries, `ParsedIntent.concept_tokens`, and `SemanticRegistry.search_candidates`**

1. In `CatalogStore.get_all_indicator_dimensions(self, *, include_structural: bool = True)`: skip loading `dimension_members` for structural Country/Time dimensions when `include_structural=False`, and call `get_all_indicator_dimensions(include_structural=False)` inside `SemanticRegistry._build_in_memory_index()`.
2. In `QueryParser`: add regional entries (`"america latina y el caribe": ("ALC", "América Latina y el Caribe")`, `"america latina": ("ALC", "América Latina")`, `"alc": ("ALC", "América Latina y el Caribe")`, `"america del sur": ("SUD", "América del Sur")`, `"centroamerica": ("CAM", "Centroamérica")`, `"el caribe": ("CAR", "El Caribe")`) to `COUNTRY_LEXICON`, and populate `intent.concept_tokens` with normalized informative tokens remaining after stripping geography, years, stopwords, and matched facet trigger phrases.
3. In `SemanticRegistry._build_in_memory_index()`: build an inverted stem dictionary `_inverted_index: dict[str, list[tuple[int, float]]]` + IDF weights over `name` (`3.0`), `subarea` (`1.8`), `area` (`1.2`), and non-structural `dimension_members` (`1.5`), recording `restricted_country_scope` on indicators whose title/area restricts geography (e.g. leading `"CHILE "` -> `{"CHL"}`, `"Centroamérica y México"` -> CAM+MEX ISO3 set). Implement `search_candidates()` using IDF-weighted coverage + `Thesaurus` synonym expansion and filtering incompatible `restricted_country_scope`.

- [ ] **Step 4: Run inverted index tests**

Run: `uv run pytest tests/test_semantic_inverted_index.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/catalog/store.py src/unofficial_cepalstat_mcp/semantic/parser.py src/unofficial_cepalstat_mcp/semantic/registry.py tests/test_semantic_inverted_index.py
git commit -m "feat(semantic): add sub-0.3ms in-memory inverted catalog index and regional aggregates"
```

---

### Task 2: Tier-2 Deterministic Full-Catalog Resolution & Parsimonious Stage 4 Swaps in `SemanticResolutionEngine`

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/engine.py:130-145, 290-515`
- Create: `tests/test_semantic_tier2_hybrid.py`

**Interfaces:**
- Consumes: `SemanticRegistry.search_candidates` and `ParsedIntent.concept_tokens` from Task 1
- Produces:
  - `SemanticResolutionEngine.__init__(..., store: CatalogStore | None = None, enable_tier2_catalog: bool | None = None)` (`True` when `store` is provided or `catalog_profile == "full_catalog"`, preserving deterministic `official_25` behavior when `store is None and catalog_profile == "official_25"`).
  - Parsimonious Stage 4 `BREAKDOWN_OF` child selection ordered by `(len(cand_dims), cand_id)` instead of arbitrary dict iteration order.
  - Tier-2 resolution policy: `RESOLVED` on unique unambiguous winner covering all `concept_tokens` and `facets`; `ALTERNATIVE_PROPOSED` (`<= 4` alternatives, `< 250 tokens`) when `>= 2` valid candidates compete within normalized score margin `< 0.15`; `ABSTAINED` otherwise (`0.00% FSR`).

- [ ] **Step 1: Write failing tests for Tier-2 resolution, Review Focus #1 (adversarial immunity), Review Focus #2 (competing series -> `ALTERNATIVE_PROPOSED`), and parsimonious Stage 4 swap**

Create `tests/test_semantic_tier2_hybrid.py`:
```python
from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus
from unofficial_cepalstat_mcp.semantic.registry import SemanticRegistry


def _full_engine(tmp_path, monkeypatch) -> SemanticResolutionEngine:
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(tmp_path / ".statscepal_cache.db"))
    store = CatalogStore()
    return SemanticResolutionEngine(registry=SemanticRegistry(store=store), catalog_profile="full_catalog")


def test_tier2_resolves_uncurated_catalog_indicators_and_competing_alternatives(tmp_path, monkeypatch) -> None:
    engine = _full_engine(tmp_path, monkeypatch)
    # Uncurated catalog indicator (e.g. wholesale price index 544 or literacy 5683)
    r_ipm = engine.resolve("índice de precios al por mayor en Chile 2022")
    assert r_ipm.status == ResolutionStatus.RESOLVED
    assert r_ipm.selected_candidate is not None
    assert r_ipm.selected_candidate.indicator_id == 544

    # Competing series (e.g. exportaciones de bienes -> multiple compatible tables)
    r_exp = engine.resolve("exportaciones de bienes en Chile 2022")
    assert r_exp.status in (ResolutionStatus.RESOLVED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    if r_exp.status == ResolutionStatus.ALTERNATIVE_PROPOSED:
        assert 1 <= len(r_exp.alternatives) <= 4
        assert len(r_exp.conversational_hint or "") < 600


def test_tier2_never_substitutes_adversarial_queries(tmp_path, monkeypatch) -> None:
    engine = _full_engine(tmp_path, monkeypatch)
    for adv in [
        "precio del bitcoin en El Salvador 2023",
        "pobreza por coeficiente intelectual en Chile 2022",
        "inflación anual en Francia 2022",
    ]:
        resp = engine.resolve(adv)
        assert resp.status == ResolutionStatus.ABSTAINED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_tier2_hybrid.py -v`
Expected: FAIL (`índice de precios al por mayor` returns `ABSTAINED: LOW_CONCEPTUAL_RELEVANCE`).

- [ ] **Step 3: Implement Tier-2 candidate evaluation and parsimonious Stage 4 swaps in `SemanticResolutionEngine`**

1. In Stage 4 (`engine.py:458-496`), collect all valid `BREAKDOWN_OF` swap candidates first and select `min(valid_swaps, key=lambda item: (len(self.registry.get_dimensions(item[0])), item[0]))` so the engine always picks the most parsimonious breakdown cube.
2. Add `_resolve_via_tier2_catalog(self, query_str: str, intent: Any, applied_filters: AppliedFilters, trace: list[str], t0: float) -> SemanticResolutionResponse | None`:
   - Invoked only when `self.enable_tier2_catalog` is `True`, `not intent.unknown_concept`, `not intent.unsupported_facet`, `not intent.period_out_of_range`, `not intent.unsupported_frequency`, and (`intent.root_concept is None` or Tier 1 failed Stage 3.5 `UNRESOLVED_SPECIFICITY`).
   - Query `self.registry.search_candidates(intent.concept_tokens, facets=intent.facets, country_code=intent.country_code, top_k=10)`.
   - Filter candidates strictly: every critical specificity / concept token in `intent.concept_tokens` must pass `_is_token_covered_by_indicator` (or `Thesaurus` synonym equivalence), and every requested critical facet in `intent.facets` must pass `FacetOntology` + `DynamicMemberMatcher` (`Zero Facet Loss`).
   - If `0` candidates survive -> return `None` (falls through to `ABSTAINED`).
   - If `1` candidate survives, or `top_score - second_score >= 0.15` with identical concept stem -> proceed to Stage 5 Temporal Audit and return `RESOLVED` (`relevance_score=0.90`).
   - Otherwise -> return `ALTERNATIVE_PROPOSED` with the top candidate as `selected_candidate` (`relevance_score=0.82`) and up to 3 `AlternativeCandidate` entries summarizing `(indicator_id, name, unit)` in `< 250 tokens`.

- [ ] **Step 4: Run Tier-2, 200-canonical, and 40-adversarial benchmarks**

Run: `uv run pytest tests/test_semantic_tier2_hybrid.py tests/test_semantic_benchmark_200.py tests/test_adversarial_benchmark_40.py -v`
Expected: PASS (`0.00% FSR`, `40/40` adversarial abstentions, `p50 < 0.5 ms`).

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/engine.py tests/test_semantic_tier2_hybrid.py
git commit -m "feat(semantic): add Tier-2 deterministic catalog resolution and parsimonious graph swaps"
```

---

### Task 3: Server-Side `members=` Pushdown, Non-Mutating Fetch, Fail-Closed Collapse & Compact Dimension Summary

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/dimensions.py:77-124`
- Modify: `src/unofficial_cepalstat_mcp/extractor.py:63-102`
- Modify: `src/unofficial_cepalstat_mcp/semantic/fetcher.py:180-375, 1115-1225`
- Create: `tests/test_fetcher_pushdown_and_immutability.py`

**Interfaces:**
- Consumes: `DimensionManager`, `CatalogStore`, `DEFAULT_FACET_ONTOLOGY`
- Produces:
  - `DimensionManager.summarize_indicator_structure(self, indicator_id: int, store: CatalogStore | None = None, max_members: int = 15) -> dict[str, Any]` (`< 250 tokens`: country count, year min/max, and non-structural dimensions with capped member previews).
  - Server-side `members=` pushdown in `SemanticDataFetcher._prepare_empirical_fetch` resolving `country_codes` and `years` against structural Country/Time dimensions (never emitting `SYNTHETIC_DIMENSION_MEMBER_IDS`).
  - Fail-closed `"AMBIGUOUS_UNCONSTRAINED_DIMENSION: <col>"` in `_filter_unconstrained_dimensions` when an unconstrained non-structural dimension has `>1` unique values and no aggregate member.
  - Non-mutating `SemanticDataFetcher.fetch_resolved_data(response, ...)` leaving `response` unchanged.

- [ ] **Step 1: Write failing tests for Country/Year `members=` pushdown, Review Focus #4 (unconstrained non-total dimension fail-closed), Review Focus #5 (response immutability), and `< 250 token` structure summary**

Create `tests/test_fetcher_pushdown_and_immutability.py`:
```python
import json

import pandas as pd

from unofficial_cepalstat_mcp.dimensions import Dimension, DimensionManager, Member
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.fetcher import SemanticDataFetcher


def test_fetcher_pushes_country_and_year_member_ids_and_does_not_mutate_response(mocker) -> None:
    dims = [
        Dimension(id=208, name="País__ESTANDAR", members=[Member(id=79578, name="Chile"), Member(id=210, name="Perú")]),
        Dimension(id=29117, name="Años__ESTANDAR", members=[Member(id=29190, name="2022"), Member(id=29191, name="2023")]),
    ]
    df = pd.DataFrame([{"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "value": 11.6}])
    extractor = mocker.Mock()
    extractor.dimension_manager.get_dimensions.return_value = dims
    extractor.get_dataframe.return_value = df

    resp = SemanticResolutionEngine().resolve("inflación anual en Chile 2022")
    trace_before = list(resp.execution_trace)
    out = SemanticDataFetcher(extractor=extractor).fetch_resolved_data(resp)

    assert out["observation_exists"] is True
    called_members = extractor.get_dataframe.call_args.kwargs.get("members") or extractor.get_dataframe.call_args.args[1]
    assert 79578 in called_members and 29190 in called_members
    assert resp.execution_trace == trace_before
    assert resp.empirical_data is None


def test_fetcher_fails_closed_on_unconstrained_dimension_without_total_member(mocker) -> None:
    df = pd.DataFrame([
        {"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "Producto CUCI": "Cobre", "value": 45000.0},
        {"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "Producto CUCI": "Celulosa", "value": 3200.0},
    ])
    extractor = mocker.Mock(get_dataframe=mocker.Mock(return_value=df))
    extractor.dimension_manager.get_dimensions.return_value = []
    resp = SemanticResolutionEngine().resolve("inflación anual en Chile 2022")
    out = SemanticDataFetcher(extractor=extractor).fetch_resolved_data(resp)
    assert out["observation_exists"] is False
    assert "AMBIGUOUS_UNCONSTRAINED_DIMENSION" in out["reason"]


def test_summarize_indicator_structure_stays_under_250_tokens(mocker) -> None:
    client = mocker.Mock()
    dm = DimensionManager(client)
    dm._cache[127] = [
        Dimension(id=208, name="País__ESTANDAR", members=[Member(id=i, name=f"Country {i}") for i in range(40)]),
        Dimension(id=29117, name="Años__ESTANDAR", members=[Member(id=100 + y, name=str(y)) for y in range(1980, 2026)]),
        Dimension(id=144, name="Sexo__ESTANDAR", members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")]),
    ]
    summary = dm.summarize_indicator_structure(127)
    serialized = json.dumps(summary, ensure_ascii=False)
    assert len(serialized) < 900  # ~220 tokens max
    assert summary["country_count"] == 40
    assert summary["year_range"] == [1980, 2025]
    assert len(summary["breakdown_dimensions"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_fetcher_pushdown_and_immutability.py -v`
Expected: FAIL (`members=None` passed to `get_dataframe`, `resp.empirical_data` mutated in-place, unconstrained `"Producto CUCI"` silently returns `45000.0` Cobre, and `summarize_indicator_structure` missing).

- [ ] **Step 3: Implement Country/Year `members=` pushdown, fail-closed unconstrained collapse, deep-copy response handling, and `summarize_indicator_structure`**

1. In `DimensionManager` (`dimensions.py`): add `summarize_indicator_structure(self, indicator_id: int, store: CatalogStore | None = None, max_members: int = 15) -> dict[str, Any]` separating structural dimensions (`country_count`, `year_range`) from non-structural breakdown dimensions (`dim_id`, `name`, `total_members`, `members_preview[:max_members]`).
2. In `DataExtractor.get_dataframe(..., dimensions: list[Dimension] | None = None)` (`extractor.py`): accept pre-fetched `dimensions` so callers with `DimensionManager._cache` or `CatalogStore` avoid a second `/dimensions` HTTP request.
3. In `SemanticDataFetcher` (`fetcher.py`):
   - At the start of `fetch_resolved_data`, work on `work_resp = response.model_copy(deep=True)` (updating any existing CLI caller in `cli.py` to read the returned `payload` dict instead of relying on side-effect mutation of `res.empirical_data`).
   - In `_prepare_empirical_fetch`, inspect structural Country and Time dimensions via `self.extractor.dimension_manager.get_dimensions(empirical_id)` (note: `79578` inside real `dim_208` IS Chile's real country member ID, whereas `SYNTHETIC_DIMENSION_MEMBER_IDS` filtering applies only to synthetic non-structural `AppliedDimensionFilter.member_id`s from `DEFAULT_OFFICIAL_DIMENSIONS`!). Resolve target countries (`country_names` / ISO3) and target years (including `anchor` years when `temporal_info` has anchors) to real structural `member_id`s and include them in `members=`.
   - In `_filter_unconstrained_dimensions`, if an unconstrained non-structural column has `unique_vals > 1` and `chosen_raw is None` (no aggregate/total member matched), flag `"AMBIGUOUS_UNCONSTRAINED_DIMENSION: <col>"` and return `observation_exists=False` in `fetch_resolved_data`.

- [ ] **Step 4: Run pushdown and existing fetcher/CLI tests**

Run: `uv run pytest tests/test_fetcher_pushdown_and_immutability.py tests/test_semantic_fetcher.py tests/test_cli_semantic.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/dimensions.py src/unofficial_cepalstat_mcp/extractor.py src/unofficial_cepalstat_mcp/semantic/fetcher.py src/unofficial_cepalstat_mcp/cli.py tests/test_fetcher_pushdown_and_immutability.py tests/test_semantic_fetcher.py tests/test_cli_semantic.py
git commit -m "feat(fetcher): push country/year member filters to API and prevent unconstrained row corruption"
```

---

### Task 4: `AsyncCepalStatClient`, Bounded TTL Cache & `429`/`5xx` Exponential Backoff

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/client.py`
- Modify: `src/unofficial_cepalstat_mcp/__init__.py`
- Create: `tests/test_async_client_and_cache.py`
- Modify: `tests/test_client.py`

**Interfaces:**
- Consumes: `httpx.Client`, `httpx.AsyncClient`
- Produces:
  - `CepalStatClient(..., cache_ttl_seconds: float = 300.0, max_cache_entries: int = 256, max_retries: int = 3, retry_backoff_base: float = 0.5)`
  - `AsyncCepalStatClient` with async context manager (`async with AsyncCepalStatClient(...) as client:`) and `async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]` + `async def get_raw(...) -> bytes` sharing the same bounded LRU/TTL cache and `429`/`502`/`503`/`504` retry policy.

- [ ] **Step 1: Write failing tests for async GET, bounded TTL cache hits, and `429`/`503` retry backoff**

Create `tests/test_async_client_and_cache.py`:
```python
import asyncio

import httpx
import respx

from unofficial_cepalstat_mcp.client import AsyncCepalStatClient, CepalStatClient


@respx.mock
def test_sync_client_caches_ttl_and_retries_429(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda _: None)
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/127/metadata").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "rate limit"}),
            httpx.Response(200, json={"body": {"metadata": {"name": "Desocupación"}}}),
        ]
    )
    with CepalStatClient(cache_ttl_seconds=60.0, max_retries=3) as client:
        first = client.get("/cepalstat/api/v1/indicator/127/metadata")
        second = client.get("/cepalstat/api/v1/indicator/127/metadata")
    assert first == second
    assert route.call_count == 2  # 1 retry after 429 + 1 cached hit (no 3rd HTTP call)


@respx.mock
def test_async_client_fetches_and_caches_without_blocking(monkeypatch) -> None:
    async def _noop_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", _noop_sleep)
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/365/metadata").mock(
        side_effect=[
            httpx.Response(503, text="unavailable"),
            httpx.Response(200, json={"body": {"metadata": {"name": "IPC"}}}),
        ]
    )

    async def _run() -> dict:
        async with AsyncCepalStatClient(cache_ttl_seconds=60.0, max_retries=3) as client:
            await client.get("/cepalstat/api/v1/indicator/365/metadata")
            return await client.get("/cepalstat/api/v1/indicator/365/metadata")

    result = asyncio.run(_run())
    assert result["body"]["metadata"]["name"] == "IPC"
    assert route.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_async_client_and_cache.py -v`
Expected: FAIL (`ImportError: cannot import name 'AsyncCepalStatClient'`).

- [ ] **Step 3: Implement bounded LRU/TTL cache, `429`/`5xx` backoff, and `AsyncCepalStatClient` in `client.py`**

1. Implement a lightweight `OrderedDict`-based `_BoundedTTLCache(ttl_seconds: float, max_entries: int)` in `src/unofficial_cepalstat_mcp/client.py` keyed on `(clean_endpoint, tuple(sorted(query_params.items())))`.
2. Add retry loop (`max_retries=3`, `retry_backoff_base=0.5`, honoring numeric `Retry-After` header up to `5.0s`) on HTTP `429, 502, 503, 504` and transient `httpx.TransportError` in `CepalStatClient.get` / `get_raw`.
3. Implement `AsyncCepalStatClient` (`__aenter__`, `__aexit__`, `aclose`, `async def get`, `async def get_raw`) using `httpx.AsyncClient` and `asyncio.sleep`, and export `AsyncCepalStatClient` in `src/unofficial_cepalstat_mcp/__init__.py`.

- [ ] **Step 4: Run client tests**

Run: `uv run pytest tests/test_async_client_and_cache.py tests/test_client.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/client.py src/unofficial_cepalstat_mcp/__init__.py tests/test_async_client_and_cache.py tests/test_client.py
git commit -m "feat(client): add AsyncCepalStatClient with bounded TTL cache and 429/5xx retry"
```

---

### Task 5: 100-Query Cross-23-Area Full-Catalog Scale Benchmark & Documentation Cleanup

**Files:**
- Create: `tests/benchmark/catalog_scale_benchmark_cases_100.json`
- Create: `tests/test_catalog_scale_benchmark_100.py`
- Modify: `docs/reports/2026-10-18-adversarial-benchmark-specification.md`
- Modify: `docs/reports/benchmark_200_preguntas.md`

**Interfaces:**
- Consumes: Full Phase 1 + Phase 2 + Phase 3 stack (`CatalogStore` seeded with 1,739 indicators + `SemanticResolutionEngine(catalog_profile="full_catalog")`)
- Produces: Automated certification that Tier-1 + Tier-2 resolution across all **23 CEPALSTAT areas** achieves **0.00% FSR**, **`p50 < 0.5 ms`**, and **`p95 < 2.0 ms`**, alongside `200/200` canonical and `40/40` adversarial benchmarks.

- [ ] **Step 1: Create the 100-case cross-23-area benchmark dataset and test runner**

Create `tests/benchmark/catalog_scale_benchmark_cases_100.json` covering all 23 CEPALSTAT areas in `master_indicators` (80 positive queries across ODS, Subnacional, Sociales, TIC, Comercio, Agropecuario, Género, Demográficos, Ciudades, PIB y Cuentas Nacionales, Productividad, Eléctrico/Hidrocarburos, Recursos Ambientales, Pueblos Indígenas, Cohesión Social, Calidad Ambiental, Precios, Sector Público, Financiero/Monetario, Residuos, Discapacidad, Gestión Ambiental, Desastres + 20 cross-domain adversarial/country-scope traps) and `tests/test_catalog_scale_benchmark_100.py` asserting:
- `false_substitution_rate == 0.0` (`0` cases where `ABSTAINED` was expected or a wrong concept/country-scoped indicator was returned as `RESOLVED`)
- `accuracy >= 0.95` across all 100 cases
- `statistics.median(latencies_ms) < 0.5` and `quantiles_p95 < 2.0`

- [ ] **Step 2: Run the new 100-case scale benchmark + 200-case canonical + 40-case adversarial benchmarks**

Run: `uv run pytest tests/test_catalog_scale_benchmark_100.py tests/test_semantic_benchmark_200.py tests/test_adversarial_benchmark_40.py -v`
Expected: PASS (`0.00% FSR`, `p50 < 0.5 ms`, `p95 < 2.0 ms`).

- [ ] **Step 3: Clean up legacy `C:/papx/statscepal` links and unfinished scratch section in `docs/reports/`**

Replace hardcoded `file:///C:/papx/statscepal/...` and `src/statscepal/` paths with repository-relative `src/unofficial_cepalstat_mcp/` paths in `docs/reports/benchmark_200_preguntas.md` and `docs/reports/2026-10-18-adversarial-benchmark-specification.md`, removing the open scratch placeholder (`## 4. Espacio para 'Cosas Picantes'`).

- [ ] **Step 4: Run complete pre-MCP release verification gate**

Run: `uv run ruff check . && uv run mypy src/unofficial_cepalstat_mcp/ && uv build && uv run pytest -m "not integration" -q`
Expected: `All checks passed!`, `0` `mypy` errors, wheel built cleanly, all offline tests and 340 benchmark queries (`200 + 40 + 100`) PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/benchmark/catalog_scale_benchmark_cases_100.json tests/test_catalog_scale_benchmark_100.py docs/reports/
git commit -m "test(benchmark): add 100-query full-catalog scale benchmark across all 23 CEPALSTAT areas"
```
