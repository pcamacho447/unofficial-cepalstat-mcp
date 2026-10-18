# Task 5 Report: CLI `conversational_hint` Rendering for `ALTERNATIVE_PROPOSED`, Multi-Year Dynamic Anchor Rescue, and Multi-Country Country Attribution (`AI-6`)

**Author:** Amelia, Senior Developer  
**Date:** 2026-10-17  
**Commit:** `065f29a` (`fix(cli,fetcher): display conversational hints on alternatives, rescue partial multi-year anchors, and fix payload country attribution`)  
**Base Commit:** `4724f32`  
**Working Directory:** `C:\papx\statscepal`  

---

## 1. Executive Summary

Task 5 addressed three targeted consistency and observability gaps across the CEPALSTAT Semantic CLI and Data Fetcher (`AI-6`):
1. **CLI `conversational_hint` Rendering on Alternatives:** Resolved an issue where conversational hints detailing alternative indicator IDs (e.g., ID 1241 and ID 1242 for public finances) were suppressed when `res.selected_candidate` was populated (`ALTERNATIVE_PROPOSED`). Hints are now universally displayed whenever present.
2. **Multi-Year Dynamic Anchor Rescue across Partial Gaps:** In multi-year queries where a requested time span has missing years (e.g., 2021 unobserved in a 2020–2022 range query), the fetcher previously skipped anchor discovery if *any* requested year was observed (`if not observed_requested and avail_years:`). The fetcher now calculates `missing_requested = requested_year_set - avail_years` to dynamically rescue adjacent official anchor periods (e.g. CASEN pandemic/post-pandemic surveys) and promote the response status to `RESOLVED_WITH_ANCHORS`.
3. **Multi-Country Top-Level Country Attribution:** In multi-country queries where `series[-1]` corresponds to the last country processed, the root `payload["country"]` previously defaulted to `applied_filters.country_name` (the first country), causing misattribution. The root payload now extracts `latest_item.get("country", ...)` to ensure exact 1-to-1 alignment between the root observation metrics and the series tail.

All 316 non-integration tests pass, the 200-question benchmark maintains 100.0% Top-1 accuracy and 0.00% False Substitution Rate, and strict offline hermeticity is preserved.

---

## 2. Test-Driven Development (TDD) Workflow

### A. Red Phase (Failing Tests Added)
1. **CLI Hint Display:** Added `test_cli_semantic_resolve_displays_conversational_hint_on_alternative_proposed` in `tests/test_cli_semantic.py`.
   - Command: `uv run pytest tests/test_cli_semantic.py -k test_cli_semantic_resolve_displays_conversational_hint_on_alternative_proposed`
   - Result: Failed with `AssertionError: assert 'Hint:' in ...`
2. **Multi-Year Partial Anchor Rescue:** Added `test_fetcher_multi_year_rescues_anchors_for_missing_year_in_range` in `tests/test_semantic_fetcher.py`.
   - Command: `uv run pytest tests/test_semantic_fetcher.py -k test_fetcher_multi_year_rescues_anchors_for_missing_year_in_range`
   - Result: Failed with `AssertionError: assert (False or <ResolutionStatus.RESOLVED: 'RESOLVED'> == <ResolutionStatus.RESOLVED_WITH_ANCHORS: 'RESOLVED_WITH_ANCHORS'>)`
3. **Multi-Country Country Attribution:** Added `test_fetcher_multi_country_payload_country_attribution` in `tests/test_semantic_fetcher.py`.
   - Command: `uv run pytest tests/test_semantic_fetcher.py -k test_fetcher_multi_country_payload_country_attribution`
   - Result: Failed with `AssertionError: assert 'Perú' == 'Colombia'`

### B. Implementation Phase
1. `src/statscepal/cli.py`:
   - Moved `if res.conversational_hint: print(f"Hint:      {res.conversational_hint}")` outside the `else:` branch after `if res.selected_candidate:`.
2. `src/statscepal/semantic/fetcher.py`:
   - Replaced `observed_requested = avail_years.intersection(requested_year_set)` gate with `missing_requested = requested_year_set - avail_years`.
   - Set `has_rescued_anchors = True` when anchors are discovered for missing years.
   - Updated `response.status = ResolutionStatus.RESOLVED_WITH_ANCHORS` if `has_rescued_anchors and response.status == ResolutionStatus.RESOLVED`.
   - Assigned `payload["country"] = latest_item.get("country", response.applied_filters.country_name or response.applied_filters.country_code)`.

