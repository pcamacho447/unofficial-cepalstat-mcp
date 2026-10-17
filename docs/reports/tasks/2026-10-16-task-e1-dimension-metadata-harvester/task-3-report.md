# Task 3 Report: CLI Subcommand `statscepal catalog harvest` & Diagnostics

**Status:** DONE  
**Commit:** `c19b413cb139c3591471db57bcd42957627d2916` (`c19b413`)  
**Base Commit:** `5b61ff1`  
**Date:** 2026-10-16  

---

## 1. Summary of Changes

### 1.1 CLI Argument Parser (`src/statscepal/cli.py`)
- Registered `harvest` subcommand under `catalog_subparsers`.
- Supported options:
  - `--ids`: Comma-separated list of indicator IDs (e.g. `3328,3342`).
  - `--resume` (default `True`): Resumes harvesting by skipping already harvested indicators.
  - `--no-resume` (`resume=False`): Disables checkpoint skipping.
  - `--force`: Force re-harvesting of all target indicators even if already recorded in the SQLite database.
  - `--rate`: Inter-request delay in seconds for API rate limiting (default: `0.05`s).
  - `--limit`: Maximum number of pending/target indicators to harvest in the run.

### 1.2 CLI Command Execution Handler (`src/statscepal/cli.py`)
- Instantiates `store = CatalogStore()` and initializes semantic relational tables via `store.init_semantic_tables()`.
- Instantiates `client = CepalStatClient()` and `harvester = CatalogHarvester(client=client, store=store, rate_limit_delay=parsed.rate)`.
- Validates `--ids` integers cleanly, reporting errors with exit code 1 on malformed inputs.
- Prints banner with target description and execution mode:
  ```
  ======================================================================
  CEPALSTAT Dimension Metadata Harvester
  ======================================================================
  Target: ...
  Mode:   ...
  ======================================================================
  ```
- Emits real-time progress updates via callback:
  `[Harvesting] (idx/total) Indicator ID: {id} - {status}`
- Prints aligned summary statistics block upon run completion:
  ```
  ======================================================================
  Catalog Harvest Complete
  ======================================================================
  Total target:      ...
  Already harvested: ...
  Newly harvested:   ...
  Failed:            ...
  Duration:          ...s
  ======================================================================
  ```
- Returns exit code `0` on successful run (including non-fatal failed indicators recorded in `failed_ids`), or `1` on unhandled fatal exceptions.

---

## 2. Test Verification

### 2.1 Unit & CLI Tests (`tests/test_catalog_harvester.py`)
- `test_cli_catalog_harvest_success`:
  - Verified default all-indicators harvest behavior with mock API endpoint.
  - Confirmed banner display, live progress emission, summary block formatting, and SQLite persistence.
- `test_cli_catalog_harvest_with_ids_and_force`:
  - Verified `--ids 3342` filtering.
  - Verified resumption behavior (`Already harvested: 1`, `Newly harvested: 0`).
  - Verified `--force` behavior (`Mode: Force re-harvest`, `Newly harvested: 1`).
- `test_cli_catalog_harvest_invalid_ids`:
  - Verified validation of `--ids` argument and error exit code 1.

### 2.2 Test Results
- Target tests: `tests/test_catalog_harvester.py` (10 passed) and `tests/test_catalog_cli.py` (9 passed).
- Full non-integration test suite:
  ```
  uv run pytest -m "not integration"
  ===================== 246 passed, 2 deselected in 56.14s ======================
  ```
- Strict offline hermeticity preserved with zero regressions.

---

## 3. Artifacts & Deliverables
- `src/statscepal/cli.py`: CLI parser registration and command handler.
- `tests/test_catalog_harvester.py`: CLI automated unit tests with `respx.mock`.
