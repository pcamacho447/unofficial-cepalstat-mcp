# Task 6 Brief: Modular Decomposition of `SemanticDataFetcher.fetch_resolved_data` & Test/Lexicon Hygiene (`AI-7` & `AI-8`)

**Implementer:** Amelia, Senior Developer  
**Plan:** [`docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md)  
**Base Commit:** `065f29a`  

---

## 1. What to Build

### A. Modular Decomposition of `SemanticDataFetcher.fetch_resolved_data` (`AI-7`)
In `src/statscepal/semantic/fetcher.py`:
`fetch_resolved_data` has grown into a 765-line monolithic method. Decompose it into cohesive private helper methods on `SemanticDataFetcher`:
1. `_prepare_empirical_fetch(self, response: SemanticResolutionResponse) -> tuple[int, pd.DataFrame]`
   - Resolves `empirical_id = self._resolve_empirical_indicator_id(response)`.
   - Strips `SYNTHETIC_DIMENSION_MEMBER_IDS` from `member_ids`.
   - Calls `_load_indicator_data(empirical_id, member_ids)`.
2. `_resolve_geography(self, df: pd.DataFrame, response: SemanticResolutionResponse) -> tuple[str | None, list[str], list[str], bool, dict[str, str], dict[str, Any]]`
   - Identifies human-readable country column vs code column.
   - Extracts target countries, determines `is_multi_country`.
   - Builds `country_anchor_map` and `code_by_name`.
3. `_apply_dimension_filters(self, df: pd.DataFrame, response: SemanticResolutionResponse) -> tuple[pd.DataFrame, set[str]]`
   - Step 2: Matches dimension columns with aliases.
   - Filters rows using member name alias closure and IDs.
   - Tracks `filtered_dim_cols`.
4. `_apply_temporal_and_anchors(self, df: pd.DataFrame, response: SemanticResolutionResponse, country_col: str | None, filtered_dim_cols: set[str], country_anchor_map: dict[str, Any], is_multi_country: bool, code_by_name: dict[str, str]) -> tuple[pd.DataFrame, str | None, bool, list[int]]`
   - Identifies `year_col` (including decade columns).
   - Calls `_filter_unconstrained_dimensions`.
   - Discovers dynamic empirical anchors for `missing_requested = requested_year_set - avail_years`.
   - Filters temporal constraints (single year, multi-year range, or latest-year cross section per country).
5. `_format_payload(self, df: pd.DataFrame, response: SemanticResolutionResponse, empirical_id: int, year_col: str | None, country_col: str | None, is_multi_country: bool, is_multi_year: bool, has_breakdown: bool, has_rescued_anchors: bool, country_anchor_map: dict[str, Any], requested_year_set: set[int], code_by_name: dict[str, str], target_year: int | None) -> dict[str, Any]`
   - Formats series items and observation metadata.
   - Tags `is_anchor` and `notes`.
   - Returns structured payload.

`fetch_resolved_data` itself becomes a clean 50-60 line orchestrator coordinating these stages.

### B. Clean up `COUNTRY_LEXICON` Dead `"ñ"` Keys (`AI-8`)
In `src/statscepal/semantic/parser.py:58-128`:
Because `clean = strip_accents(query)` converts `"ñ"` to `"n"` before scanning `COUNTRY_LEXICON`, entries with `"ñ"` (e.g. `"brasileño"`, `"panameño"`, `"hondureño"`, `"salvadoreño"`) are unreachable dead keys. Remove the 14 dead accented keys, keeping `"brasileno"`, `"panameno"`, `"hondureno"`, `"salvadoreno"`.

### C. Differentiate Multi-Country Test Max Years (`AI-8`)
In `tests/test_semantic_fetcher.py:273-305`:
In `test_fetcher_multi_country_without_year_filters_to_latest_year_per_country`:
Change Perú's max year to 2021 (e.g. 2019 and 2021) and Chile's max year to 2022 (e.g. 2017 and 2022).
Verify that Perú returns 2021 (value 27.5) and Chile returns 2022 (value 6.5), proving that per-country `groupby` maximum operates correctly and does not collapse to a global table maximum.

---

## 2. Test-Driven Development (TDD) Workflow

1. Update `test_fetcher_multi_country_without_year_filters_to_latest_year_per_country` in `tests/test_semantic_fetcher.py` and run it:
   `uv run pytest tests/test_semantic_fetcher.py -k test_fetcher_multi_country_without_year_filters_to_latest_year_per_country -v`
2. Remove dead `"ñ"` keys in `src/statscepal/semantic/parser.py`.
3. Modularize `fetch_resolved_data` in `src/statscepal/semantic/fetcher.py`.
4. Run full verification:
   `uv run pytest tests/test_semantic_fetcher.py -v`
   `uv run pytest tests/test_semantic_benchmark_200.py -v`
   `uv run pytest tests/test_semantic_facet_coverage.py -v`
   `uv run pytest -m "not integration"`
5. Commit:
   `git add src/statscepal/semantic/fetcher.py src/statscepal/semantic/parser.py tests/test_semantic_fetcher.py`
   `git commit -m "refactor(semantic): modularize fetch_resolved_data into stage helpers and clean up COUNTRY_LEXICON"`
6. Write your task report to `C:\papx\statscepal\.superpowers\sdd\2026-10-17-retrospective-remediation-and-hardening-plan\task-6-report.md`.
