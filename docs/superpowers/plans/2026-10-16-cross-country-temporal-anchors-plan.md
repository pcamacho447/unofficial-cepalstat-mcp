# Cross-Country Temporal Anchor Audit & Automatic Anchor Observation Rescue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance Stage 5 (Temporal Audit), `SemanticDataFetcher`, and the CLI so that when a single-country or multi-country query encounters a household survey periodicity gap (e.g., Chile in 2021 for poverty while Peru and Colombia have 2021 data), the engine explicitly reports the adjacent official anchor years (`Prev=2020, Next=2022`) per country and `--fetch` automatically rescues those official anchor observations without leaving the country blank or interpolating.

**Architecture:**
- **Structured Per-Country Anchor Metadata (`models.py` & `engine.py`):** Introduce `CountryTemporalAnchor` inside `TemporalAnchorInfo.country_anchors` (`dict[str, CountryTemporalAnchor]`) mapping each country code with survey gaps to its `unobserved_years`, `previous_anchor_year`, and `next_anchor_year`. Update Stage 5 in `SemanticResolutionEngine.resolve` to populate `country_anchors` and generate explicit per-country anchor notices in both `execution_trace` and `disclaimer`.
- **Automatic Anchor Observation Rescue (`fetcher.py`):** Update `SemanticDataFetcher.fetch_resolved_data` so that when `response.status == ResolutionStatus.RESOLVED_WITH_ANCHORS`, any country with unobserved requested years automatically includes its official `previous_anchor_year` and `next_anchor_year` rows from the indicator DataFrame, tagging those series items with `"is_anchor": True`, `"anchor_for_years": [...]`, and an explicit note `"[Ancla oficial para 2021]"`.
- **CLI Transparency (`cli.py`):** Update `statscepal semantic resolve` to display per-country anchor years in the `Temporal:` header line and highlight rescued anchor rows in the `--fetch` empirical table.

**Tech Stack:**
- Python 3.10+ (modern union types `X | Y`, built-in collections `dict`, `list`, `set`)
- Pydantic v2 (`BaseModel`, `Field`)
- pandas (`DataFrame` vector filtering)
- pytest (`capsys`, `unittest.mock.patch`)

**Spec:** User feedback on multi-country survey gap handling (`"tasa de pobreza en peru colombia y chile en el 2021"`).

## Global Constraints

- Modern Python 3.10+ typing syntax (`X | Y`, built-in generic collections).
- Strictly 0.00% False Substitution Rate across the 200-question and 70-case facet benchmarks.
- Maintain 100.0% Top-1 Accuracy across all benchmark test suites.
- Strictly forbid linear interpolation (`forbid_interpolation=True` invariant).
- Zero hardcoded facet or indicator literals in Stage 4 of `engine.py`.
- Strict offline hermeticity in unit tests (no live network calls to CEPALSTAT).
- Safe UTF-8 encoding for Windows console environments.

---

## File Structure

- **Modify:** `src/statscepal/semantic/models.py`
  - Add `CountryTemporalAnchor` model and `country_anchors: dict[str, CountryTemporalAnchor]` field on `TemporalAnchorInfo`.
  - Export `CountryTemporalAnchor` in `src/statscepal/semantic/__init__.py`.
- **Modify:** `src/statscepal/semantic/engine.py`
  - Populate `country_anchors` in Stage 5 for both multi-country and single-country audits, and include explicit per-country anchor years (`Prev=..., Next=...`) in Stage 5 trace logs and `TemporalAnchorInfo.disclaimer`.
- **Modify:** `src/statscepal/semantic/fetcher.py`
  - Rescue official anchor observations per country when `ResolutionStatus.RESOLVED_WITH_ANCHORS` is active, tagging rescued items with `"is_anchor": True` and `"anchor_for_years"`.
- **Modify:** `src/statscepal/cli.py`
  - Format `Temporal:` summary with per-country anchor pairs and annotate anchor rows in `--fetch` output.
- **Test:** `tests/test_semantic_multi_year.py`
  - Add unit and CLI tests covering per-country anchor metadata, disclaimer formatting, and automatic anchor observation rescue in `SemanticDataFetcher` and CLI `--fetch`.

