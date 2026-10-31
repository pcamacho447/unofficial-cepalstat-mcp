# Phase 1: Canonical CEPALSTAT IDs, Fail-Closed Fetch Binding & Type Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate all synthetic/colliding indicator IDs in the semantic layer, enforce fail-closed `FacetOntology` column binding during empirical data extraction, run specificity checks before ambiguity shortcuts, and achieve zero `mypy` errors across `src/`.

**Architecture:** Migrate `VERTICAL_SLICE_INDICATORS` and all routing tables to real CEPALSTAT `indicator_id`s from Spec Section 3, attaching declarative `mandatory_filters` (`tuple[AppliedDimensionFilter, ...]`) to indicators backed by multi-rubric tables (`1246`, `2050`, `883`, `286`, `2193`, `4410`, `365`). Upgrade `SemanticDataFetcher` to bind DataFrame columns via `FacetOntology.classify_dimension` and fail closed (`observation_exists=False`) whenever a non-aggregate dimension filter cannot be bound. Execute Stage 3.5 `Specificity Guard` prior to Stage 3 `AMBIGUOUS_CONFIGS` shortcuts so uncovered domain tokens never trigger false proposals.

**Tech Stack:** Python >=3.10, `uv`, `pydantic` v2, `pandas`, `sqlite3`, `pytest`, `mypy`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-10-30-pre-mcp-semantic-scaling-spec.md`

## Global Constraints

- Import always from `unofficial_cepalstat_mcp` (never `from statscepal`).
- Always run `uv run pytest -m "not integration"`; never trigger live `@pytest.mark.integration` network calls in CI/test runs.
- Preserve **0.00% False Substitution Rate (FSR)**, **Zero Facet Loss**, **40/40** adversarial rejections, and local resolution latency **`p50 < 0.5 ms` / `p95 < 2.0 ms`**.
- Register new facets declaratively in `FacetOntology` (`src/unofficial_cepalstat_mcp/semantic/facet_ontology.py`), never via hardcoded `if facet == "..."` branches in `engine.py`, `parser.py`, or `matcher.py`.
- Never overwrite `provenance='curated'` relationships with `provenance='inferred'`.
- Never create `statscepal.db` in repo root; preserve UN/ECLAC non-affiliation disclaimers in `LICENSE` and `README.md`.
- Every modified module must pass `uv run mypy src/` (`0` errors) and `uv run ruff check .`.

## Review Focus

1. **Live CEPALSTAT suffix & inflection drift (`_(EH)`, `"Urbana"` vs `"Urbano"`):** Real CEPALSTAT DataFrames name poverty geography `"Area geográfica_(EH)"` with member `"Urbana"`, whereas curated metadata uses `"Área geográfica"` / `"Urbano"` — fetcher must bind both without dropping the filter or collapsing to `"Nacional"`.
2. **Unbound non-aggregate dimension filter (Fail-Closed Gate):** When a resolved `AppliedDimensionFilter` (e.g., `Rubro="Transporte"` or `Tipo de pobreza="Pobreza extrema"`) matches zero columns or zero rows in the DataFrame, `SemanticDataFetcher` must return `observation_exists=False` with `"UNBOUND_DIMENSION_FILTER"` rather than returning headline/national rows.
3. **Multi-rubric table without user-supplied facet (`1246`, `2050`, `883`, `286`, `2193`):** Queries like `"balance primario del gobierno central en Chile 2022"` have `facets={}` but target multi-rubric table `1246` — `IndicatorMetadata.mandatory_filters` must pin `"Resultado primario"` so `_format_payload` never selects an arbitrary rubric via `iloc[0]`.
4. **Ambiguous query hijacking specialized concepts (`"población sin ingresos propios en Chile"`, `"gasto público en salud"`):** `is_ambiguous_measure` in Stage 3 must not bypass Stage 3.5 `Specificity Guard`, and `"salud"` must resolve via declarative `funcion="SALUD"` on `4410` rather than being silently swallowed into aggregate `4405`.
5. **Optimized Python runtime (`python -O`) & `None` candidate guards:** Bare `assert selected_candidate is not None` statements are stripped under `PYTHONOPTIMIZE=1`; explicit `if ... is None:` checks must guard `engine.py` and `fetcher.py` (`_format_payload`).

---

## File Structure

- **Modify:** `src/unofficial_cepalstat_mcp/semantic/facet_ontology.py` — Accept `dim_id: int | None` in `classify_dimension`/`is_structural_dimension`, strip `_(...)` survey tags, and add declarative `funcion` COFOG facet (`SALUD`, `EDUCACION`, `PROTECCION_SOCIAL`).
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/models.py` — Ensure `AppliedDimensionFilter` is hashable/reusable for `IndicatorMetadata.mandatory_filters`.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/thesaurus.py` — Fix `target_id: int | None` typing at L202 and update `DEFAULT_ANTONYM_RULES` indicator IDs (`1241 -> 1246`, `1243 -> 740`).
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/parser.py` — Rename shadowed `m` loop variable (`edad_m`), route public spending functions via `FacetOntology`, and stop consuming `"salud"` into aggregate `GASTO_SOCIAL`.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/graph_builder.py` — Check curated relationships in both parent/child directions at L408–413 with explicit `None` narrowing.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/registry.py` — Add `mandatory_filters` to `IndicatorMetadata`, migrate `VERTICAL_SLICE_INDICATORS`, `OFFICIAL_25_CANONICAL_DEFAULTS`, `DEFAULT_OFFICIAL_DIMENSIONS`, `BADEHOG_SURVEY_INDICATORS`, and `TEMPORAL_AVAILABILITY_MATRIX` to Spec Section 3 real CEPALSTAT IDs; set `EMPIRICAL_INDICATOR_ID_MAP = {}`.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/engine.py` — Replace bare `assert`s, move Stage 3.5 `Specificity Guard` ahead of Stage 3 `AMBIGUOUS_CONFIGS` return, inject `mandatory_filters`, and update ID constants (`28`, `340`, `341`, `2204`, `2206`, `286`, `2484`, `365`, `1246`, `821`, `740`, `883`, `3154`, `4410`, `3324`, `3390`).
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/fetcher.py` — Add explicit `None` guard in `_format_payload`, bind columns via `FacetOntology.classify_dimension`, enforce fail-closed on unbound filters, expand gender/COICOP aliases, and add `allow_alternative: bool = False` to `fetch_resolved_data`.
- **Modify:** `src/unofficial_cepalstat_mcp/client.py` & `src/unofficial_cepalstat_mcp/cli.py` — Fix `dict[str, Any]` return narrowing in `client.py:67` and variable-shadowing type annotations in `cli.py` (`catalog_store`, `bitacora_store`, `dim_filter`, `metric_row`, `reg_summary`).
- **Create:** `tests/test_type_safety_and_guards.py` — Regression tests for `None` candidate payloads, `python -O` safety, bidirectional `GraphBuilder` curated checks, and `mypy` zero-error check.
- **Create:** `tests/test_canonical_catalog_alignment.py` — Cross-checks every `VERTICAL_SLICE_INDICATORS` entry against official CEPALSTAT IDs, names, units, and `mandatory_filters`.
- **Modify:** Benchmark JSONs & existing semantic unit tests (`tests/benchmark/*.json`, `tests/test_semantic_*.py`, `tests/test_benchmark_dataset_integrity.py`, `tests/test_parser_income_modifiers.py`, `tests/test_cli_semantic.py`) + `.agents/rules/semantic-resolution-guardrails.md` & `AGENTS.md`.

