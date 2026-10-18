# Task 4 Report: Dimension & Member Alias Resolution on Empirical Remapping `3340 -> 3295 / 3324 / 3390` (`AI-5`)

**Implementer:** Amelia, Senior Developer  
**Plan:** `docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md`  
**Base Commit:** `403bc8b`  
**Task 4 Commit:** `4724f32` (`feat(semantic): support dimension and member aliases for empirical income distribution indicators (3324, 3390)`)  
**Diff File:** `review-403bc8b..4724f32.diff`  
**Date:** 2026-10-17  

---

## 1. Executive Summary

Task 4 resolves retrospective remediation item `AI-5` to enable seamless data extraction when generic income distribution queries mapped to conceptual indicator `3340` (*Distribución del ingreso por estratos*) dynamically remap to physical CEPALSTAT tables:
- **`3324`**: *Distribución del ingreso por quintiles*
- **`3390`**: *Distribución del ingreso por deciles*
- **`3295`**: *Relación de ingresos entre el quintil 5 y el quintil 1*

### Core Architectural Challenge
In CEPALSTAT's knowledge graph, `3340` provides a normalized conceptual umbrella with dimension `Estrato de ingreso` and descriptive members (`"Primer quintil"`, `"Quinto quintil"`, `"Primer decil"`, `"Décimo decil"`). However, the physical DataFrames retrieved from CEPALSTAT tables `3324` and `3390`:
1. Use column names `"Quintil"` / `"Quintiles"` or `"Decil"` / `"Deciles"` (never `"Estrato de ingreso"`).
2. Use row labels such as `"Quintil 1"`, `"Quintil 5"`, `"Decil 1"`, `"Decil 10"` (or Roman numerals `"I"`, `"V"`, `"X"`, or abbreviations `"Q1"`, `"D1"`).
3. Indicator `3295` is an empirical ratio table that does not contain an estrato breakdown dimension.

Without dimension and member alias resolution, Step 2 in `fetcher.py` failed to match the physical dimension column or row values, filtering out all rows and returning an empty observation payload.

### Key Solutions Implemented
1. **`DIM_NAME_ALIASES` & Symmetric Column Matching:**
   Defined dimension name aliases mapping `"estrato de ingreso"` to `["quintil", "decil", "estrato", "quintiles", "deciles", "estratos", "estrato de ingresos"]`. Updated `_match_dim_column` to perform symmetric accent-insensitive and `__estandar`-free alias matching.
2. **`MEMBER_VALUE_ALIASES` & Bi-directional Canonical Closure:**
   Defined comprehensive alias mappings for all quintiles (1-5) and all deciles (1-10) covering descriptive names, numeric labels (`"quintil 1"`), Roman numerals (`"i"`, `"v"`), abbreviations (`"q1"`, `"d1"`), and ordinal forms. Implemented `_get_acceptable_member_forms` to compute bi-directional canonical alias closures.
3. **Step 2 Member Value Filtering:**
   Integrated `_get_acceptable_member_forms` into Step 2 filtering, matching DataFrame values via normalized member comparison against the acceptable forms set.
4. **Consistent Series Representation & Indicator ID Alignment:**
   Updated single-observation payloads to consistently include `"series": [single_item]` with resolved `"member"` labels, and aligned `"indicator_id": empirical_id` while retaining candidate ID provenance in `res.selected_candidate.indicator_id`.
5. **Mock Extractor Robustness:**
   Updated `_load_indicator_data` to validate `isinstance(res, pd.DataFrame)` across `get_dataframe` and `fetch_indicator_dataframe`, eliminating test mock method collisions.

---

## 2. Changes Implemented

