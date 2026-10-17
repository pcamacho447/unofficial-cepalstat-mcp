# Task 4 Brief: End-to-End Certification & Live Staging Validation

## Context
- Working Directory: `C:\papx\statscepal`
- Base Commit: `c19b413`
- Plan: `docs/superpowers/plans/2026-10-16-task-e1-dimension-metadata-harvester-plan.md`

## Objectives
1. Implement End-to-End Live Staging test in `tests/test_catalog_harvester.py`:
   - Add a test marked `@pytest.mark.integration` (`test_live_harvest_smoke_indicator_dimensions`):
     - Uses `CepalStatClient()` live against `https://api-cepalstat.cepal.org`.
     - Executes `CatalogHarvester.harvest(indicator_ids=[3328, 3342], force=True)`.
     - Asserts that dimensions are fetched and stored in SQLite.
     - Asserts that `store.get_indicator_dimensions(3328)` contains Area ("Área geográfica") and `store.get_indicator_dimensions(3342)` contains Etnia ("Tipo de etnia") with matching member IDs.
2. Execute live smoke test in CLI against local SQLite database:
   - Run `uv run python -m statscepal.cli catalog harvest --ids 3328,3342 --force`
   - Verify console output, duration, and metrics.
   - Inspect physical `.statscepal_cache.db` to ensure rows are populated in `indicator_dimensions` and `dimension_members`.
3. Certify that all offline tests and benchmark invariants pass:
   - `uv run pytest tests/test_catalog_harvester.py -v`
   - `uv run pytest tests/test_semantic_benchmark_200.py -v`
   - `uv run pytest -m "not integration"`
4. Commit:
   `git add tests/test_catalog_harvester.py`
   `git commit -m "test(catalog): certify catalog harvester with hermetic fixtures and live integration test"`
5. Write final Task 4 report to `.superpowers/sdd/2026-10-16-task-e1-dimension-metadata-harvester/task-4-report.md`.
