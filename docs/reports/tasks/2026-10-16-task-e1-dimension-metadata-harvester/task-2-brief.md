# Task 2 Brief: Offline Mock Fixtures and CatalogHarvester Core Engine

## Context
- Working Directory: `C:\papx\statscepal`
- Base Commit: `a78e1a5`
- Plan: `docs/superpowers/plans/2026-10-16-task-e1-dimension-metadata-harvester-plan.md`

## Objectives
1. Create hermetic offline JSON fixtures:
   - `tests/fixtures/dimensions/indicator_3328.json`: Valid CEPALSTAT dimensions response for Indicator 3328 (e.g. Dimensions: Área geográfica, Sexo, Años; with member IDs).
   - `tests/fixtures/dimensions/indicator_3342.json`: Valid CEPALSTAT dimensions response for Indicator 3342 (Dimensions: Área geográfica, Sexo, Tipo de etnia, Situación de pobreza, Años; with member IDs).
2. Create `src/statscepal/catalog/harvester.py`:
   - Class `CatalogHarvester(client: CepalStatClient, store: CatalogStore, rate_limit_delay: float = 0.05, max_retries: int = 3, retry_backoff_base: float = 0.5)`
   - Computes deterministic SHA-256 `content_hash` over raw JSON bytes/canonical payload.
   - Method `harvest(indicator_ids: list[int] | None = None, resume: bool = True, force: bool = False, on_progress: Callable[[int, int, int, str], None] | None = None) -> HarvestSummary`:
     - If `indicator_ids` is None, loads all indicators from `master_indicators` via store (`SELECT indicator_id FROM master_indicators ORDER BY indicator_id ASC`).
     - If `resume` is True and not `force`: filters out indicators already in `store.get_harvested_indicator_ids()`.
     - Iterates through pending indicators:
       - Applies `time.sleep(self.rate_limit_delay)` if `rate_limit_delay > 0`.
       - Implements retry loop with exponential backoff on transient errors (HTTP 5xx, timeouts, connection errors).
       - Fetches dimensions via `client.get(f"/cepalstat/api/v1/indicator/{id}/dimensions")`.
       - Decodes and parses into `list[Dimension]`.
       - Persists via `store.store_indicator_dimensions(indicator_id, dimensions, content_hash=hash, harvested_at=utc_iso)`.
       - If failed after retries, records indicator_id in `summary.failed_ids` without aborting the entire run.
       - Invokes `on_progress(current_idx, total_count, indicator_id, status)` callback if supplied.
     - Returns `HarvestSummary(total_target=..., already_harvested=..., newly_harvested=..., failed_ids=..., duration_seconds=...)`.
3. Follow strict TDD:
   - In `tests/test_catalog_harvester.py`:
     - Add `test_harvester_resumable_and_retry` using `respx.mock` and fixtures.
     - Add `test_harvester_handles_http_errors_and_continues` testing 404 / 500 error recording in `failed_ids`.
   - Run red test: `uv run pytest tests/test_catalog_harvester.py -k "test_harvester"`
   - Implement `harvester.py`.
   - Run green test: `uv run pytest tests/test_catalog_harvester.py`
   - Run full non-integration suite: `uv run pytest -m "not integration"`
4. Commit:
   `git add src/statscepal/catalog/harvester.py tests/fixtures/dimensions/ tests/test_catalog_harvester.py`
   `git commit -m "feat(catalog): implement CatalogHarvester with resumption, backoff, and content hashing"`
5. Write report to `.superpowers/sdd/2026-10-16-task-e1-dimension-metadata-harvester/task-2-report.md`.
