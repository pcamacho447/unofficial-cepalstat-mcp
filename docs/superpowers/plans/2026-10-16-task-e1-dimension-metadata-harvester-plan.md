# Task E1: Dimension Metadata Harvester Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a resumable, rate-limited, and content-versioned harvesting engine (`CatalogStore.harvest` and CLI `statscepal catalog harvest`) that queries `/cepalstat/api/v1/indicator/{id}/dimensions` across all ~1,739 indicators in the master catalog and populates SQLite relational tables `indicator_dimensions` and `dimension_members` with 100% offline test hermeticity.

**Architecture:** Extend SQLite schema in `store.py` with metadata columns (`harvested_at`, `content_hash`). Build an asynchronous/resumable worker pipeline in `src/statscepal/catalog/harvester.py` utilizing `DimensionManager` and `CatalogStore.store_indicator_dimensions`, complete with retry with exponential backoff on transient network dropouts and a `--resume` checkpoint cursor. Expose the workflow in `src/statscepal/cli.py` with progress tracking and summary statistics.

**Tech Stack:** Python 3.10+, SQLite3, Pydantic v2, hashlib, respx / pytest-mock.

**Spec:** [docs/superpowers/plans/2026-10-16-epic-metadata-ingestion-generic-facet-routing.md](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-16-epic-metadata-ingestion-generic-facet-routing.md) and [docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md](file:///C:/papx/statscepal/docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md) (Decision 7).

## Global Constraints
- Python 3.10+ modern typing syntax (`int | None`, `list[int]`, `dict[str, Any]`).
- All existing 236+ non-integration tests must remain passing without regression.
- False Substitution Rate must strictly equal 0.00% across the 200-question benchmark.
- Top-1 Accuracy across the 200 benchmark test cases must strictly remain 100.0%.
- Local resolution latency over SQLite and in-memory thesaurus must maintain $p50 < 0.5\text{ ms}$.
- Strict offline hermeticity: test suites must NEVER perform live network calls to CEPALSTAT.
- Windows CP1252 / UTF-8 terminal output safety.

---

## File Structure & Responsibilities

| File | Action | Responsibility |
|---|---|---|
| `src/statscepal/catalog/store.py` | Modify | Update `indicator_dimensions` schema with `harvested_at`, `content_hash`, add `get_harvest_status()`, `get_unharvested_indicator_ids()`. |
| `src/statscepal/catalog/models.py` | Modify | Add `HarvestSummary`, `HarvestRecord` data models. |
| `src/statscepal/catalog/harvester.py` | Create | Core harvesting engine: rate limiting, retry with exponential backoff, checkpointing, content hash computation, batch progress callbacks. |
| `src/statscepal/cli.py` | Modify | Register `statscepal catalog harvest` subparser and command handler with interactive or progress bar reporting. |
| `tests/fixtures/dimensions/indicator_3328.json` | Create | Hermetic JSON fixture of dimensions for Indicator 3328. |
| `tests/fixtures/dimensions/indicator_3342.json` | Create | Hermetic JSON fixture of dimensions for Indicator 3342. |
| `tests/test_catalog_harvester.py` | Create | Unit and integration test suite testing schema updates, harvester logic, resume/checkpoint behavior, rate limiting, and CLI execution with respx mocks. |

---

### Task 1: Schema Extension and Harvest Status Query in `CatalogStore`

**Files:**
- Modify: `src/statscepal/catalog/store.py:81-125`
- Modify: `src/statscepal/catalog/models.py`
- Test: `tests/test_catalog_harvester.py`

**Interfaces:**
- Consumes: Existing SQLite connection `_get_connection()`, `Dimension` model from `statscepal.dimensions`.
- Produces:
  - `store.init_semantic_tables()`: adds `harvested_at TEXT`, `content_hash TEXT` to `indicator_dimensions` if not present.
  - `store.store_indicator_dimensions(indicator_id: int, dimensions: list[Dimension], content_hash: str | None = None, harvested_at: str | None = None) -> None`.
  - `store.get_harvested_indicator_ids() -> set[int]`.
  - `store.get_harvest_stats() -> dict[str, int]`.

- [ ] **Step 1: Write failing tests for schema migration and status queries**

```python
# In tests/test_catalog_harvester.py
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

    # Store with content hash
    dims = [
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=224, name="Total nacional"), Member(id=225, name="Urbana")]
        )
    ]
    store.store_indicator_dimensions(
        indicator_id=3328,
        dimensions=dims,
        content_hash="abc123hash",
        harvested_at="2026-10-16T16:00:00Z"
    )

    assert 3328 in store.get_harvested_indicator_ids()
    updated_stats = store.get_harvest_stats()
    assert updated_stats["harvested_indicators"] == 1
    assert updated_stats["total_dimensions"] == 1
    assert updated_stats["total_members"] == 2
```

- [ ] **Step 2: Run test to confirm failure**
Run: `uv run pytest tests/test_catalog_harvester.py -k test_store_harvest_columns_and_status`
Expected output: Fails with `AttributeError` or missing parameters.

- [ ] **Step 3: Implement schema migration and harvest status queries in `store.py`**
Modify `init_semantic_tables`:
Add `ALTER TABLE` migrations or initialize `indicator_dimensions` with `harvested_at TEXT, content_hash TEXT`.
Add methods `get_harvested_indicator_ids()` and `get_harvest_stats()`.
Update `store_indicator_dimensions` to record `content_hash` and `harvested_at`.

- [ ] **Step 4: Run test to confirm passing**
Run: `uv run pytest tests/test_catalog_harvester.py -k test_store_harvest_columns_and_status`
Expected output: 1 passed.

- [ ] **Step 5: Run full non-integration test suite**
Run: `uv run pytest -m "not integration"`
Ensure all 236+ tests pass without regression.

- [ ] **Step 6: Commit changes**
Run:
```bash
git add src/statscepal/catalog/store.py src/statscepal/catalog/models.py tests/test_catalog_harvester.py
git commit -m "feat(catalog): extend SQLite semantic schema with content hash and harvest tracking"
```

---

### Task 2: Offline Mock Fixtures and `Harvester` Core Engine

**Files:**
- Create: `tests/fixtures/dimensions/indicator_3328.json`
- Create: `tests/fixtures/dimensions/indicator_3342.json`
- Create: `src/statscepal/catalog/harvester.py`
- Modify: `tests/test_catalog_harvester.py`

**Interfaces:**
- Consumes: `CepalStatClient`, `DimensionManager`, `CatalogStore`.
- Produces:
  - `CatalogHarvester(client: CepalStatClient, store: CatalogStore, rate_limit_delay: float = 0.05, max_retries: int = 3)`
  - `harvester.harvest(indicator_ids: list[int] | None = None, resume: bool = True, force: bool = False, on_progress: Callable[[int, int, int], None] | None = None) -> HarvestSummary`
  - `HarvestSummary`: dataclass or Pydantic model with `total_target`, `already_harvested`, `newly_harvested`, `failed_ids`, `duration_seconds`.

- [ ] **Step 1: Create JSON fixtures for offline testing**
Generate hermetic payload fixtures for indicator `3328` (Area, Sexo, Años) and indicator `3342` (Área, Sexo, Etnia, Pobreza).

- [ ] **Step 2: Write failing unit test for `CatalogHarvester`**

```python
# In tests/test_catalog_harvester.py
import json
from pathlib import Path
import respx
import httpx
from statscepal.catalog.harvester import CatalogHarvester
from statscepal.client import CepalStatClient

@respx.mock
def test_harvester_resumable_and_retry(tmp_path):
    db_path = tmp_path / "test_catalog.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()
    
    # Pre-populate master_indicators with 2 indicators
    with store._get_connection() as conn:
        conn.execute("INSERT INTO master_indicators (indicator_id, name) VALUES (3328, 'Pobreza')")
        conn.execute("INSERT INTO master_indicators (indicator_id, name) VALUES (3342, 'Pobreza etnica')")

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
    summary = harvester.harvest(resume=True)
    assert summary.newly_harvested == 2
    assert summary.failed_count == 0

    # Second run with resume=True: skips both
    summary_resume = harvester.harvest(resume=True)
    assert summary_resume.already_harvested == 2
    assert summary_resume.newly_harvested == 0
```

- [ ] **Step 3: Run test to confirm failure**
Run: `uv run pytest tests/test_catalog_harvester.py -k test_harvester_resumable_and_retry`
Expected output: Fails with `ModuleNotFoundError: No module named 'statscepal.catalog.harvester'`.

- [ ] **Step 4: Implement `CatalogHarvester` in `src/statscepal/catalog/harvester.py`**
- Compute SHA-256 `content_hash` over canonical JSON representation of raw dimension response.
- Query target indicators from `master_indicators` if `indicator_ids` is None.
- Filter out already-harvested indicators if `resume=True` and not `force`.
- Loop over pending IDs with retry loop (max 3 retries, exponential backoff $0.5\text{s}, 1.0\text{s}, 2.0\text{s}$) on network timeout or HTTP 5xx.
- Persist dimensions via `store.store_indicator_dimensions()`.
- Return structured `HarvestSummary`.

- [ ] **Step 5: Run test to confirm passing**
Run: `uv run pytest tests/test_catalog_harvester.py -k test_harvester_resumable_and_retry`
Expected output: 1 passed.

- [ ] **Step 6: Add error resilience tests**
Add `test_harvester_handles_http_errors_and_continues` testing that a 404 or 500 on one indicator records it in `failed_ids` without terminating the batch.
Run: `uv run pytest tests/test_catalog_harvester.py`
Expected output: All harvester tests pass.

- [ ] **Step 7: Commit changes**
Run:
```bash
git add src/statscepal/catalog/harvester.py tests/fixtures/dimensions/ tests/test_catalog_harvester.py
git commit -m "feat(catalog): implement CatalogHarvester with resumption, backoff, and content hashing"
```

---

### Task 3: CLI Subcommand `statscepal catalog harvest` & Diagnostics

**Files:**
- Modify: `src/statscepal/cli.py:94-135,320-375`
- Modify: `tests/test_catalog_harvester.py`

**Interfaces:**
- Consumes: `CatalogHarvester`, `CatalogStore`.
- Produces: CLI interface:
  `statscepal catalog harvest [--ids 3328,3342] [--resume] [--force] [--rate 0.05] [--limit 50]`
  Formatted terminal output with summary table and error reporting.

- [ ] **Step 1: Write failing CLI integration test**

```python
# In tests/test_catalog_harvester.py
from statscepal.cli import main
import pytest

@respx.mock
def test_cli_catalog_harvest(capsys, tmp_path, monkeypatch):
    db_path = tmp_path / "test_cli_catalog.db"
    monkeypatch.setenv("STATS_CEPAL_CACHE_DB", str(db_path)) # or override CatalogStore default path
    
    # Setup test DB with 1 indicator
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()
    with store._get_connection() as conn:
        conn.execute("INSERT INTO master_indicators (indicator_id, name) VALUES (3328, 'Pobreza')")

    fixture_3328 = json.loads(Path("tests/fixtures/dimensions/indicator_3328.json").read_text(encoding="utf-8"))
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/3328/dimensions").respond(
        status_code=200, json=fixture_3328
    )

    exit_code = main(["catalog", "harvest", "--ids", "3328"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "Catalog Harvest Complete" in captured.out
    assert "Newly harvested:   1" in captured.out
```

- [ ] **Step 2: Run test to confirm failure**
Run: `uv run pytest tests/test_catalog_harvester.py -k test_cli_catalog_harvest`
Expected output: Fails because `harvest` is not recognized by `catalog_subparsers`.

- [ ] **Step 3: Implement `catalog harvest` parser and handler in `cli.py`**
- Add `harvest_parser` under `catalog_subparsers`.
  - Arguments: `--ids` (comma-separated ints), `--resume` (default True), `--force` (action="store_true"), `--rate` (float, default 0.05), `--limit` (int, optional).
- Implement execution block:
  - Initialize `CatalogStore()` and `CepalStatClient()`.
  - Instantiate `CatalogHarvester`.
  - Print live progress: `[Harvesting] (N/Total) ID: {indicator_id} - {status}`.
  - Print formatted summary block at finish.

- [ ] **Step 4: Run test to confirm passing**
Run: `uv run pytest tests/test_catalog_harvester.py -k test_cli_catalog_harvest`
Expected output: 1 passed.

- [ ] **Step 5: Run regression and full non-integration test suite**
Run:
```bash
uv run pytest tests/test_catalog_harvester.py -v
uv run pytest tests/test_semantic_benchmark_200.py -v
uv run pytest -m "not integration"
```
Ensure all tests pass and 0.00% FSR is preserved.

- [ ] **Step 6: Commit changes**
Run:
```bash
git add src/statscepal/cli.py tests/test_catalog_harvester.py
git commit -m "feat(cli): add 'statscepal catalog harvest' command with progress reporting"
```

---

### Task 4: End-to-End Certification & Live Staging Validation

**Files:**
- Modify: `tests/test_catalog_harvester.py`
- Test: Live optional execution with `--ids 3328,3342` against CEPALSTAT API in staging mode.

**Interfaces:**
- Consumes: All Task 1-3 deliverables.
- Produces: Verification report demonstrating:
  1. Offline unit test suite passing hermetically in CI.
  2. Live harvest of sample indicators (e.g. 3328, 3342) populates actual SQLite database `.statscepal_cache.db`.
  3. `store.get_indicator_dimensions(3328)` and `store.get_indicator_dimensions(3342)` return exact dimensions and members matching official API metadata.

- [ ] **Step 1: Add live smoke test (marked `@pytest.mark.integration`)**
Write an integration test in `tests/test_catalog_harvester.py` that executes live against the API when run with `-m integration`.

- [ ] **Step 2: Execute live test and verify `.statscepal_cache.db`**
Run:
```bash
uv run python -m statscepal.cli catalog harvest --ids 3328,3342 --force
```
Verify terminal output and check database contents:
```bash
uv run python -c "from statscepal.catalog.store import CatalogStore; s = CatalogStore(); print(s.get_harvest_stats()); print([(d.id, d.name, len(d.members)) for d in s.get_indicator_dimensions(3342)])"
```

- [ ] **Step 3: Run full benchmark regression suite**
Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`
Confirm 11/11 passed, 100% accuracy, 0.00% FSR.

- [ ] **Step 4: Commit changes and write completion report**
Run:
```bash
git add tests/test_catalog_harvester.py
git commit -m "test(catalog): certify catalog harvester with hermetic fixtures and live integration test"
```

---

## Plan Self-Review Checklist
- [x] All file paths are exact and verified in workspace.
- [x] All tasks follow strict TDD (write failing test, run red, implement, run green, verify regression, commit).
- [x] Interfaces (consumes/produces) are declared explicitly for each task.
- [x] Hermeticity guaranteed: unit tests use respx/fixtures, live tests marked `integration`.
- [x] Preserves performance invariant $p50 < 0.5\text{ ms}$ and zero facet loss.