---

### Task 1: Static Type Hygiene & Runtime `None`-Guard Hardening (`mypy` -> 0 errors)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/facet_ontology.py:160-215`
- Modify: `src/unofficial_cepalstat_mcp/semantic/thesaurus.py:195-211`
- Modify: `src/unofficial_cepalstat_mcp/semantic/parser.py:554-565`
- Modify: `src/unofficial_cepalstat_mcp/semantic/graph_builder.py:406-415`
- Modify: `src/unofficial_cepalstat_mcp/semantic/engine.py:368-540`
- Modify: `src/unofficial_cepalstat_mcp/semantic/fetcher.py:283-355, 920-1114`
- Modify: `src/unofficial_cepalstat_mcp/client.py:66-72`
- Modify: `src/unofficial_cepalstat_mcp/cli.py:440-1040`
- Create: `tests/test_type_safety_and_guards.py`

**Interfaces:**
- Consumes: `SemanticResolutionResponse`, `FacetOntology`, `GraphBuilder`
- Produces:
  - `FacetOntology.is_structural_dimension(self, dim_id: int | None, dim_name: str) -> bool`
  - `FacetOntology.classify_dimension(self, dim_id: int | None, dim_name: str) -> str | None`
  - Zero `mypy` errors across all 32+ source files in `src/unofficial_cepalstat_mcp/`

