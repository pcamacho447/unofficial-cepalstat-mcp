# Task 3 Brief: CLI Subcommand `statscepal catalog harvest` & Diagnostics

## Context
- Working Directory: `C:\papx\statscepal`
- Base Commit: `5b61ff1`
- Plan: `docs/superpowers/plans/2026-10-16-task-e1-dimension-metadata-harvester-plan.md`

## Objectives
1. Modify `src/statscepal/cli.py`:
   - Under `catalog_subparsers`, register `harvest` subcommand:
     - `--ids`: Comma-separated list of indicator IDs (e.g. `--ids 3328,3342`). Optional; if omitted, targets all catalog indicators.
     - `--no-resume`: Flag to disable resumption. (Default is resume=True).
     - `--force`: Force re-harvesting of all targets even if already harvested.
     - `--rate`: Float, inter-request rate limit delay in seconds (default: 0.05).
     - `--limit`: Optional integer, maximum number of pending indicators to process in this run.
   - Implement CLI execution handler for `parsed.catalog_command == "harvest"`:
     - Parses `--ids` (splitting comma-separated strings into `list[int]`).
     - Instantiates `store = CatalogStore()` and ensures `store.init_semantic_tables()`.
     - Instantiates `client = CepalStatClient()` and `harvester = CatalogHarvester(client=client, store=store, rate_limit_delay=parsed.rate)`.
     - Displays banner:
       ```
       ======================================================================
       CEPALSTAT Dimension Metadata Harvester
       ======================================================================
       Target: ...
       Mode:   ...
       ======================================================================
       ```
     - Prints progress lines during execution via callback:
       `[Harvesting] (idx/total) Indicator ID: {id} - {status}`
     - Prints summary block upon completion:
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
     - Exits with code 0 if successful (even if some individual indicators failed, as long as the run completed), or 1 on unhandled fatal error.
2. Follow strict TDD:
   - In `tests/test_catalog_harvester.py`:
     - Add `test_cli_catalog_harvest_success` using `respx.mock` and CLI invocation.
     - Add `test_cli_catalog_harvest_with_ids_and_force` verifying CLI options.
   - Run red test: `uv run pytest tests/test_catalog_harvester.py -k test_cli_catalog_harvest`
   - Implement CLI changes in `src/statscepal/cli.py`.
   - Run green test: `uv run pytest tests/test_catalog_harvester.py -k test_cli_catalog_harvest`
   - Run full non-integration suite: `uv run pytest -m "not integration"`
3. Commit:
   `git add src/statscepal/cli.py tests/test_catalog_harvester.py`
   `git commit -m "feat(cli): add 'statscepal catalog harvest' command with progress reporting"`
4. Write report to `.superpowers/sdd/2026-10-16-task-e1-dimension-metadata-harvester/task-3-report.md`.
