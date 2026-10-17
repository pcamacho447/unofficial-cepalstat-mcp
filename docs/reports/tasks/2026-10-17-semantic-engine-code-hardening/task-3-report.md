# Task 3 Report: Household Survey Family Temporal Calendar Propagation & Dynamic Empirical Anchor Rescue

## Executive Summary
- **Status**: DONE
- **Commit**: `7c2f146` (`feat(semantic): propagate BADEHOG temporal anchors and add dynamic DataFrame anchor rescue`)
- **Base Commit**: `6927d25`
- **Test Summary**: 294 passed, 3 deselected in 32.98s; 100.0% Top-1 Accuracy and 0.00% False Substitution Rate on the 200-question benchmark.

## Implementation Details

### 1. BADEHOG Household Survey Matrix Propagation (`src/statscepal/semantic/registry.py`)
- Defined `BADEHOG_SURVEY_INDICATORS: tuple[int, ...] = (3328, 3329, 3330, 3339, 3340, 3341, 3342, 3345, 3289)`.
- Populated `TEMPORAL_AVAILABILITY_MATRIX` for all 9 BADEHOG household survey indicators:
  - **Chile (`CHL`)**: 2020 (`OBSERVATION_EXISTING`), 2021 (`PERIOD_UNOBSERVED`, anchors: 2020, 2022), 2022 (`OBSERVATION_EXISTING`).
  - **Mexico (`MEX`)**: 2020 (`OBSERVATION_EXISTING`), 2021 (`PERIOD_UNOBSERVED`, anchors: 2020, 2022), 2022 (`OBSERVATION_EXISTING`).
  - **Brazil (`BRA`)**: 2021 (`OBSERVATION_EXISTING`).
  - **Peru (`PER`)**: 2021 (`OBSERVATION_EXISTING`).
  - **Costa Rica (`CRI`)**: 2022 (`OBSERVATION_EXISTING`).

### 2. Dynamic Empirical Anchor Discovery & Rescue (`src/statscepal/semantic/fetcher.py`)
- Enhanced `code_by_name` and `_get_row_country_code` to reliably map ISO3 / `country_code` values and accents to standardized uppercase country codes.
- Added dynamic empirical anchor discovery prior to Step 4 temporal filtering:
  - Inspects `filtered_df` (after unconstrained dimension collapse) when `requested_year_set` is non-empty and a requested country has no observations in `requested_year_set` within `filtered_df`.
  - Determines available years for that country with non-null values.
  - Dynamically calculates `prev_anchor = max((y for y in avail_years if y < req_y), default=None)` and `next_anchor = min((y for y in avail_years if y > req_y), default=None)`.
  - Registers discovered anchors in `country_anchor_map[c_code]`.
  - The existing anchor rescue logic seamlessly extracts and tags the anchor rows (`is_anchor=True`, `anchor_for_years=[req_y]`), setting `has_rescued_anchors=True` and setting `observation_exists=True`.

### 3. Unit Tests (`tests/test_semantic_multi_year.py`)
- Added `test_badehog_family_indicators_report_chile_2021_anchors_in_stage5` verifying that indicators 3342, 3341, 3329, and 3289 detect Chile's 2021 CASEN gap in Stage 5 resolution.
- Added `test_fetcher_dynamically_rescues_empirical_anchors_even_when_unindexed_in_stage5` verifying that the fetcher dynamically computes and rescues anchor years from empirical DataFrames when an unobserved gap was not indexed ahead of time in Stage 5.

## Verification Evidence
1. **Red Test Phase**:
   - `uv run pytest tests/test_semantic_multi_year.py -k "test_badehog_family_indicators or test_fetcher_dynamically_rescues" -v`
   - Both tests failed as expected (`RESOLVED` instead of `RESOLVED_WITH_ANCHORS`; `observation_exists == False` instead of `True`).
2. **Green Test Phase**:
   - `uv run pytest tests/test_semantic_multi_year.py -v`: 24 passed in 5.88s.
3. **200-Question Benchmark**:
   - `uv run pytest tests/test_semantic_benchmark_200.py -v`: 11 passed in 1.25s (100.0% Top-1 Accuracy, 0.00% False Substitution Rate).
4. **Full Test Suite (Hermetic non-integration)**:
   - `uv run pytest -m "not integration"`: 294 passed, 3 deselected in 32.98s.

## Concerns / Notes
- None. Offline hermeticity strictly preserved with 0 live network calls.
