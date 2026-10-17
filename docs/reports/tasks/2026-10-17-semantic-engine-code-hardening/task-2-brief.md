# Task 2 Brief: Implicit Aggregate Filtering for Unconstrained DataFrame Dimensions & Latest-Year Cross-Sections in SemanticDataFetcher

Plan: `docs/superpowers/plans/2026-10-17-semantic-engine-code-hardening-plan.md`

## Requirements
1. In `src/statscepal/semantic/fetcher.py`:
   - Add helper constants and method `_filter_unconstrained_dimensions(self, df: pd.DataFrame, filtered_dim_cols: set[str], country_col: str | None, year_col: str | None) -> pd.DataFrame` to `SemanticDataFetcher`:
     - Identifies any non-structural, non-meta dimension column in `df` (not in `filtered_dim_cols`, not `country_col`, not `year_col`, not in `_STRUCTURAL_AND_META_COLS`).
     - If that column has `> 1` unique values, automatically filters `df` to its official aggregate member (`"total"`, `"ambos sexos"`, `"jefe ambos sexos"`, `"nacional"`, `"total nacional"`, `"total pobreza"`, `"pobreza"`, `"indice general"`, `"general"`, `"todas las edades"`).
     - This guarantees that unconstrained dimensions (like `Sexo__ESTANDAR` on indicator 3342 or `Sexo jefatura de hogar` on indicator 3345) never multiply rows into duplicate Cartesian series.
   - Track `filtered_dim_cols: set[str] = set()` in Step 2 of `fetch_resolved_data`, and call `filtered_df = self._filter_unconstrained_dimensions(filtered_df, filtered_dim_cols, country_col, year_col)` after year column identification.
   - In Step 4 (`Filter by temporal constraints`):
     - When `target_year is None`, `not target_years`, and `time_mode == "SINGLE"`, and `(is_multi_country or has_breakdown)`:
       - Filter `filtered_df` to the latest available year per country (if `country_col` is present and `is_multi_country`), or to the overall latest available year with a valid numeric observation.
       - This guarantees that multi-country or breakdown queries without an explicit year (e.g. `"pobreza en peru y chile"`) return only the latest cross-section instead of dumping all decades since 1990.

2. In `tests/test_semantic_fetcher.py`:
   - Add test `test_fetcher_collapses_unconstrained_dataframe_dimensions_to_aggregate_members` verifying that unbound DataFrame dimensions (e.g. `Sexo__ESTANDAR` in 3342) collapse to `Ambos sexos` rather than returning 3 rows per year.
   - Add test `test_fetcher_multi_country_without_year_filters_to_latest_year_per_country` verifying that a multi-country query with no year specified returns exactly 1 latest-year observation per country.

3. Global Constraints:
   - Python 3.10+ modern typing syntax.
   - All 290+ existing non-integration tests must pass without regression.
   - Maintain 100.0% Top-1 Accuracy and 0.00% False Substitution Rate on the 200-question benchmark (`tests/test_semantic_benchmark_200.py`) and facet-coverage benchmark (`tests/test_semantic_facet_coverage.py`).
   - Resolution latency p50 < 0.5 ms.
   - Hermetic offline tests (no live network calls).

## Verification Commands
- `uv run pytest tests/test_semantic_fetcher.py -v`
- `uv run pytest tests/test_semantic_multi_year.py -v`
- `uv run pytest tests/test_semantic_benchmark_200.py -v`
- `uv run pytest -m "not integration"`