- [ ] **Step 1: Write the failing tests for `None`-candidate safety, bidirectional curated graph check, `dim_id=None` classification, and `mypy` cleanliness**

Create `tests/test_type_safety_and_guards.py`:
```python
import subprocess
import sys

import pandas as pd

from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY
from unofficial_cepalstat_mcp.semantic.fetcher import SemanticDataFetcher
from unofficial_cepalstat_mcp.semantic.graph_builder import GraphBuilder
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus, SemanticResolutionResponse


def test_classify_dimension_accepts_none_dim_id() -> None:
    assert DEFAULT_FACET_ONTOLOGY.classify_dimension(None, "Area geográfica_(EH)") == "area"
    assert DEFAULT_FACET_ONTOLOGY.classify_dimension(None, "País__ESTANDAR") == "__structural__"


def test_format_payload_handles_none_selected_candidate_without_crash() -> None:
    fetcher = SemanticDataFetcher.__new__(SemanticDataFetcher)
    resp = SemanticResolutionResponse(status=ResolutionStatus.ABSTAINED, query="test")
    payload = fetcher._format_payload(
        filtered_df=pd.DataFrame(),
        response=resp,
        empirical_id=3328,
        year_col=None,
        country_col=None,
        dim_cols=[],
        breakdown_cols=[],
        is_multi_year=False,
        is_multi_country=False,
        has_breakdown=False,
        has_rescued_anchors=False,
        target_year=2022,
        requested_year_set={2022},
        country_anchor_map={},
        code_by_name={},
        target_country_codes=[],
        target_country_names=[],
    )
    assert payload["observation_exists"] is False
    assert payload["indicator_name"] == ""
    assert payload["unit"] == ""


def test_graph_builder_does_not_flag_child_to_parent_curated_breakdown_as_false(tmp_path) -> None:
    store = CatalogStore(db_path=tmp_path / "g.db")
    builder = GraphBuilder(store=store)
    report = builder.build_breakdown_graph(persist=False, seed_curated=True)
    assert report.false_curated_edges == 0


def test_mypy_passes_with_zero_errors() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", "src/unofficial_cepalstat_mcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"mypy failed:\n{proc.stdout}\n{proc.stderr}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_type_safety_and_guards.py -v`
Expected: FAIL (`AttributeError: 'NoneType' object has no attribute 'name'` in `_format_payload` and `mypy` exit code 1 with 64 errors).

- [ ] **Step 3: Fix type annotations, survey-tag stripping in `FacetOntology`, and runtime `None` guards**

1. In `src/unofficial_cepalstat_mcp/semantic/facet_ontology.py`:
   - Change `is_structural_dimension(self, dim_id: int | None, dim_name: str) -> bool` and `classify_dimension(self, dim_id: int | None, dim_name: str) -> str | None`, guarding `dim_id is not None` before `in` checks.
   - Normalize `dim_name` in both methods by stripping trailing `_(...)` survey qualifiers (`re.sub(r"_\([^)]*\)$", "", norm)`) in addition to `__.*$`.
2. In `src/unofficial_cepalstat_mcp/semantic/thesaurus.py:197`: annotate `target_id: int | None = None`.
3. In `src/unofficial_cepalstat_mcp/semantic/parser.py:560`: rename loop variable `for edad_m in edad_matches: consumed_phrases.append(edad_m.matched_term)`.
4. In `src/unofficial_cepalstat_mcp/semantic/graph_builder.py:407-414`: look up `rel = VERTICAL_SLICE_INDICATORS[edge.parent_id].relationships.get(edge.child_id) or VERTICAL_SLICE_INDICATORS[edge.child_id].relationships.get(edge.parent_id)` and narrow with `if rel is not None:` before reading `rel.value`.
5. In `src/unofficial_cepalstat_mcp/semantic/engine.py` (`L368`, `L433`, `L511`) and `fetcher.py` (`L287`, `L347`, `L933-1113`): replace bare `assert ... is not None` with explicit `if ... is None:` checks; bind `cand_name = response.selected_candidate.name if response.selected_candidate else ""` and `cand_unit = response.selected_candidate.unit if response.selected_candidate else ""` at the top of `_format_payload`, and annotate `payload: dict[str, Any]`.
6. In `src/unofficial_cepalstat_mcp/client.py:67`: validate `data = response.json()` is `dict` (`if not isinstance(data, dict): raise CepalStatAPIError(...)`) before returning `data`.
7. In `src/unofficial_cepalstat_mcp/cli.py`: use distinct typed local variables per subcommand (`cat_store: CatalogStore`, `bit_store: BitacoraStore`, `dim_f: AppliedDimensionFilter`, `metric_item: CountryPeriodMetric`, `reg_model: RegressionModelSummary`, `resolved_member_ids: list[int] | None`) instead of reusing untyped variable names across branches.

