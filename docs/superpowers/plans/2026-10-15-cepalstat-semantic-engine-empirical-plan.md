# CEPALSTAT Real Semantic Engine & Empirical Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and empirically validate the end-to-end CEPALSTAT Semantic Resolution Engine as a production-grade Python library backed by dynamic SQLite metadata, dynamic dimension/member matching, live API data extraction, a rich CLI diagnostic tool (`statscepal semantic resolve`), and an expanded 50-case benchmark covering all major thematic domains.

**Architecture:**
1. **Dynamic SQLite Metadata Store (`CatalogStore` & `SemanticRegistry`):** Persist dimensions, members, typed relationships (`breakdown_of`, `alternative_measure`), and empirical temporal availability calendars in `.statscepal_cache.db`, replacing hardcoded dictionaries with dynamic relational queries.
2. **Dynamic Member Matcher (`src/statscepal/semantic/matcher.py`):** Map canonical conceptual facets (e.g. `SEXO: FEMENINO`, `AREA: RURAL`) to actual `dim_id` and `member_id` values dynamically discovered from each indicator's real metadata in the database.
3. **Live Empirical Data Fetcher (`src/statscepal/semantic/fetcher.py`):** Bridge resolved queries to live data extraction via `DataExtractor`, verifying that resolved indicators and filters return valid non-empty observations with provenance.
4. **Interactive CLI Diagnostics (`statscepal semantic resolve`):** Expose terminal commands with table and JSON outputs for interactive testing by researchers and developers.
5. **Expanded 50-Case Benchmark:** Expand ground truth test dataset across all 23 areas of CEPALSTAT with rigorous automated regression verification.

**Tech Stack:** Python 3.10+, `pydantic>=2.7.0`, `sqlite3`, `httpx>=0.27.0`, `pandas>=2.2.0`, `pytest>=8.0.0`, `statscepal`.

**Specs:**
- Normativa Arquitectura v2: [`docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md)
- Benchmark & Corte Vertical Spec: [`docs/specs/2026-10-15-benchmark-y-corte-vertical-spec.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/specs/2026-10-15-benchmark-y-corte-vertical-spec.md)
- Resumen Ejecutivo: [`docs/specs/2026-10-15-motor-semantico-cepalstat-resumen-ejecutivo.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/specs/2026-10-15-motor-semantico-cepalstat-resumen-ejecutivo.md)

## Global Constraints
- Python 3.10+ modern typing syntax (`int | None`).
- Strict Test-Driven Development (TDD) for every task: write test -> see RED -> minimal implementation -> see GREEN -> commit.
- All 142 existing non-integration tests must remain passing without regression.
- False Substitution Rate must strictly equal 0.0% (no untyped indicator swaps).
- Local resolution latency over SQLite must maintain p50 < 2.0 ms.
- Safe UTF-8 encoding for Windows console environments (`cp1252` protection).

---

### Task 1: Relational Schema & Dynamic Metadata Ingestion in SQLite

**Files:**
- Modify: `src/statscepal/catalog/store.py`
- Modify: `src/statscepal/semantic/registry.py`
- Test: `tests/test_semantic_store_relational.py`

**Interfaces:**
- Consumes:
  - `CatalogStore._get_connection()`
  - `Dimension`, `Member` from `src/statscepal/dimensions.py`
- Produces:
  - `CatalogStore.init_semantic_tables() -> None`
  - `CatalogStore.store_indicator_dimensions(indicator_id: int, dimensions: list[Dimension]) -> None`
  - `CatalogStore.get_indicator_dimensions(indicator_id: int) -> list[Dimension]`
  - `CatalogStore.store_relationship(indicator_a: int, indicator_b: int, rel: str) -> None`
  - `CatalogStore.get_relationships(indicator_a: int) -> dict[int, str]`
  - `CatalogStore.store_temporal_record(indicator_id: int, country: str, year: int, status: str, prev: int | None, next: int | None) -> None`
  - `CatalogStore.get_temporal_record(indicator_id: int, country: str, year: int) -> tuple[str, int | None, int | None] | None`
  - `SemanticRegistry(store: CatalogStore | None = None)` dynamically querying SQLite with in-memory fallback.

- [ ] **Step 1: Write failing test in `tests/test_semantic_store_relational.py`**

```python
from pathlib import Path
import pytest
from statscepal.catalog.store import CatalogStore
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.registry import SemanticRegistry
from statscepal.semantic.models import RelationshipType, TemporalAvailabilityStatus


def test_catalog_store_relational_schema(tmp_path: Path):
    db_path = tmp_path / "test_semantic_relational.db"
    store = CatalogStore(db_path=db_path)
    store.init_semantic_tables()

    # Store dimensions and members
    dims = [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=331, name="Rural")],
        ),
    ]
    store.store_indicator_dimensions(3341, dims)
    loaded_dims = store.get_indicator_dimensions(3341)
    assert len(loaded_dims) == 2
    assert loaded_dims[0].id == 144
    assert len(loaded_dims[0].members) == 2
    assert loaded_dims[0].members[1].name == "Mujeres"

    # Store relationship
    store.store_relationship(3341, 3328, "breakdown_of")
    rels = store.get_relationships(3341)
    assert rels.get(3328) == "breakdown_of"

    # Store temporal availability
    store.store_temporal_record(3328, "CHL", 2021, "PERIOD_UNOBSERVED", 2020, 2022)
    temp_rec = store.get_temporal_record(3328, "CHL", 2021)
    assert temp_rec is not None
    assert temp_rec[0] == "PERIOD_UNOBSERVED"
    assert temp_rec[1] == 2020
    assert temp_rec[2] == 2022

    # Query via SemanticRegistry backed by this store
    registry = SemanticRegistry(store=store)
    rel = registry.check_relationship(3341, 3328)
    assert rel == RelationshipType.BREAKDOWN_OF
    status, prev_a, next_a = registry.check_temporal_availability(3328, "CHL", 2021)
    assert status == TemporalAvailabilityStatus.PERIOD_UNOBSERVED
    assert prev_a == 2020
    assert next_a == 2022