### A. Alias Dictionaries & Helpers in `src/statscepal/semantic/fetcher.py`
Defined top-level dictionaries and normalization helpers:
```python
DIM_NAME_ALIASES: dict[str, list[str]] = {
    "estrato de ingreso": [
        "quintil",
        "decil",
        "estrato",
        "quintiles",
        "deciles",
        "estratos",
        "estrato de ingresos",
    ],
}

MEMBER_VALUE_ALIASES: dict[str, list[str]] = {
    "primer quintil": ["quintil 1", "i", "quintil i", "1", "q1", "i quintil"],
    "segundo quintil": ["quintil 2", "ii", "quintil ii", "2", "q2", "ii quintil"],
    "tercer quintil": ["quintil 3", "iii", "quintil iii", "3", "q3", "iii quintil"],
    "cuarto quintil": ["quintil 4", "iv", "quintil iv", "4", "q4", "iv quintil"],
    "quinto quintil": ["quintil 5", "v", "quintil v", "5", "q5", "v quintil"],
    "primer decil": ["decil 1", "i", "decil i", "1", "d1", "i decil"],
    "segundo decil": ["decil 2", "ii", "decil ii", "2", "d2", "ii decil"],
    "tercer decil": ["decil 3", "iii", "decil iii", "3", "d3", "iii decil"],
    "cuarto decil": ["decil 4", "iv", "decil iv", "4", "d4", "iv decil"],
    "quinto decil": ["decil 5", "v", "decil v", "5", "d5", "v decil"],
    "sexto decil": ["decil 6", "vi", "decil vi", "6", "d6", "vi decil"],
    "septimo decil": ["decil 7", "vii", "decil vii", "7", "d7", "vii decil"],
    "octavo decil": ["decil 8", "viii", "decil viii", "8", "d8", "viii decil"],
    "noveno decil": ["decil 9", "ix", "decil ix", "9", "d9", "ix decil"],
    "decimo decil": ["decil 10", "x", "decil x", "10", "d10", "x decil"],
}

def _normalize_member_text(text: str) -> str:
    """Normalize member name or value for robust matching."""
    return _strip_accents(str(text)).lower().strip()

def _get_acceptable_member_forms(member_name: str) -> set[str]:
    """Return all normalized acceptable aliases and representations for a member name."""
    norm_m = _normalize_member_text(member_name)
    acceptable = {norm_m}
    if norm_m in MEMBER_VALUE_ALIASES:
        for alias in MEMBER_VALUE_ALIASES[norm_m]:
            acceptable.add(_normalize_member_text(alias))
    for canonical, aliases in MEMBER_VALUE_ALIASES.items():
        norm_aliases = {_normalize_member_text(a) for a in aliases}
        if norm_m in norm_aliases:
            acceptable.add(_normalize_member_text(canonical))
            acceptable |= norm_aliases
    return acceptable
```

### B. Symmetric Alias Matching in `_match_dim_column`
```python
def _match_dim_column(col_name: str, target_name: str) -> bool:
    """Check if a DataFrame column name matches a target dimension name, ignoring case, accents, and __estandar."""
    cl = _strip_accents(col_name).lower().strip().replace("__estandar", "")
    dl = _strip_accents(target_name).lower().strip().replace("__estandar", "")
    if cl == dl or cl.replace(" ", "") == dl.replace(" ", ""):
        return True
    aliases_dl = DIM_NAME_ALIASES.get(dl, [])
    if cl in aliases_dl or cl.replace(" ", "") in [a.replace(" ", "") for a in aliases_dl]:
        return True
    aliases_cl = DIM_NAME_ALIASES.get(cl, [])
    if dl in aliases_cl or dl.replace(" ", "") in [a.replace(" ", "") for a in aliases_cl]:
        return True
    return False
```

### C. Step 2 Member Filtering in `fetcher.py`
In `SemanticDataFetcher.fetch_resolved_data`:
```python
if dim_col is not None:
    filtered_dim_cols.add(dim_col)
    dim_mask = pd.Series(False, index=filtered_df.index)
    ...
    for m_name in candidate_names:
        dim_mask |= (
            filtered_df[dim_col].astype(str).str.strip().str.lower()
            == m_name.strip().lower()
        )
        dim_mask |= (
            filtered_df[dim_col].astype(str).str.strip().map(_strip_accents)
            == _strip_accents(m_name.strip())
        )
        acceptable_forms = _get_acceptable_member_forms(m_name)
        dim_mask |= (
            filtered_df[dim_col]
            .astype(str)
            .str.strip()
            .map(_normalize_member_text)
            .isin(acceptable_forms)
        )
    for m_id in candidate_ids:
        dim_mask |= (
            filtered_df[dim_col].astype(str).str.strip()
            == str(m_id)
        )
    filtered_df = filtered_df[dim_mask]
```