- [ ] **Step 4: Run tests and `mypy` to verify they pass**

Run: `uv run pytest tests/test_type_safety_and_guards.py -v && uv run mypy src/unofficial_cepalstat_mcp/`
Expected: PASS (`Success: no issues found in 32 source files`).

- [ ] **Step 5: Commit**

```bash
git add src/ tests/test_type_safety_and_guards.py
git commit -m "fix(typing): resolve all 64 mypy errors and guard None candidate dereferences"
```

---

### Task 2: Canonical Real CEPALSTAT ID Migration & `mandatory_filters` in `SemanticRegistry`

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/registry.py`
- Modify: `src/unofficial_cepalstat_mcp/semantic/thesaurus.py:424-634`
- Create: `tests/test_canonical_catalog_alignment.py`
- Modify: `tests/test_semantic_registry_200.py`

**Interfaces:**
- Consumes: `AppliedDimensionFilter` from `unofficial_cepalstat_mcp.semantic.models`
- Produces:
  - `IndicatorMetadata.__init__(..., mandatory_filters: tuple[AppliedDimensionFilter, ...] = ())`
  - `EMPIRICAL_INDICATOR_ID_MAP: dict[int, int] = {}` (zero synthetic-to-live remapping needed)
  - Real CEPALSTAT IDs across `VERTICAL_SLICE_INDICATORS` and `OFFICIAL_25_CANONICAL_DEFAULTS` per Spec Section 3:
    `128->341`, `3337->340`, `3339->2287`, `3345->2198`, `3340->3324` (+ `3390` deciles breakdown), `3331/3344->5097`, `3333->2288`, `729->2204`, `2203` (current USD), `2193` (current local currency), `730->2206`, `731/2447->286`, `2928->2484`, `2929` (annual food CPI growth `%`), `2930->365` (with COICOP rubric dimension), `1241->1246` (mandatory rubric `"Resultado primario"`), `1242->821`, `1243->740`, `1244/2954->883` (mandatory rubric `"Relación de precios del intercambio de bienes"`), `2949->2050` (mandatory rubric `"Balanza de bienes"`), `4405->4410` (`% PIB` by COFOG function; `4405` retained with true SOCX local-currency metadata), `4406->460`, `5683->3154`, `1318->4185`, `4992->28` (`4992` retained only for indigenous `%` by area).

- [ ] **Step 1: Write the failing canonical alignment test**

Create `tests/test_canonical_catalog_alignment.py`:
```python
from unofficial_cepalstat_mcp.semantic.registry import (
    EMPIRICAL_INDICATOR_ID_MAP,
    OFFICIAL_25_CANONICAL_DEFAULTS,
     SemanticRegistry,
    VERTICAL_SLICE_INDICATORS,
)

FORBIDDEN_SYNTHETIC_IDS = {128, 729, 730, 731, 1241, 1242, 1243, 1244, 1318, 2447, 2928, 2930, 3331, 3344, 4406}


def test_no_synthetic_ids_remain_in_registry_or_defaults() -> None:
    assert EMPIRICAL_INDICATOR_ID_MAP == {}
    assert FORBIDDEN_SYNTHETIC_IDS.isdisjoint(VERTICAL_SLICE_INDICATORS.keys())
    assert FORBIDDEN_SYNTHETIC_IDS.isdisjoint(OFFICIAL_25_CANONICAL_DEFAULTS.values())