---

### Task 1: Per-Country Temporal Anchor Model & Stage 5 Cross-Country Audit

**Files:**
- Modify: `src/statscepal/semantic/models.py:70-100`
- Modify: `src/statscepal/semantic/__init__.py`
- Modify: `src/statscepal/semantic/engine.py:410-510`
- Test: `tests/test_semantic_multi_year.py`

**Interfaces:**
- Produces:
  ```python
  class CountryTemporalAnchor(BaseModel):
      country_code: str
      country_name: str | None = None
      unobserved_years: list[int] = Field(default_factory=list)
      previous_anchor_year: int | None = None
      next_anchor_year: int | None = None
  ```
  and on `TemporalAnchorInfo`:
  ```python
  country_anchors: dict[str, CountryTemporalAnchor] = Field(default_factory=dict)
  ```

- [ ] **Step 1: Write the failing test in `tests/test_semantic_multi_year.py`**

```python
def test_stage5_populates_per_country_anchors_and_explicit_disclaimer():
    from statscepal.semantic.engine import SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    res = engine.resolve("tasa de pobreza en peru colombia y chile en el 2021")

    assert res.status == ResolutionStatus.RESOLVED_WITH_ANCHORS
    assert res.temporal_info is not None
    assert "CHL" in res.temporal_info.country_anchors
    chl_anchor = res.temporal_info.country_anchors["CHL"]
    assert chl_anchor.country_code == "CHL"
    assert chl_anchor.country_name == "Chile"
    assert chl_anchor.unobserved_years == [2021]
    assert chl_anchor.previous_anchor_year == 2020
    assert chl_anchor.next_anchor_year == 2022

    # Disclaimer and trace must explicitly mention Chile's anchor years 2020 and 2022
    assert "2020" in res.temporal_info.disclaimer
    assert "2022" in res.temporal_info.disclaimer
    trace_str = "\n".join(res.execution_trace)
    assert "Prev=2020, Next=2022" in trace_str
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_multi_year.py -k test_stage5_populates_per_country_anchors_and_explicit_disclaimer -v`
Expected: FAIL with `AttributeError: 'TemporalAnchorInfo' object has no attribute 'country_anchors'`

- [ ] **Step 3: Implement `CountryTemporalAnchor` in `models.py` and Stage 5 per-country anchor tracking in `engine.py`**

In `src/statscepal/semantic/models.py`:
```python
class CountryTemporalAnchor(BaseModel):
    """Official adjacent survey anchor years for a specific country with unobserved periods."""

    country_code: str
    country_name: str | None = None
    unobserved_years: list[int] = Field(default_factory=list)
    previous_anchor_year: int | None = None
    next_anchor_year: int | None = None


class TemporalAnchorInfo(BaseModel):
    """Information about temporal availability and adjacent anchor points."""

    requested_year: int
    requested_years: list[int] = Field(default_factory=list)
    observed_years: list[int] = Field(default_factory=list)
    unobserved_years: list[int] = Field(default_factory=list)
    requested_countries: list[str] = Field(default_factory=list)
    observed_countries: list[str] = Field(default_factory=list)
    unobserved_countries: list[str] = Field(default_factory=list)
    country_anchors: dict[str, CountryTemporalAnchor] = Field(default_factory=dict)
    temporal_status: TemporalAvailabilityStatus
    previous_anchor_year: int | None = None
    next_anchor_year: int | None = None
    forbid_interpolation: bool = True
    disclaimer: str = ""
```