```

- [ ] **Step 2: Run test to confirm failure (RED)**

Run: `uv run pytest tests/test_semantic_store_relational.py`  
Expected: FAIL with `AttributeError: 'CatalogStore' object has no attribute 'init_semantic_tables'`

- [ ] **Step 3: Implement SQLite tables and methods in `store.py` and `registry.py`**
- Modify `src/statscepal/catalog/store.py` to create tables `indicator_dimensions`, `dimension_members`, `indicator_relationships`, and `temporal_availability`, with insert/select methods.
- Update `SemanticRegistry` in `src/statscepal/semantic/registry.py` to check `self.store` for relationships and temporal records before falling back to in-memory dictionaries.

- [ ] **Step 4: Run test to confirm pass (GREEN)**

Run: `uv run pytest tests/test_semantic_store_relational.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/catalog/store.py src/statscepal/semantic/registry.py tests/test_semantic_store_relational.py
git commit -m "feat(semantic): implement dynamic SQLite relational metadata store and registry integration"
```

---

### Task 2: Dynamic Dimension & Member Matching Engine

**Files:**
- Create: `src/statscepal/semantic/matcher.py`
- Modify: `src/statscepal/semantic/engine.py`
- Modify: `src/statscepal/semantic/__init__.py`
- Test: `tests/test_semantic_matcher.py`

**Interfaces:**
- Consumes:
  - `Dimension`, `Member` from `src/statscepal/dimensions.py`
  - `AppliedDimensionFilter` from `src/statscepal/semantic/models.py`
- Produces:
  - `DynamicMemberMatcher.match_facets_to_dimensions(indicator_id: int, dimensions: list[Dimension], facets: dict[str, str]) -> tuple[bool, list[AppliedDimensionFilter], list[str]]`
    - Returns `(all_matched: bool, applied_filters: list[AppliedDimensionFilter], unhandled_facets: list[str])`.

- [ ] **Step 1: Write failing test in `tests/test_semantic_matcher.py`**

```python
import pytest
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.matcher import DynamicMemberMatcher


def test_dynamic_member_matcher_resolves_members():
    matcher = DynamicMemberMatcher()
    dims = [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=43054,
            name="Grupo de edad",
            members=[Member(id=43059, name="0 a 14 años"), Member(id=43058, name="15 a 24 años")],
        ),
    ]

    facets = {"sexo": "FEMENINO", "area": "RURAL", "edad": "JUVENTUD"}
    success, filters, unhandled = matcher.match_facets_to_dimensions(3341, dims, facets)

    assert success is True
    assert len(unhandled) == 0
    assert len(filters) == 3

    filter_map = {f.dim_id: (f.member_id, f.member_name) for f in filters}
    assert filter_map[144] == (266, "Mujeres")
    assert filter_map[326] == (331, "Rural")
    assert filter_map[43054] == (43058, "15 a 24 años")


def test_dynamic_member_matcher_flags_unhandled_facet():
    matcher = DynamicMemberMatcher()
    dims = [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional")],
        )
    ]
    facets = {"sexo": "FEMENINO"}
    success, filters, unhandled = matcher.match_facets_to_dimensions(3328, dims, facets)

    assert success is False
    assert "sexo" in unhandled
```

- [ ] **Step 2: Run test to confirm failure (RED)**

Run: `uv run pytest tests/test_semantic_matcher.py`  
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.semantic.matcher'`