def test_colliding_ids_carry_true_cepalstat_definitions() -> None:
    reg = SemanticRegistry()
    # 2203 = corrientes USD; 2204 = constantes USD; 2193 = corrientes MN
    assert "corrientes" in reg.get_indicator(2203).name.lower()
    assert "constantes" in reg.get_indicator(2204).name.lower()
    assert "moneda nacional" in reg.get_indicator(2193).name.lower()
    # 4405 = moneda nacional SOCX; 4410 = gasto publico por funcion % PIB
    assert "moneda nacional" in reg.get_indicator(4405).unit.lower() or "moneda nacional" in reg.get_indicator(4405).name.lower()
    assert reg.get_indicator(4410).unit == "%"
    # 28 = poblacion segun area geografica y sexo; 4992 = % poblacion indigena
    assert "indigena" not in reg.get_indicator(28).name.lower()
    assert "indígena" in reg.get_indicator(4992).name.lower()
    # Multi-rubric indicators declare mandatory_filters
    assert len(reg.get_indicator(1246).mandatory_filters) == 1
    assert "primario" in reg.get_indicator(1246).mandatory_filters[0].member_name.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_canonical_catalog_alignment.py -v`
Expected: FAIL (`EMPIRICAL_INDICATOR_ID_MAP` has 25 entries, synthetic IDs present, `2203`/`2204` inverted).

- [ ] **Step 3: Migrate `SemanticRegistry`, `DEFAULT_ANTONYM_RULES`, and `tests/test_semantic_registry_200.py` to Spec Section 3 real IDs**

1. Add `mandatory_filters: tuple[AppliedDimensionFilter, ...] = ()` to `IndicatorMetadata.__init__` in `src/unofficial_cepalstat_mcp/semantic/registry.py` and copy it in `SemanticRegistry._build_in_memory_index()`.
2. Replace every synthetic/colliding entry in `VERTICAL_SLICE_INDICATORS`, `DEFAULT_OFFICIAL_DIMENSIONS`, `OFFICIAL_25_CANONICAL_DEFAULTS`, `BADEHOG_SURVEY_INDICATORS`, and `TEMPORAL_AVAILABILITY_MATRIX` with the exact real CEPALSTAT IDs, names, units, and `mandatory_filters` from Spec Section 3 (wiring `3324 <-> 3390` as `BREAKDOWN_OF`/`ALTERNATIVE_MEASURE` for quintiles vs deciles, `2484` with `2929`/`4145` for CPI YoY rates and `365`/`1684` for CPI index levels + COICOP transport/energy rubric, and `28` for urban/rural population).
3. Set `EMPIRICAL_INDICATOR_ID_MAP: dict[int, int] = {}` in `registry.py`.
4. Update `DEFAULT_ANTONYM_RULES` in `src/unofficial_cepalstat_mcp/semantic/thesaurus.py` (`1241 -> 1246`, `1243 -> 740`) and update `EXPECTED_25_INDICATORS` / `EXPECTED_TYPED_RELATIONSHIPS` in `tests/test_semantic_registry_200.py`.

- [ ] **Step 4: Run registry alignment tests**

Run: `uv run pytest tests/test_canonical_catalog_alignment.py tests/test_semantic_registry_200.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/registry.py src/unofficial_cepalstat_mcp/semantic/thesaurus.py tests/test_canonical_catalog_alignment.py tests/test_semantic_registry_200.py
git commit -m "refactor(semantic): migrate registry from synthetic IDs to real CEPALSTAT IDs"
```

---

### Task 3: Engine Routing Migration, Early Specificity Guard & Declarative `funcion` Facet

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/facet_ontology.py:351-805`
- Modify: `src/unofficial_cepalstat_mcp/semantic/parser.py:820-840, 1175-1220`
- Modify: `src/unofficial_cepalstat_mcp/semantic/engine.py:44-165, 320-640, 892-898`
- Modify: `src/unofficial_cepalstat_mcp/cli.py:925-938`
- Modify: `tests/test_semantic_unconsumed_tokens_guard.py`
- Modify: `tests/test_semantic_motivating_remediations.py`

**Interfaces:**
- Consumes: `IndicatorMetadata.mandatory_filters` from Task 2; `FacetDefinition` in `FacetOntology`
- Produces:
  - Declarative `FacetDefinition(facet_key="funcion", ...)` in `DEFAULT_FACETS` (`SALUD`, `EDUCACION`, `PROTECCION_SOCIAL`, `TOTAL`, with `implicit_aggregate_values=frozenset({"TOTAL"})`).
  - Stage 3.5 `Specificity Guard` executed **before** `AMBIGUOUS_CONFIGS` returns `ALTERNATIVE_PROPOSED` in `SemanticResolutionEngine.resolve()`.
  - Automatic prepending of `selected_meta.mandatory_filters` into `applied_filters.dimensions` when not already constrained by user facets.

- [ ] **Step 1: Write failing tests for Review Focus #3 and #4 (early specificity guard, health spending facet, and mandatory rubric injection)**

