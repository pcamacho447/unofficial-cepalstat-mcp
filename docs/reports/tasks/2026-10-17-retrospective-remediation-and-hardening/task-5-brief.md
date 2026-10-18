# Task 5 Brief: CLI `conversational_hint` Rendering for `ALTERNATIVE_PROPOSED`, Multi-Year Dynamic Anchor Rescue, and Multi-Country Country Attribution (`AI-6`)

**Implementer:** Amelia, Senior Developer  
**Plan:** [`docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md)  
**Base Commit:** `4724f32`  

---

## 1. What to Build

### A. CLI `conversational_hint` Display (`src/statscepal/cli.py`)
In `cli.py:639-650`:
Currently, `res.conversational_hint` is only printed in the `else:` branch when `res.selected_candidate is None`.
However, when `res.status == SemanticResolutionStatus.ALTERNATIVE_PROPOSED`, `res.selected_candidate` is populated (with the primary candidate), so the dynamic hint guiding the user with alternative indicators is never printed to the CLI!

**Fix:** Move the hint check outside the `if/else` block:
```python
if res.selected_candidate:
    sc = res.selected_candidate
    print(f"Indicator: {sc.indicator_id} - {sc.name} (Measure: {sc.measure_type}, Unit: {sc.unit})")
    print(f"Score:     {sc.relevance_score}")
else:
    if res.abstention_reason:
        print(f"Reason:    {res.abstention_reason}")

if res.conversational_hint:
    print(f"Hint:      {res.conversational_hint}")
```

Add test `test_cli_semantic_resolve_displays_conversational_hint_on_alternative_proposed` in `tests/test_cli_semantic.py` verifying that running `uv run statscepal semantic resolve "cuentas fiscales de chile 2022"` outputs `"Hint:"` and alternative IDs.

### B. Multi-Year Dynamic Anchor Rescue across Partial Gaps (`src/statscepal/semantic/fetcher.py`)
In `fetcher.py:687-705`:
Currently, the fetcher checks:
`if not observed_requested and avail_years:`
If a user requests `[2020, 2021, 2022]`, and 2020 and 2022 are present, but 2021 is missing, `not observed_requested` evaluates to `False`, so dynamic anchor discovery is skipped entirely for 2021!

**Fix:** Inspect missing requested years:
```python
missing_requested = requested_year_set - avail_years
if missing_requested and avail_years:
    for req_y in sorted(missing_requested):
        prev_anchor = max((y for y in avail_years if y < req_y), default=None)
        next_anchor = min((y for y in avail_years if y > req_y), default=None)
        if prev_anchor is not None or next_anchor is not None:
            if c_code not in country_anchor_map:
                country_anchor_map[c_code] = {}
            if prev_anchor is not None:
                country_anchor_map[c_code].setdefault(prev_anchor, [])
                if req_y not in country_anchor_map[c_code][prev_anchor]:
                    country_anchor_map[c_code][prev_anchor].append(req_y)
            if next_anchor is not None:
                country_anchor_map[c_code].setdefault(next_anchor, [])
                if req_y not in country_anchor_map[c_code][next_anchor]:
                    country_anchor_map[c_code][next_anchor].append(req_y)
            has_rescued_anchors = True
```
And if `has_rescued_anchors` and `response.status == SemanticResolutionStatus.RESOLVED`, update `response.status = SemanticResolutionStatus.RESOLVED_WITH_ANCHORS`.

Add test `test_fetcher_multi_year_rescues_anchors_for_missing_year_in_range` in `tests/test_semantic_fetcher.py`.

### C. Multi-Country Top-Level Country Attribution (`src/statscepal/semantic/fetcher.py`)
In `fetcher.py:914-929`:
When building `payload` from `series[-1]`:
Currently:
`"country": response.applied_filters.country_name or response.applied_filters.country_code`
In multi-country queries, `series[-1]` is the last country's observation, but `applied_filters.country_name` is the first country's name!

**Fix:**
```python
latest_item = series[-1]
payload = {
    ...
    "country": latest_item.get("country", response.applied_filters.country_name or response.applied_filters.country_code),
    ...
}
```

Add test `test_fetcher_multi_country_payload_country_attribution` in `tests/test_semantic_fetcher.py`.

---

## 2. Test-Driven Development (TDD) Workflow

1. Add the failing tests to `tests/test_cli_semantic.py` and `tests/test_semantic_fetcher.py`.
2. Run red tests:
   `uv run pytest tests/test_cli_semantic.py -k test_cli_semantic_resolve_displays_conversational_hint_on_alternative_proposed`
   `uv run pytest tests/test_semantic_fetcher.py -k "test_fetcher_multi_year_rescues_anchors or test_fetcher_multi_country_payload_country_attribution"`
3. Implement the fixes in `src/statscepal/cli.py` and `src/statscepal/semantic/fetcher.py`.
4. Run green tests:
   `uv run pytest tests/test_cli_semantic.py tests/test_semantic_fetcher.py -v`
   `uv run pytest tests/test_semantic_benchmark_200.py -v`
   `uv run pytest -m "not integration"`
5. Commit:
   `git add src/statscepal/cli.py src/statscepal/semantic/fetcher.py tests/test_cli_semantic.py tests/test_semantic_fetcher.py`
   `git commit -m "fix(cli,fetcher): display conversational hints on alternatives, rescue partial multi-year anchors, and fix payload country attribution"`
6. Write your task report to `C:\papx\statscepal\.superpowers\sdd\2026-10-17-retrospective-remediation-and-hardening-plan\task-5-report.md`.