- [ ] **Step 3: Implement `src/statscepal/semantic/matcher.py` and integrate with `engine.py`**
- Create `src/statscepal/semantic/matcher.py` implementing `DynamicMemberMatcher` with regex/token rules resolving concept values (`FEMENINO`, `JUVENTUD`, `RURAL`, etc.) to actual member names in the dimension.
- Update `src/statscepal/semantic/engine.py` to use `DynamicMemberMatcher` to populate `applied_filters.dimensions`.
- Export `DynamicMemberMatcher` in `src/statscepal/semantic/__init__.py`.

- [ ] **Step 4: Run test to confirm pass (GREEN)**

Run: `uv run pytest tests/test_semantic_matcher.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/semantic/matcher.py src/statscepal/semantic/engine.py src/statscepal/semantic/__init__.py tests/test_semantic_matcher.py
git commit -m "feat(semantic): implement dynamic dimension and member matcher"
```

---

### Task 3: Live End-to-End Data Extraction Verification

**Files:**
- Create: `src/statscepal/semantic/fetcher.py`
- Modify: `src/statscepal/semantic/models.py`
- Modify: `src/statscepal/semantic/__init__.py`
- Test: `tests/test_semantic_fetcher.py`

**Interfaces:**
- Consumes:
  - `SemanticResolutionResponse` from `statscepal.semantic.models`
  - `CepalStatClient` from `statscepal.client`
  - `DataExtractor` from `statscepal.extractor`
- Produces:
  - `SemanticDataFetcher.fetch_resolved_data(response: SemanticResolutionResponse) -> dict[str, Any]`
  - Added field on `SemanticResolutionResponse`: `empirical_data: dict[str, Any] | None = None`

- [ ] **Step 1: Write failing test in `tests/test_semantic_fetcher.py`**

```python
from unittest.mock import MagicMock
import pandas as pd
import pytest
from statscepal.semantic.models import (
    AppliedDimensionFilter,
    AppliedFilters,
    ResolutionStatus,
    SelectedCandidate,
    SemanticResolutionResponse,
)
from statscepal.semantic.fetcher import SemanticDataFetcher


def test_semantic_data_fetcher_extracts_and_formats_observation():
    mock_extractor = MagicMock()
    # Mock return DataFrame from CEPALSTAT
    df_mock = pd.DataFrame(
        [
            {
                "country": "Brasil",
                "year": 2021,
                "value": 31.8,
                "notes_ids": "",
            }
        ]
    )
    mock_extractor.fetch_indicator_dataframe.return_value = df_mock

    fetcher = SemanticDataFetcher(extractor=mock_extractor)

    res = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="pobreza de mujeres jovenes rurales brasil 2021",
        selected_candidate=SelectedCandidate(
            indicator_id=3341,
            name="Tasa de incidencia de la pobreza según sexo y edad",
            measure_type="INCIDENCIA_PORCENTUAL",
            unit="%",
        ),
        applied_filters=AppliedFilters(
            country_code="BRA",
            country_name="Brasil",
            year=2021,
            facets={"sexo": "FEMENINO", "edad": "JUVENTUD", "area": "RURAL"},
            dimensions=[
                AppliedDimensionFilter(dim_id=144, dim_name="Sexo", member_id=266, member_name="Mujeres"),
                AppliedDimensionFilter(dim_id=326, dim_name="Área", member_id=331, member_name="Rural"),
            ],
        ),
    )

    data_payload = fetcher.fetch_resolved_data(res)
    assert data_payload["observation_exists"] is True
    assert data_payload["value"] == 31.8
    assert data_payload["unit"] == "%"
    assert data_payload["country"] == "Brasil"
    assert data_payload["year"] == 2021
```

- [ ] **Step 2: Run test to confirm failure (RED)**

Run: `uv run pytest tests/test_semantic_fetcher.py`  
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.semantic.fetcher'`

- [ ] **Step 3: Implement `src/statscepal/semantic/fetcher.py` and update `models.py`**
- Add `empirical_data: dict[str, Any] | None = None` to `SemanticResolutionResponse` in `src/statscepal/semantic/models.py`.
- Implement `SemanticDataFetcher` in `src/statscepal/semantic/fetcher.py` using `DataExtractor` or `CepalStatClient`.
- Export `SemanticDataFetcher` in `src/statscepal/semantic/__init__.py`.

- [ ] **Step 4: Run test to confirm pass (GREEN)**

Run: `uv run pytest tests/test_semantic_fetcher.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/semantic/fetcher.py src/statscepal/semantic/models.py src/statscepal/semantic/__init__.py tests/test_semantic_fetcher.py
git commit -m "feat(semantic): implement empirical data fetcher for resolved queries"
```

---

### Task 4: Interactive CLI Diagnostics Tool (`statscepal semantic resolve`)

