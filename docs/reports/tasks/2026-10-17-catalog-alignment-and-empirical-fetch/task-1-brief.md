# Task 1 Brief: Empirical Indicator ID Mapping & Synthetic member_id Isolation

## Mission
1. In `src/statscepal/semantic/registry.py`:
   - Define `SYNTHETIC_DIMENSION_MEMBER_IDS: frozenset[int]` listing all synthetic member IDs from `DEFAULT_OFFICIAL_DIMENSIONS` that must not be sent as raw integer filters to the live CEPALSTAT API (`{300, 301, 302, 327, 330, 331, 412, 413, 414, 415, 501, 502, 601, 602, 603, 604, 605, 610, 611, 612, 613, 701, 79578, 79580}`).
   - Define `EMPIRICAL_INDICATOR_ID_MAP: dict[int, int]` mapping synthetic/placeholder `official_25` indicator IDs to verified real CEPALSTAT `master_indicators` IDs (`2928 -> 2484`, `2930 -> 4145`, `729 -> 2204`, `730 -> 2206`, `731 -> 286`, `2447 -> 286`, `3331 -> 5097`, `3344 -> 5097`, `128 -> 341`, `3337 -> 340`, `3339 -> 2287`, `3345 -> 5698`, `3340 -> 3390`, `1241 -> 1246`, `1242 -> 821`, `1243 -> 740`, `1244 -> 883`, `5683 -> 3154`, `4406 -> 460`, `1318 -> 3097`, `3333 -> 2288`, `2949 -> 2050`, `2954 -> 883`).
2. In `src/statscepal/semantic/fetcher.py`:
   - Add method `_resolve_empirical_indicator_id(self, response: SemanticResolutionResponse) -> int` handling special dynamic mappings (e.g. for `3340`: `3295` if `estrato == "RELACION_Q5_Q1"`, `3324` if `"QUINTIL"` in `estrato`, else `3390`; and general lookup in `EMPIRICAL_INDICATOR_ID_MAP`).
   - In `fetch_resolved_data`:
     - Resolve `empirical_id = self._resolve_empirical_indicator_id(response)`.
     - Filter out `SYNTHETIC_DIMENSION_MEMBER_IDS` from `member_ids` before calling `self._load_indicator_data(empirical_id, member_ids)`.
     - Record `"empirical_indicator_id": empirical_id` in `payload`.
3. In `tests/test_semantic_fetcher.py`:
   - Add unit tests:
     - `test_fetcher_strips_synthetic_member_ids_to_prevent_api_country_collision`
     - `test_fetcher_maps_synthetic_indicator_2928_to_real_cepalstat_2484`

## Base Commit
`4ac75d712711be26317233f605917fb8a08d3bdb`

## Constraints
- Python 3.10+ modern typing syntax.
- All non-integration tests (295+) must pass without regression.
- False Substitution Rate must strictly equal 0.00% across the 200-question benchmark.
- Top-1 Accuracy across the 200 benchmark test cases must strictly remain 100.0%.
- Local resolution latency over SQLite and in-memory thesaurus must maintain p50 < 0.5 ms.
- Safe UTF-8 encoding for Windows console environments.
- Strict offline hermeticity: test suites must NEVER perform live network calls to CEPALSTAT.