Append to `tests/test_semantic_unconsumed_tokens_guard.py`:
```python
def test_ambiguous_income_does_not_hijack_gender_own_income_query() -> None:
    engine = SemanticResolutionEngine()
    resp = engine.resolve("población sin ingresos propios en Chile 2022")
    # Must NOT propose Salario medio real (341) with score 0.92
    assert resp.status == ResolutionStatus.ABSTAINED
    assert "UNRESOLVED_SPECIFICITY" in (resp.abstention_reason or "") or resp.selected_candidate is None


def test_public_health_spending_routes_to_cofog_function_not_aggregate_socx() -> None:
    engine = SemanticResolutionEngine()
    resp = engine.resolve("gasto público en salud como porcentaje del PIB en Argentina 2022")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 4410
    assert resp.applied_filters.facets.get("funcion") == "SALUD"


def test_primary_fiscal_balance_injects_mandatory_rubric_filter() -> None:
    engine = SemanticResolutionEngine()
    resp = engine.resolve("balance primario del gobierno central en Chile 2022")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 1246
    assert any("primario" in d.member_name.lower() for d in resp.applied_filters.dimensions)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_unconsumed_tokens_guard.py -v`
Expected: FAIL (`población sin ingresos propios` returns `ALTERNATIVE_PROPOSED` on wage; `gasto público en salud` routes to `4405` without `funcion="SALUD"`).

- [ ] **Step 3: Register `funcion` in `FacetOntology`, fix `parser.py` token consumption, and reorder Stage 3 / Stage 3.5 in `engine.py`**