**Files:**
- Modify: `src/statscepal/cli.py`
- Test: `tests/test_cli_semantic.py`

**Interfaces:**
- Consumes:
  - `SemanticResolutionEngine` from `statscepal.semantic`
  - `SemanticDataFetcher` from `statscepal.semantic`
- Produces:
  - Subcommand `statscepal semantic resolve "<query>" [--fetch] [--json]`

- [ ] **Step 1: Write failing test in `tests/test_cli_semantic.py`**

```python
import json
from unittest.mock import patch, MagicMock
from statscepal.cli import main


def test_cli_semantic_resolve_json_output(capsys):
    exit_code = main(["semantic", "resolve", "Pobreza total en Brasil en 2021", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "RESOLVED"
    assert data["selected_candidate"]["indicator_id"] == 3328


def test_cli_semantic_resolve_table_output(capsys):
    exit_code = main(["semantic", "resolve", "Tasa de pobreza de Chile en 2021"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "RESOLVED_WITH_ANCHORS" in captured.out or "CASEN" in captured.out
```

- [ ] **Step 2: Run test to confirm failure (RED)**

Run: `uv run pytest tests/test_cli_semantic.py`  
Expected: FAIL with `invalid choice: 'semantic'`

- [ ] **Step 3: Modify `src/statscepal/cli.py`**
- Add `semantic` subparser to `argparse` with `resolve` command taking `query`, `--fetch` (`action="store_true"`), and `--json` (`action="store_true"`).
- Format clean terminal box / table showing Status, Selected Indicator, Applied Filters, Temporal Anchors, and Empirical Value.

- [ ] **Step 4: Run test to confirm pass (GREEN)**

Run: `uv run pytest tests/test_cli_semantic.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/cli.py tests/test_cli_semantic.py
git commit -m "feat(cli): add statscepal semantic resolve subcommand with table and json output"
```

---

### Task 5: Expanded 50-Case Empirical Benchmark Suite

**Files:**
- Modify: `tests/benchmark/semantic_benchmark_cases.json`
- Modify: `tests/test_semantic_benchmark.py`

**Interfaces:**
- Consumes:
  - `BenchmarkEvaluator` from `statscepal.semantic`
  - 50 empirical ground-truth test cases across Social, Macro, Environmental, and Regional domains.
- Produces:
  - 100% pass rate across 50 cases.
  - Zero false substitutions (0.0%).
  - Local SQLite p50 latency < 2.0 ms.

- [ ] **Step 1: Expand `semantic_benchmark_cases.json` to 50 cases**
Add 25 additional cases covering:
- Cuentas Nacionales & PIB: Volumen constante `2203` vs corriente `2204`, PIB per cápita `2206`, PIB trimestral `2447`.
- Inflación & Precios: IPC General `365`, IPC alimentos `1684`, variación a doce meses `2929`.
- Sector Externo: Balanza comercial `2949`, Saldo en cuenta corriente % PIB `740`, IED `4231`.
- Sector Público: Deuda pública % PIB `1240`, Gasto social SOCX `4405`.
- Medio Ambiente: Emisiones GEI con LULUCF `5681` vs sin LULUCF `5682`, Recursos hídricos.
- Regionalismos colombianos, chilenos, mexicanos y peruanos.
- Casos de abstención justificada por periodicidad o concepto inválido.

- [ ] **Step 2: Update `tests/test_semantic_benchmark.py` to assert 50 cases**

```python
def test_full_benchmark_suite_execution_50_cases(benchmark_file: Path):
    evaluator = BenchmarkEvaluator(cases_path=benchmark_file)
    report = evaluator.evaluate()

    assert report.total_cases == 50
    assert report.passed_cases == 50, f"Failed cases: {[d.case_id for d in report.details if not d.passed]}"
    assert report.top1_accuracy_pct == 100.0
    assert report.recall_at_3_pct == 100.0
    assert report.false_substitution_rate_pct == 0.0
    assert report.facet_precision_pct == 100.0
    assert report.temporal_status_accuracy_pct == 100.0
    assert report.justified_abstention_rate_pct == 100.0
    assert report.p50_latency_ms < 2.0
```

- [ ] **Step 3: Run benchmark tests to confirm pass (GREEN)**

Run: `uv run pytest tests/test_semantic_benchmark.py`  
Expected: PASS (all tests pass)

- [ ] **Step 4: Run full project regression suite**

Run: `uv run pytest -m "not integration"`  
Expected: All 146+ tests pass with zero regressions.

- [ ] **Step 5: Commit**

```bash
git add tests/benchmark/semantic_benchmark_cases.json tests/test_semantic_benchmark.py
git commit -m "test(semantic): expand benchmark suite to 50 empirical test cases with 100% pass rate"
```
