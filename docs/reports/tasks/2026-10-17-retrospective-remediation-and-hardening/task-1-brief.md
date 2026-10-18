# Task 1 Brief: Member ID Collision Isolation in `3342` & Accent-Insensitive Matching in `SemanticDataFetcher` Step 5 (`AI-1` & `AI-2`)

**Implementer:** Amelia, Senior Developer  
**Plan:** [`docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md)  
**Base Commit:** `8d6bd7a`  

---

## 1. What to Build

### A. Fix `dim_id=43039` Member Collision in `DEFAULT_OFFICIAL_DIMENSIONS[3342]` (`AI-1`)
In `src/statscepal/semantic/registry.py`:
Currently, `DEFAULT_OFFICIAL_DIMENSIONS[3342]` defines `dim_id=43039` with synthetic sequential IDs (`43040="Afrodescendiente"`, `43041="Indígena"`, `43042="No indígena ni afrodescendiente"`, `43043="Total"`).
In contrast, `DEFAULT_OFFICIAL_DIMENSIONS[4639]` registers the real CEPALSTAT member IDs for `dim_id=43039`:
`43040: "Total"`, `43044: "Afrodescendiente"`, `77477: "Indígena"`, `43043: "No indígena ni afrodescendiente"`.
Notice that `43040` in real CEPALSTAT is `"Total"`, but `3342` mapped it to `"Afrodescendiente"`.

**Fix:** Update `DEFAULT_OFFICIAL_DIMENSIONS[3342]` to match real member IDs:
```python
{
    "dim_id": 43039,
    "dim_name": "Tipo de etnia",
    "members": {
        43040: "Total",
        43044: "Afrodescendiente",
        77477: "Indígena",
        43043: "No indígena ni afrodescendiente",
    },
    "members_by_value": {
        "TOTAL": 43040,
        "AFRODESCENDIENTE": 43044,
        "INDIGENA": 77477,
        "NO_INDIGENA": 43043,
    },
}
```

Add an invariant test `test_default_official_dimensions_shared_dim_id_consistency` in `tests/test_semantic_registry_200.py` verifying that every shared `dim_id` across `DEFAULT_OFFICIAL_DIMENSIONS` maps identical `member_id` to identical semantic values.

### B. Accent-Insensitive Matching in `SemanticDataFetcher` Step 5 (`AI-2`)
In `src/statscepal/semantic/fetcher.py`:
Define a helper method `_match_dim_column(col_name: str, target_name: str) -> bool`:
```python
def _match_dim_column(col_name: str, target_name: str) -> bool:
    cl = _strip_accents(col_name).lower().strip().replace("__estandar", "")
    dl = _strip_accents(target_name).lower().strip().replace("__estandar", "")
    return cl == dl or cl.replace(" ", "") == dl.replace(" ", "")
```
Replace the column comparison in Step 2 (`fetcher.py:438-445`) and Step 5 (`fetcher.py:690-701`) with calls to `_match_dim_column`.
Add a test in `tests/test_semantic_fetcher.py` (`test_fetcher_step5_breakdown_cols_matches_accented_dataframe_columns`) verifying that a DataFrame column with diacritics (e.g. `"Área geográfica"`) populates `breakdown_cols` and assigns `"member"` labels when `dim_name` is `"Area Geografica"`.

---

## 2. Test-Driven Development (TDD) Workflow

1. Write the failing tests in `tests/test_semantic_registry_200.py` and `tests/test_semantic_fetcher.py`.
2. Run red tests:
   `uv run pytest tests/test_semantic_registry_200.py -k test_default_official_dimensions_shared_dim_id_consistency`
   `uv run pytest tests/test_semantic_fetcher.py -k test_fetcher_step5_breakdown_cols_matches_accented_dataframe_columns`
3. Implement minimal changes in `src/statscepal/semantic/registry.py` and `src/statscepal/semantic/fetcher.py`.
4. Run green tests:
   `uv run pytest tests/test_semantic_registry_200.py tests/test_semantic_fetcher.py -v`
   `uv run pytest tests/test_semantic_benchmark_200.py -v`
   `uv run pytest -m "not integration"`
5. Commit:
   `git add src/statscepal/semantic/registry.py src/statscepal/semantic/fetcher.py tests/test_semantic_registry_200.py tests/test_semantic_fetcher.py`
   `git commit -m "fix(semantic): isolate 3342 member IDs and unify accent-insensitive column matching in fetcher"`
6. Write your task report to `C:\papx\statscepal\.superpowers\sdd\2026-10-17-retrospective-remediation-and-hardening-plan\task-1-report.md`.
