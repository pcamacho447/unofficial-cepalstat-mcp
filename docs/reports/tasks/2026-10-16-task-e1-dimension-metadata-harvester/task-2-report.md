# Task 2 Report: Offline Mock Fixtures and CatalogHarvester Core Engine

## Executive Summary
- **Task**: Task 2 of Task E1 (Offline Mock Fixtures and CatalogHarvester Core Engine)
- **Status**: DONE
- **Commit**: `5b61ff18a69f78fc340b993579dc07ebfc2a3988` (`5b61ff1`)
- **Developer**: Amelia (Senior Developer)
- **Working Directory**: `C:\papx\statscepal`

---

## Changes Implemented

### 1. Hermetic Offline Mock Fixtures (`tests/fixtures/dimensions/`)
- Created `tests/fixtures/dimensions/indicator_3328.json`: Valid CEPALSTAT dimensions response for Indicator 3328 containing dimensions: `País__ESTANDAR`, `Área geográfica`, `Tipo de pobreza`, `Sexo__ESTANDAR`, `Años__ESTANDAR` with valid member IDs.
- Created `tests/fixtures/dimensions/indicator_3342.json`: Valid CEPALSTAT dimensions response for Indicator 3342 containing dimensions: `País__ESTANDAR`, `Área geográfica`, `Sexo__ESTANDAR`, `Tipo de etnia`, `Situación de pobreza`, `Años__ESTANDAR` with valid member IDs.

### 2. CatalogHarvester Core Engine (`src/statscepal/catalog/harvester.py`)
- Implemented `CatalogHarvester(client, store, rate_limit_delay=0.05, max_retries=3, retry_backoff_base=0.5)`:
  - `compute_content_hash(payload)`: Deterministic SHA-256 calculation over canonical sorted-key JSON bytes or raw bytes.
  - `_parse_dimensions(raw_response)`: Robustly decodes and validates CEPALSTAT dimensions response body into `list[Dimension]` with nested `list[Member]`.
  - `_notify_progress(on_progress, current_idx, total_count, indicator_id, status)`: Dual-compatible callback dispatcher supporting both 4-argument `(idx, total, ind_id, status)` and 3-argument `(idx, total, ind_id)` signatures.
  - `harvest(indicator_ids=None, resume=True, force=False, on_progress=None) -> HarvestSummary`:
    - Queries all indicators from `master_indicators` via SQLite store if `indicator_ids` is None.
    - Checkpoint resumption: filters out indicators already present in `store.get_harvested_indicator_ids()` unless `force=True`.
    - Rate limiting: enforces configurable `rate_limit_delay` between requests.
    - Transient fault tolerance: retries with exponential backoff on transient errors (HTTP 5xx, HTTP 429, connection timeouts, `httpx.RequestError`).
    - Error isolation: non-transient errors (e.g. 404 Not Found) or exhausted retries are recorded in `failed_ids` without terminating the batch.
    - Deterministic persistence: stores dimensions with computed `content_hash` and UTC ISO timestamp.
    - Returns structured `HarvestSummary`.

### 3. Comprehensive Unit Tests (`tests/test_catalog_harvester.py`)
- `test_harvester_resumable_and_retry`: Validates complete batch harvest, content hash persistence, resume skipping of already-harvested indicators, and forced re-harvesting.
- `test_harvester_handles_http_errors_and_continues`: Validates that HTTP 404 (non-transient) and HTTP 500 (exhausted retry) failures are recorded in `failed_ids` while succeeding indicators in the batch are still harvested.
- `test_harvester_retries_transient_error_and_succeeds`: Verifies retry with exponential backoff recovers when a service returns transient 503 before succeeding on next attempt.
- `test_harvester_explicit_indicator_ids_and_3arg_callback`: Validates explicit target list and backward compatibility with 3-arg progress callbacks.

---

## Verification & Test Results

### 1. TDD Red Phase
```
uv run pytest tests/test_catalog_harvester.py -k "test_harvester"
Result: FAILED (ModuleNotFoundError: No module named 'statscepal.catalog.harvester')
```

### 2. TDD Green Phase
```
uv run pytest tests/test_catalog_harvester.py
Result: 7 passed in 5.59s
```

### 3. Full Non-Integration Test Suite
```
uv run pytest -m "not integration"
Result: 243 passed, 2 deselected in 53.97s
```
Zero regressions across all existing tests (236 baseline + 3 Task 1 tests + 4 Task 2 tests). Strict offline hermeticity maintained without live external network calls.
