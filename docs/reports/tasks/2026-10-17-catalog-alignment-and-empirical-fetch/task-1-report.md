# Task 1 Report: Empirical Indicator ID Mapping & Synthetic member_id Isolation

**Status:** DONE
**Author:** Amelia, Senior Developer
**Commit:** `591da03` (`feat(semantic): map synthetic indicator IDs to real CEPALSTAT IDs and strip synthetic member IDs`)
**Date:** 2026-10-17

---

## 1. Summary of Changes

### `src/statscepal/semantic/registry.py`
- **Defined `SYNTHETIC_DIMENSION_MEMBER_IDS: frozenset[int]`:**
  Lists all synthetic mock member IDs from `DEFAULT_OFFICIAL_DIMENSIONS` (`{300, 301, 302, 327, 330, 331, 412, 413, 414, 415, 501, 502, 601, 602, 603, 604, 605, 610, 611, 612, 613, 701, 79578, 79580}`) that must never be sent as raw integer filters (`members=`) to the CEPALSTAT API to prevent unexpected member filtering or country collisions (e.g., member `79578` colliding with Chile).
- **Defined `EMPIRICAL_INDICATOR_ID_MAP: dict[int, int]`:**
  Maps synthetic/placeholder `official_25` indicator IDs to verified real CEPALSTAT `master_indicators` IDs (`2928 -> 2484`, `2930 -> 4145`, `729 -> 2204`, `730 -> 2206`, `731 -> 286`, `2447 -> 286`, `3331 -> 5097`, `3344 -> 5097`, `128 -> 341`, `3337 -> 340`, `3339 -> 2287`, `3345 -> 5698`, `3340 -> 3390`, `1241 -> 1246`, `1242 -> 821`, `1243 -> 740`, `1244 -> 883`, `5683 -> 3154`, `4406 -> 460`, `1318 -> 3097`, `3333 -> 2288`, `2949 -> 2050`, `2954 -> 883`).

### `src/statscepal/semantic/fetcher.py`
- **Implemented `_resolve_empirical_indicator_id(self, response: SemanticResolutionResponse) -> int`:**
  Resolves dynamic mappings for indicator `3340` based on `estrato` (`RELACION_Q5_Q1` -> `3295`, `"QUINTIL"` in `estrato` -> `3324`, default -> `3390`), and general mapping lookup in `EMPIRICAL_INDICATOR_ID_MAP`.
- **Integrated in `fetch_resolved_data`:**
  - Resolved `empirical_id = self._resolve_empirical_indicator_id(response)`.
  - Filtered `SYNTHETIC_DIMENSION_MEMBER_IDS` out of `member_ids` before calling `_load_indicator_data(empirical_id, member_ids)`.
  - Recorded `"empirical_indicator_id": empirical_id` in `payload` and preserved on `response.empirical_data`.
  - Adjusted country column search order so human-readable country columns (`Países_agregados...`) are prioritized ahead of `iso3`.

### `tests/test_semantic_fetcher.py`
- Added unit tests:
  - `test_fetcher_strips_synthetic_member_ids_to_prevent_api_country_collision`
  - `test_fetcher_maps_synthetic_indicator_2928_to_real_cepalstat_2484`

---

## 2. Test-Driven Development (TDD) Trace

1. **Red Test:**
   Ran `uv run pytest tests/test_semantic_fetcher.py -k "test_fetcher_strips_synthetic_member_ids or test_fetcher_maps_synthetic_indicator_2928" -v`
   - `test_fetcher_strips_synthetic_member_ids_to_prevent_api_country_collision`: FAILED (`Expected: get_dataframe(2929, members=None), Actual: get_dataframe(2929, members=[79578])`).
   - `test_fetcher_maps_synthetic_indicator_2928_to_real_cepalstat_2484`: FAILED (`Expected: get_dataframe(2484, members=None), Actual: get_dataframe(2928, members=None)`).

2. **Green Test:**
   After implementing `SYNTHETIC_DIMENSION_MEMBER_IDS`, `EMPIRICAL_INDICATOR_ID_MAP`, `_resolve_empirical_indicator_id`, and payload mapping:
   - `uv run pytest tests/test_semantic_fetcher.py -v`: 12 passed in 3.10s.
   - `uv run pytest tests/test_semantic_benchmark_200.py -v`: 11 passed (100% pass across all 10 clusters and 200 questions).
   - `uv run pytest -m "not integration"`: 297 passed, 3 deselected in 49.62s.

---

## 3. Benchmark & Constraints Verification

- **Top-1 Accuracy:** 100.0% preserved across 200 benchmark test cases.
- **False Substitution Rate:** 0.00% strictly maintained.
- **Test suite:** 297/297 non-integration tests passing with 0 regressions.
- **Hermeticity:** All unit tests run fully offline with mocks, without live API calls.
- **Git status:** Clean workspace, only expected commit created.