### C. Green Phase (Verification)
- `tests/test_cli_semantic.py tests/test_semantic_fetcher.py`: 35/35 passed (9.17s)
- `tests/test_semantic_benchmark_200.py`: 11/11 clusters passed (1.59s), 100.0% Top-1 accuracy, 0.00% False Substitution Rate
- `pytest -m "not integration"`: 316/316 passed, 3 deselected (44.12s)

---

## 3. Changeset Inspection

```diff
diff --git a/src/statscepal/cli.py b/src/statscepal/cli.py
index e204c87..3c30ead 100644
--- a/src/statscepal/cli.py
+++ b/src/statscepal/cli.py
@@ -645,8 +645,9 @@ def main(args: Sequence[str] | None = None) -> int:
                 else:
                     if res.abstention_reason:
                         print(f"Reason:    {res.abstention_reason}")
-                    if res.conversational_hint:
-                        print(f"Hint:      {res.conversational_hint}")
+
+                if res.conversational_hint:
+                    print(f"Hint:      {res.conversational_hint}")
 
                 if res.polarity_info:
                     print(
diff --git a/src/statscepal/semantic/fetcher.py b/src/statscepal/semantic/fetcher.py
index c09bdfd..acfbe2d 100644
--- a/src/statscepal/semantic/fetcher.py
+++ b/src/statscepal/semantic/fetcher.py
@@ -684,10 +684,10 @@ class SemanticDataFetcher:
                     .astype(int)
                 )
                 avail_years = set(num_years.unique())
-                observed_requested = avail_years.intersection(requested_year_set)
+                missing_requested = requested_year_set - avail_years
 
-                if not observed_requested and avail_years:
-                    for req_y in sorted(requested_year_set):
+                if missing_requested and avail_years:
+                    for req_y in sorted(missing_requested):
                         prev_anchor = max((y for y in avail_years if y < req_y), default=None)
                         next_anchor = min((y for y in avail_years if y > req_y), default=None)
                         if prev_anchor is not None or next_anchor is not None:
@@ -707,6 +707,7 @@ class SemanticDataFetcher:
                                     c_str = str(c_val).strip()
                                     code_by_name[_strip_accents(c_str).lower()] = c_code
                                     code_by_name[c_str.lower()] = c_code
+                            has_rescued_anchors = True
 
         # 4. Filter by temporal constraints
         if not filtered_df.empty and year_col is not None:
@@ -792,6 +793,9 @@ class SemanticDataFetcher:
                             all_years = _extract_numeric_years(filtered_df[year_col])
                             filtered_df = filtered_df[all_years == max_y]
 
+        if has_rescued_anchors and response.status == ResolutionStatus.RESOLVED:
+            response.status = ResolutionStatus.RESOLVED_WITH_ANCHORS
+
         # 5. Format observation result
         if not filtered_df.empty:
             if is_multi_year or has_breakdown or is_multi_country or has_rescued_anchors:
@@ -918,8 +922,11 @@ class SemanticDataFetcher:
                         "indicator_name": response.selected_candidate.name,
                         "value": latest_item["value"],
                         "unit": response.selected_candidate.unit,
-                        "country": response.applied_filters.country_name
-                        or response.applied_filters.country_code,
+                        "country": latest_item.get(
+                            "country",
+                            response.applied_filters.country_name
+                            or response.applied_filters.country_code,
+                        ),
                         "year": latest_item["year"],
                         "dimensions_applied": [
                             f.model_dump() for f in response.applied_filters.dimensions
```

---

## 4. Verification & Quality Gates

| Gate | Target | Result | Status |
|---|---|---|---|
| Red Test (CLI hint) | `assert 'Hint:' in captured` fails | Failed with `AssertionError` | PASSED |
| Red Test (Multi-year anchor) | `assert res.status == RESOLVED_WITH_ANCHORS` fails | Failed with `AssertionError` | PASSED |
| Red Test (Country attribution) | `assert payload['country'] == 'Colombia'` fails | Failed with `'Perú' == 'Colombia'` | PASSED |
| Green Test (CLI + Fetcher) | 35 unit tests pass | 35 passed | PASSED |
| 200-Question Benchmark | 100% Top-1 Accuracy, 0.00% False Substitution | 11/11 clusters passed | PASSED |
| Full Non-Integration Suite | All tests pass | 316 passed, 3 deselected | PASSED |
| Offline Hermeticity | Zero network calls | Fully mock/fixture verified | PASSED |
| Hygiene & Cleanliness | Clean working directory, no stray files | Verified with `git status` | PASSED |

---

## 5. Conclusion

Task 5 is 100% complete. All requirements from the brief and remediation plan have been implemented under TDD, verified against regressions across the entire test suite and benchmark, and committed with clean traceability.