1. In `src/unofficial_cepalstat_mcp/semantic/facet_ontology.py`: add `FacetDefinition(facet_key="funcion", description="Clasificación funcional del gasto público (COFOG)", dimension_name_patterns=("funcion", "clasificacion funcional", "finalidad del gasto"), member_value_patterns={"SALUD": ("salud",), "EDUCACION": ("educacion",), "PROTECCION_SOCIAL": ("proteccion social", "gasto social"), "TOTAL": ("total", "gasto total")}, implicit_aggregate_values=frozenset({"TOTAL"}), total_member_patterns=("total", "gasto total"), query_triggers=(QueryTriggerRule(canonical_value="SALUD", phrases=("en salud", "de salud", "sanitario")), QueryTriggerRule(canonical_value="PROTECCION_SOCIAL", phrases=("proteccion social", "gasto social")),))` and add `"propios"` / `"sin ingresos"` awareness to `CRITICAL_SPECIFICITY_TOKENS` in `engine.py`.
2. In `src/unofficial_cepalstat_mcp/semantic/parser.py`: remove `"salud"` / `"gasto en salud"` from `consumed_phrases` when routing general `GASTO_SOCIAL`, let `ontology.extract_query_facets()` populate `facets["funcion"] = "SALUD"`, and route `PIB_CORRIENTE` to `2193` (local currency) / `2203` (USD).
3. In `src/unofficial_cepalstat_mcp/semantic/engine.py`:
   - Update `GENERAL_AGGREGATE_FALLBACKS`, `AMBIGUOUS_CONFIGS`, `_route_population_indicator` (`4992 -> 28`), quarterly check `(286,)`, and tax hint (`821` / `845`) to real CEPALSTAT IDs.
   - Run the uncovered `CRITICAL_SPECIFICITY_TOKENS` check **before** the `if intent.is_ambiguous_measure:` early return so uncovered modifiers (`"propios"`, `"hipotecario"`, etc.) abstain instead of proposing unrelated macro/wage indicators.
   - Merge `selected_meta.mandatory_filters` into `applied_filters.dimensions` (for any dimension not already bound by `matcher.match_facets_to_dimensions`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_semantic_unconsumed_tokens_guard.py tests/test_semantic_motivating_remediations.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/facet_ontology.py src/unofficial_cepalstat_mcp/semantic/parser.py src/unofficial_cepalstat_mcp/semantic/engine.py src/unofficial_cepalstat_mcp/cli.py tests/test_semantic_unconsumed_tokens_guard.py tests/test_semantic_motivating_remediations.py
git commit -m "fix(semantic): enforce specificity guard before ambiguity shortcut and add COFOG funcion facet"
```

---

### Task 4: Fail-Closed `FacetOntology` Column Binding & `allow_alternative` in `SemanticDataFetcher`

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/fetcher.py:17-90, 220-282, 520-583, 1115-1155`
- Modify: `tests/test_semantic_fetcher.py`

**Interfaces:**
- Consumes: `DEFAULT_FACET_ONTOLOGY.classify_dimension(dim_id: int | None, dim_name: str) -> str | None`
- Produces:
  - `SemanticDataFetcher.fetch_resolved_data(self, response: SemanticResolutionResponse, *, allow_alternative: bool = False) -> dict[str, Any]`
  - Fail-closed behavior: if any non-aggregate `AppliedDimensionFilter` in `response.applied_filters.dimensions` fails to match a DataFrame column (or matches 0 rows due to missing member), returns `{"observation_exists": False, "indicator_id": empirical_id, "reason": "UNBOUND_DIMENSION_FILTER: <dim_name>=<member_name>", "series": []}` rather than silently collapsing to national/total.

- [ ] **Step 1: Write failing tests for Review Focus #1 and #2 (`_(EH)` column suffix binding, fail-closed unbound filter, and `allow_alternative=True`)**

Append to `tests/test_semantic_fetcher.py`:
```python
def test_fetcher_binds_live_eh_column_and_feminine_member_labels(mocker) -> None:
    df = pd.DataFrame([
        {"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "Area geográfica_(EH)": "Nacional", "Pobreza extrema y pobreza": "Pobreza", "value": 8.1},
        {"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "Area geográfica_(EH)": "Rural", "Pobreza extrema y pobreza": "Pobreza extrema", "value": 3.4},
        {"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "Area geográfica_(EH)": "Urbana", "Pobreza extrema y pobreza": "Pobreza", "value": 7.9},
    ])
    engine = SemanticResolutionEngine()
    resp = engine.resolve("pobreza extrema rural en Chile 2022")
    fetcher = SemanticDataFetcher(extractor=mocker.Mock(get_dataframe=mocker.Mock(return_value=df)))
    out = fetcher.fetch_resolved_data(resp)
    assert out["observation_exists"] is True
    assert out["value"] == 3.4


def test_fetcher_fails_closed_when_non_aggregate_dimension_column_missing(mocker) -> None:
    df = pd.DataFrame([
        {"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "value": 8.1},
    ])
    engine = SemanticResolutionEngine()
    resp = engine.resolve("pobreza extrema rural en Chile 2022")
    fetcher = SemanticDataFetcher(extractor=mocker.Mock(get_dataframe=mocker.Mock(return_value=df)))
    out = fetcher.fetch_resolved_data(resp)
    assert out["observation_exists"] is False
    assert "UNBOUND_DIMENSION_FILTER" in out["reason"]


def test_fetcher_allows_primary_candidate_when_allow_alternative_enabled(mocker) -> None:
    df = pd.DataFrame([
        {"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "value": 108.5},
    ])
    engine = SemanticResolutionEngine()
    resp = engine.resolve("salarios en Chile 2022")
    assert resp.status == ResolutionStatus.ALTERNATIVE_PROPOSED
    fetcher = SemanticDataFetcher(extractor=mocker.Mock(get_dataframe=mocker.Mock(return_value=df)))
    assert fetcher.fetch_resolved_data(resp)["observation_exists"] is False
    assert fetcher.fetch_resolved_data(resp, allow_alternative=True)["observation_exists"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_fetcher.py -k "binds_live_eh or fails_closed or allows_primary" -v`
Expected: FAIL (`binds_live_eh` returns `8.1` National instead of `3.4` Rural; `fails_closed` returns `observation_exists=True`).

- [ ] **Step 3: Implement `FacetOntology`-backed column matching, expanded member aliases, fail-closed gate, and `allow_alternative` in `SemanticDataFetcher`**

1. In `src/unofficial_cepalstat_mcp/semantic/fetcher.py`:
   - Strip `_(...)` suffixes (`re.sub(r"_\([^)]*\)$", "", text)`) in `_match_dim_column`, and add semantic fallback: if `DEFAULT_FACET_ONTOLOGY.classify_dimension(None, col_name)` matches `DEFAULT_FACET_ONTOLOGY.classify_dimension(dim_filter.dim_id, dim_filter.dim_name)` (and is not `None` or `"__structural__"`), treat the column as a match.
   - Add canonical equivalence sets in `MEMBER_VALUE_ALIASES`: `"urbano": ["urbana", "area urbana", "zona urbana"]`, `"rural": ["area rural", "zona rural"]`, `"pobreza extrema / indigencia": ["pobreza extrema", "indigencia"]`, `"total pobreza": ["pobreza"]`, `"ambos sexos": ["total"]`.
   - Change `_apply_dimension_filters(self, df: pd.DataFrame, response: SemanticResolutionResponse) -> tuple[pd.DataFrame, set[str], str | None]`: if `dim_col is None` for any filter whose `member_name` is NOT an aggregate total (`not DEFAULT_FACET_ONTOLOGY.is_aggregate_member_name(facet_key or "", dim_filter.member_name)`), return an error reason `"UNBOUND_DIMENSION_FILTER: <dim_name>=<member_name>"` and abort in `fetch_resolved_data` with `observation_exists=False`.
   - Add `*, allow_alternative: bool = False` to `fetch_resolved_data` so `ResolutionStatus.ALTERNATIVE_PROPOSED` is accepted when `allow_alternative=True` and `response.selected_candidate is not None`.

- [ ] **Step 4: Run `test_semantic_fetcher.py` to verify all fetcher tests pass**

Run: `uv run pytest tests/test_semantic_fetcher.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/fetcher.py tests/test_semantic_fetcher.py
git commit -m "fix(fetcher): bind columns via FacetOntology and fail closed on unbound filters"
```

---

### Task 5: Benchmark Suite Migration (200 Canonical + 40 Adversarial + Facet Coverage) & Guardrail Sync

**Files:**
- Modify: `tests/benchmark/semantic_benchmark_cases_200.json`
- Modify: `tests/benchmark/facet_coverage_cases.json`
- Modify: `tests/benchmark/adversarial_benchmark_cases_40.json`
- Modify: `tests/test_benchmark_dataset_integrity.py`
- Modify: `tests/test_semantic_breakdowns.py`
- Modify: `tests/test_semantic_multi_year.py`
- Modify: `tests/test_parser_income_modifiers.py`
- Modify: `tests/test_semantic_generic_gate.py`
- Modify: `tests/test_semantic_thesaurus.py`
- Modify: `tests/test_cli_semantic.py`
- Modify: `.agents/rules/semantic-resolution-guardrails.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: Real CEPALSTAT `indicator_id`s from Tasks 2–4
- Produces: 100% green offline test suite (`uv run pytest -m "not integration"`), `0.00% FSR`, `p50 < 0.5 ms`, `0` `mypy` errors, `0` `ruff` warnings.

- [ ] **Step 1: Update expected indicator IDs in unit tests and benchmark JSONs per Spec Section 3**

Apply the exact 1-to-1 ID mapping from Spec Section 3 across `tests/benchmark/semantic_benchmark_cases_200.json`, `tests/benchmark/facet_coverage_cases.json`, `tests/benchmark/adversarial_benchmark_cases_40.json`, `tests/test_benchmark_dataset_integrity.py` (`C4`: `{340, 341, 2287, 2198}`), `tests/test_semantic_breakdowns.py` (`4992 -> 28`, `3340 -> 3324/3390`, `3339 -> 2287`), `tests/test_semantic_multi_year.py`, `tests/test_parser_income_modifiers.py`, `tests/test_semantic_generic_gate.py`, `tests/test_semantic_thesaurus.py`, and `tests/test_cli_semantic.py`.

- [ ] **Step 2: Run the 200-question and 40-question adversarial benchmarks to verify 100% accuracy and latency**

Run: `uv run pytest tests/test_benchmark_dataset_integrity.py tests/test_semantic_benchmark_200.py tests/test_adversarial_benchmark_40.py -v`
Expected: PASS (`200/200` accuracy = `100.0%`, `FSR = 0.00%`, `40/40` adversarial rejections, `p50 < 0.5 ms`).

- [ ] **Step 3: Sync `.agents/rules/semantic-resolution-guardrails.md` and `AGENTS.md` with canonical IDs**

Update Guardrail #9 and #11 in `.agents/rules/semantic-resolution-guardrails.md` and `AGENTS.md` (preserving YAML frontmatter `trigger: model_decision` in `.agents/rules/semantic-resolution-guardrails.md` and zero frontmatter in `AGENTS.md`) to reflect that all `VERTICAL_SLICE_INDICATORS` now use native CEPALSTAT IDs (`28` for urban/rural population, `EMPIRICAL_INDICATOR_ID_MAP` retired to `{}`) while keeping `SYNTHETIC_DIMENSION_MEMBER_IDS` boundary protection intact.

- [ ] **Step 4: Run full offline suite, `mypy`, and `ruff`**

Run: `uv run ruff check . && uv run mypy src/unofficial_cepalstat_mcp/ && uv run pytest -m "not integration" -q`
Expected: All checks pass, `0` `mypy` errors, `400+` tests passing with `0` failures.

- [ ] **Step 5: Commit**

```bash
git add tests/ .agents/rules/semantic-resolution-guardrails.md AGENTS.md
git commit -m "test(benchmark): align 200-query and adversarial suites with real CEPALSTAT IDs"
```