### D. Observation Payload & Series Construction
Single-observation queries now consistently format series items with dimension labels and set `indicator_id = empirical_id`:
```python
single_item: dict[str, Any] = {
    "year": row_year,
    "value": val,
    "unit": response.selected_candidate.unit,
    "notes": notes_val,
}
if filtered_dim_cols:
    m_parts = [
        str(row[dc]).strip()
        for dc in filtered_dim_cols
        if dc in row and not pd.isna(row[dc])
    ]
    if m_parts:
        single_item["member"] = " / ".join(m_parts)

payload = {
    "observation_exists": True,
    "indicator_id": empirical_id,
    "indicator_name": response.selected_candidate.name,
    "value": val,
    "unit": response.selected_candidate.unit,
    "country": response.applied_filters.country_name
    or response.applied_filters.country_code,
    "year": row_year,
    "dimensions_applied": [
        f.model_dump() for f in response.applied_filters.dimensions
    ],
    "notes": notes_val,
    "series": [single_item],
}
```

### E. Extractor Mock Compatibility
In `_load_indicator_data`, DataFrame return types are verified (`isinstance(res, pd.DataFrame)`), ensuring mock objects with auto-generated methods do not hijack data loading. In `SemanticDataFetcher.__init__`, if `client` is provided with `get_dataframe` (e.g. `MagicMock`), `self.extractor` delegates directly to `client`.

---

## 3. TDD Workflow & Verification Evidence

### Step 1: Red Tests
Added 3 failing tests to `tests/test_semantic_fetcher.py`:
- `test_fetcher_empirical_mapping_3340_to_3324_matches_quintil_column_and_members`
- `test_fetcher_empirical_mapping_3340_to_3390_matches_decil_column_and_members`
- `test_fetcher_empirical_mapping_3340_to_3295_relacion_q5_q1`

```
FAILED tests/test_semantic_fetcher.py::test_fetcher_empirical_mapping_3340_to_3324_matches_quintil_column_and_members
FAILED tests/test_semantic_fetcher.py::test_fetcher_empirical_mapping_3340_to_3390_matches_decil_column_and_members
FAILED tests/test_semantic_fetcher.py::test_fetcher_empirical_mapping_3340_to_3295_relacion_q5_q1
3 failed, 18 deselected in 1.58s
```

### Step 2: Implementation & Green Tests
Following implementation in `src/statscepal/semantic/fetcher.py`:
```
tests/test_semantic_fetcher.py::test_fetcher_empirical_mapping_3340_to_3324_matches_quintil_column_and_members PASSED [ 33%]
tests/test_semantic_fetcher.py::test_fetcher_empirical_mapping_3340_to_3390_matches_decil_column_and_members PASSED [ 66%]
tests/test_semantic_fetcher.py::test_fetcher_empirical_mapping_3340_to_3295_relacion_q5_q1 PASSED [100%]
3 passed, 18 deselected in 1.33s
```

### Step 3: Full Test Suite Verification
1. **Semantic Fetcher Suite:**
   `uv run pytest tests/test_semantic_fetcher.py -v` -> **21 passed in 7.54s**
2. **200-Question Semantic Benchmark Suite:**
   `uv run pytest tests/test_semantic_benchmark_200.py -v` -> **11 passed in 1.52s** (100.0% Top-1 Accuracy, 0.00% False Substitution Rate)
3. **Full Non-Integration Suite:**
   `uv run pytest -m "not integration"` -> **313 passed, 3 deselected in 43.67s** (0 regressions)

---

## 4. Deliverables & Git Status

- **Commit:** `4724f32`
- **Files Modified:**
  - `src/statscepal/semantic/fetcher.py`
  - `tests/test_semantic_fetcher.py`
- **Diff File:** `.superpowers/sdd/2026-10-17-retrospective-remediation-and-hardening-plan/review-403bc8b..4724f32.diff`
- **Working Tree:** Clean, no stray untracked files.
