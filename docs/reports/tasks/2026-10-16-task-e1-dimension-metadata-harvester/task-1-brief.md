# Task 1 Brief: Schema Extension and Harvest Status Query in CatalogStore

## Context
- Working Directory: `C:\papx\statscepal`
- Base Commit: `f6b1cf7`
- Plan: `docs/superpowers/plans/2026-10-16-task-e1-dimension-metadata-harvester-plan.md`

## Objectives
1. Modify `src/statscepal/catalog/store.py`:
   - In `init_semantic_tables()`, ensure `indicator_dimensions` has columns `harvested_at TEXT, content_hash TEXT`. If the table already exists, handle schema upgrade/migration gracefully (`ALTER TABLE indicator_dimensions ADD COLUMN ...` or check pragma table_info).
   - In `store_indicator_dimensions()`, accept optional `content_hash: str | None = None` and `harvested_at: str | None = None`. If provided, persist them in `indicator_dimensions` (if not provided, default `harvested_at` to current UTC ISO-8601 string).
   - Implement `get_harvested_indicator_ids() -> set[int]`: returns a set of all indicator IDs present in `indicator_dimensions`.
   - Implement `get_harvest_stats() -> dict[str, int]`: returns dict with `harvested_indicators` (count of distinct indicator_id), `total_dimensions` (count of rows in indicator_dimensions), `total_members` (count of rows in dimension_members).
2. Modify `src/statscepal/catalog/models.py` if needed to export any helper models.
3. Follow strict TDD:
   - Create `tests/test_catalog_harvester.py` with test `test_store_harvest_columns_and_status`.
   - Run red test: `uv run pytest tests/test_catalog_harvester.py -k test_store_harvest_columns_and_status`
   - Implement changes in `store.py`.
   - Run green test: `uv run pytest tests/test_catalog_harvester.py -k test_store_harvest_columns_and_status`
   - Run all non-integration tests: `uv run pytest -m "not integration"`
4. Commit:
   `git add src/statscepal/catalog/store.py src/statscepal/catalog/models.py tests/test_catalog_harvester.py`
   `git commit -m "feat(catalog): extend SQLite semantic schema with content hash and harvest tracking"`
5. Write report to `.superpowers/sdd/2026-10-16-task-e1-dimension-metadata-harvester/task-1-report.md`.
