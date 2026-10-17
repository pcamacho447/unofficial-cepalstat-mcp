# Task 3 Brief: Household Survey Family Temporal Calendar Propagation & Dynamic Empirical Anchor Rescue

## Mission
1. Propagate BADEHOG household survey calendar availability matrix across all 9 household survey indicators (`3328, 3329, 3330, 3339, 3340, 3341, 3342, 3345, 3289`) in `src/statscepal/semantic/registry.py`.
   - Chile (`CHL`): 2020 existing, 2021 unobserved (anchors: 2020, 2022), 2022 existing.
   - Mexico (`MEX`): 2020 existing, 2021 unobserved (anchors: 2020, 2022), 2022 existing.
   - Brazil (`BRA`): 2021 existing.
   - Peru (`PER`): 2021 existing.
   - Costa Rica (`CRI`): 2022 existing.
2. Implement dynamic empirical anchor discovery in `SemanticDataFetcher.fetch_resolved_data` (`src/statscepal/semantic/fetcher.py`):
   - When `requested_year_set` is non-empty and a requested country has no observations in `requested_year_set` within `filtered_df`, dynamically inspect `filtered_df` (before year filtering) for that country's available years.
   - Identify `prev_anchor = max((y for y in avail_years if y < req_y), default=None)` and `next_anchor = min((y for y in avail_years if y > req_y), default=None)`.
   - Register them in `country_anchor_map[c_code]` so the existing anchor rescue logic rescues those rows with `is_anchor=True`, `anchor_for_years=[req_y]`, and sets `has_rescued_anchors=True`.
3. Add unit tests in `tests/test_semantic_multi_year.py`:
   - `test_badehog_family_indicators_report_chile_2021_anchors_in_stage5`
   - `test_fetcher_dynamically_rescues_empirical_anchors_even_when_unindexed_in_stage5`

## Base Commit
`6927d25`

## Constraints
- Python 3.10+ modern typing syntax.
- All non-integration tests (292+) must pass without regression.
- False Substitution Rate must strictly equal 0.00% across the 200-question benchmark.
- Top-1 Accuracy across the 200 benchmark test cases must strictly remain 100.0%.
- Local resolution latency over SQLite and in-memory thesaurus must maintain p50 < 0.5 ms.
- Safe UTF-8 encoding for Windows console environments.
- Strict offline hermeticity: test suites must NEVER perform live network calls to CEPALSTAT.