In `src/statscepal/semantic/engine.py` (Stage 5):
Track `c_unobs_years`, `c_prev`, `c_next` for each country `c_code` (and `c_name`), build `country_anchors[c_code] = CountryTemporalAnchor(...)`, and format `anchor_details_str`:
```python
anchor_details = []
for c_code, ca in country_anchors.items():
    c_label = f"{ca.country_name} ({c_code})" if ca.country_name else c_code
    anchor_details.append(
        f"{c_label} sin medición en {ca.unobserved_years} (Puntos ancla oficiales: Prev={ca.previous_anchor_year}, Next={ca.next_anchor_year})"
    )
```
Include `anchor_details` in `trace` and `TemporalAnchorInfo.disclaimer`. Also populate `country_anchors` on the single-country `PERIOD_UNOBSERVED` branches.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_multi_year.py -k test_stage5_populates_per_country_anchors_and_explicit_disclaimer -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/semantic/models.py src/statscepal/semantic/__init__.py src/statscepal/semantic/engine.py tests/test_semantic_multi_year.py
git commit -m "feat(semantic): track per-country temporal anchors in Stage 5 audit and disclaimer"
```

---

### Task 2: Automatic Anchor Observation Rescue in `SemanticDataFetcher`

**Files:**
- Modify: `src/statscepal/semantic/fetcher.py:225-380`
- Test: `tests/test_semantic_multi_year.py`

**Interfaces:**
- Consumes: `response.temporal_info.country_anchors`, `response.temporal_info.previous_anchor_year`, `response.temporal_info.next_anchor_year`
- Produces: Series items in `payload["series"]` where rescued anchor rows include:
  - `"is_anchor": True`
  - `"anchor_for_years": list[int]`
  - `"notes"`: includes `"[Ancla oficial para 2021]"`

- [ ] **Step 1: Write the failing test in `tests/test_semantic_multi_year.py`**

```python
def test_fetcher_rescues_anchor_years_for_unobserved_country_in_multi_country_query():
    from statscepal.semantic.engine import SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    res = engine.resolve("tasa de pobreza en peru colombia y chile en el 2021")

    mock_df = pd.DataFrame([
        {"iso3": "PER", "year": 2021, "value": 25.9, "dim_500": "502", "dim_326": "327", "notes": ""},
        {"iso3": "COL", "year": 2021, "value": 39.3, "dim_500": "502", "dim_326": "327", "notes": ""},
        # Chile has no 2021 row, only 2020 and 2022 CASEN anchor rows
        {"iso3": "CHL", "year": 2020, "value": 10.8, "dim_500": "502", "dim_326": "327", "notes": "CASEN 2020"},
        {"iso3": "CHL", "year": 2022, "value": 6.5, "dim_500": "502", "dim_326": "327", "notes": "CASEN 2022"},
        {"iso3": "CHL", "year": 2017, "value": 8.6, "dim_500": "502", "dim_326": "327", "notes": "CASEN 2017"},
    ])

    fetcher = SemanticDataFetcher()
    with patch.object(fetcher, "_load_indicator_data", return_value=mock_df):
        payload = fetcher.fetch_resolved_data(res)

    assert payload["observation_exists"] is True
    series = payload["series"]
    # PER (2021), COL (2021), CHL (2020 anchor), CHL (2022 anchor)
    assert len(series) == 4
    chl_rows = [s for s in series if s.get("country") == "CHL"]
    assert [s["year"] for s in chl_rows] == [2020, 2022]
    assert all(s.get("is_anchor") is True for s in chl_rows)
    assert all(2021 in s.get("anchor_for_years", []) for s in chl_rows)
    assert all("Ancla oficial" in s.get("notes", "") for s in chl_rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_multi_year.py -k test_fetcher_rescues_anchor_years_for_unobserved_country_in_multi_country_query -v`
Expected: FAIL (`len(series) == 2`, because `CHL` rows in 2020 and 2022 are filtered out by `col_years == 2021`)

- [ ] **Step 3: Implement anchor year rescue in `src/statscepal/semantic/fetcher.py`**

In `src/statscepal/semantic/fetcher.py`:
1. Build a lookup `country_anchor_years: dict[str, dict[int, list[int]]]` from `response.temporal_info`:
   - For each `c_code, ca` in `response.temporal_info.country_anchors.items()`:
     map `ca.previous_anchor_year` and `ca.next_anchor_year` (when not `None`) to `ca.unobserved_years`.
   - Also build `global_anchor_years: dict[int, list[int]]` when `country_anchors` is empty but `response.temporal_info.previous_anchor_year` or `next_anchor_year` is set on a single-country `PERIOD_UNOBSERVED` response.
2. In Step 4 (`# 4. Filter by temporal constraints`):
   - Compute `requested_year_set = set(target_years) if target_years else ({target_year} if target_year is not None else set())`.
   - If `country_anchor_years` or `global_anchor_years` is non-empty:
     - Allow rows where `col_years.isin(requested_year_set)` OR where the row belongs to a country `c_code` (or `c_name`) and `row_year` is in that country's `anchor_years`.
     - Set `has_rescued_anchors = True` so Step 5 formats the output as `series` even for a single-country query that rescued two anchors (`2020` and `2022`).
3. In Step 5 (`# 5. Format observation result`):
   - When `row_year not in requested_year_set` (or when `row_country` had `row_year` rescued as an anchor for an unobserved year), set:
     ```python
     item_dict["is_anchor"] = True
     item_dict["anchor_for_years"] = anchor_for_years
     anchor_tag = f"[Ancla oficial para {', '.join(str(y) for y in anchor_for_years)}]"
     item_dict["notes"] = f"{row_notes} {anchor_tag}".strip()
     ```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_multi_year.py -k test_fetcher_rescues_anchor_years_for_unobserved_country_in_multi_country_query -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/semantic/fetcher.py tests/test_semantic_multi_year.py
git commit -m "feat(semantic): rescue official anchor observations in SemanticDataFetcher when survey gaps occur"
```

---

### Task 3: CLI Display of Per-Country Anchors & Rescued Anchor Rows

**Files:**
- Modify: `src/statscepal/cli.py:660-775`
- Test: `tests/test_semantic_multi_year.py`

**Interfaces:**
- Consumes: `res.temporal_info.country_anchors`, `item.get("is_anchor")`, `item.get("anchor_for_years")`
- Produces: CLI output showing per-country anchor pairs in `Temporal:` and annotating rescued anchor observations in `--fetch`.

- [ ] **Step 1: Write the failing test in `tests/test_semantic_multi_year.py`**

```python
def test_cli_displays_per_country_anchors_and_rescued_fetch_rows(capsys):
    from statscepal.cli import main

    ret = main([
        "semantic",
        "resolve",
        "tasa de pobreza en peru colombia y chile en el 2021",
        "--explain",
    ])
    assert ret == 0
    out = capsys.readouterr().out
    assert "CHL (Prev=2020, Next=2022)" in out
    assert "Puntos ancla oficiales: Prev=2020, Next=2022" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_multi_year.py -k test_cli_displays_per_country_anchors_and_rescued_fetch_rows -v`
Expected: FAIL (`"CHL (Prev=2020, Next=2022)"` not in `out`)

- [ ] **Step 3: Update `src/statscepal/cli.py` to format per-country anchors and rescued rows**

In `src/statscepal/cli.py`:
1. When `getattr(ti, "requested_countries", None) and len(ti.requested_countries) > 1`:
   If `getattr(ti, "country_anchors", None)`:
   ```python
   unobs_fmt = [
       f"{c} (Prev={ti.country_anchors[c].previous_anchor_year}, Next={ti.country_anchors[c].next_anchor_year})"
       if c in ti.country_anchors
       else c
       for c in ti.unobserved_countries
   ]
   print(
       f"Temporal:  {ti.temporal_status.value} (Observed Countries: {ti.observed_countries}, Unobserved: [{', '.join(unobs_fmt)}])"
   )
   ```
2. In `--fetch` `Empirical Series` printing:
   When `item.get("is_anchor")` is True, append ` (Ancla)` to the displayed year or unit/notes so the user clearly distinguishes exact-year observations from rescued anchor observations.

- [ ] **Step 4: Run test and full test suite to verify everything passes**

Run: `uv run pytest tests/test_semantic_multi_year.py tests/test_cli_semantic.py tests/test_semantic_facet_coverage.py tests/test_semantic_benchmark_200.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/cli.py tests/test_semantic_multi_year.py
git commit -m "feat(cli): display per-country anchor years and annotate rescued anchor rows in semantic resolve"
```
