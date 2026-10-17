# Task 3 Brief: Harvested Dimension Audit Engine & 'catalog facet-audit' CLI

## Context
- Working Directory: `C:\papx\statscepal`
- Base Commit: `27dada9`
- Plan: `docs/superpowers/plans/2026-10-16-task-e2-declarative-facet-ontology-plan.md`

## Objectives
1. Modify `src/statscepal/catalog/store.py`:
   - Implement `CatalogStore.get_distinct_harvested_dimensions(self) -> list[dict[str, Any]]`:
     - Queries `indicator_dimensions` grouping by `dim_id` and `dim_name`.
     - Returns list of dicts: `[{"dim_id": int, "dim_name": str, "indicator_count": int, "sample_indicator_ids": list[int]}]`.
     - Ordered by `indicator_count DESC, dim_id ASC`.
     - If table is empty or does not exist, returns empty list `[]`.
2. Ensure `src/statscepal/semantic/facet_ontology.py` has complete audit method:
   - `FacetOntology.audit_dimensions(self, dimension_rows: list[dict[str, Any]]) -> FacetAuditReport`.
   - `FacetAuditReport` model:
     - `total_distinct_dimensions: int`
     - `structural_dimensions: list[dict[str, Any]]`
     - `mapped_dimensions: dict[str, list[dict[str, Any]]]`
     - `unmapped_dimensions: list[dict[str, Any]]`
     - `coverage_ratio: float`
     - `to_dict() / model_dump()`
3. Modify `src/statscepal/cli.py`:
   - Under `catalog_subparsers`, register `facet-audit` subcommand:
     - Flag `--json`: output audit report in JSON format.
   - Implement handler:
     - Instantiates `store = CatalogStore()` and `ontology = DEFAULT_FACET_ONTOLOGY`.
     - Calls `store.init_semantic_tables()`.
     - Fetches `distinct_dims = store.get_distinct_harvested_dimensions()`.
     - Computes `report = ontology.audit_dimensions(distinct_dims)`.
     - If `--json`, prints formatted JSON and returns 0.
     - Otherwise prints ASCII summary report:
       ```
       ======================================================================
       CEPALSTAT Facet Ontology Audit
       ======================================================================
       Total distinct dimensions: ...
       Structural dimensions:     ... (Country, Time)
       Mapped facet dimensions:   ...
       Unmapped dimensions:       ...
       Coverage ratio:            ...%
       ======================================================================
       Mapped Dimensions by Facet:
         - [facet_key]: N dimension(s) (... names / IDs ...)
       ...
       Unmapped Dimensions (Gap Report):
         - [dim_id] dim_name (occurs in N indicators)
       ======================================================================
       ```
     - Returns 0.
4. Follow strict TDD:
   - In `tests/test_semantic_facet_ontology.py`:
     - Add `test_store_and_ontology_facet_audit` verifying `store.get_distinct_harvested_dimensions()`, `ontology.audit_dimensions()`, and CLI `main(["catalog", "facet-audit"])`.
     - Add `test_cli_facet_audit_json` verifying JSON output formatting.
   - Run red test: `uv run pytest tests/test_semantic_facet_ontology.py -k audit`
   - Implement changes in `store.py` and `cli.py`.
   - Run green test: `uv run pytest tests/test_semantic_facet_ontology.py`
   - Run benchmark and full non-integration test suite:
     - `uv run pytest tests/test_semantic_benchmark_200.py -v`
     - `uv run pytest -m "not integration"`
5. Commit:
   `git add src/statscepal/catalog/store.py src/statscepal/semantic/facet_ontology.py src/statscepal/cli.py tests/test_semantic_facet_ontology.py`
   `git commit -m "feat(semantic): add harvested dimension audit engine and 'catalog facet-audit' CLI"`
6. Write report to `.superpowers/sdd/2026-10-16-task-e2-declarative-facet-ontology/task-3-report.md`.
