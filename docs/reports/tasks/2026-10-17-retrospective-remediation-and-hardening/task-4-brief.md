# Task 4 Brief: Dimension & Member Alias Resolution on Empirical Remapping `3340 -> 3295 / 3324 / 3390` (`AI-5`)

**Implementer:** Amelia, Senior Developer  
**Plan:** [`docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md)  
**Base Commit:** `403bc8b`  

---

## 1. What to Build

### A. Dimension & Member Alias Resolution in `src/statscepal/semantic/fetcher.py`
When `3340` (*Distribución del ingreso por estratos*) dynamically maps to:
- `3324`: *Distribución del ingreso por quintiles*
- `3390`: *Distribución del ingreso por deciles*
- `3295`: *Relación de ingresos entre el quintil 5 y el quintil 1*

The physical DataFrame columns in CEPALSTAT tables `3324` and `3390` are `"Quintil"` (or `"Quintiles"`) and `"Decil"` (or `"Deciles"`), whereas `response.applied_filters.dimensions` contains `dim_name="Estrato de ingreso"`.
Furthermore, the member values in `3340` are descriptive (e.g. `"Primer quintil"`, `"Quinto quintil"`, `"Primer decil"`), whereas the DataFrame rows have `"Quintil 1"`, `"Quintil 5"`, `"Decil 1"`, `"Decil 10"`, `"I"`, `"V"`, `"X"`, etc.

**Changes required in `fetcher.py`:**
1. Define aliases at top or class level:
```python
DIM_NAME_ALIASES: dict[str, list[str]] = {
    "estrato de ingreso": ["quintil", "decil", "estrato", "quintiles", "deciles"],
}

MEMBER_VALUE_ALIASES: dict[str, list[str]] = {
    "primer quintil": ["quintil 1", "i", "quintil i", "1", "q1", "i quintil"],
    "segundo quintil": ["quintil 2", "ii", "quintil ii", "2", "q2", "ii quintil"],
    "tercer quintil": ["quintil 3", "iii", "quintil iii", "3", "q3", "iii quintil"],
    "cuarto quintil": ["quintil 4", "iv", "quintil iv", "4", "q4", "iv quintil"],
    "quinto quintil": ["quintil 5", "v", "quintil v", "5", "q5", "v quintil"],
    "primer decil": ["decil 1", "i", "decil i", "1", "d1", "i decil"],
    "segundo decil": ["decil 2", "ii", "decil ii", "2", "d2", "ii decil"],
    "decimo decil": ["decil 10", "x", "decil x", "10", "d10", "x decil"],
}
```
2. Update `_match_dim_column(col_name: str, target_name: str) -> bool` or dimension search in Step 2 & Step 5:
   If `_match_dim_column(col, dim_filter.dim_name)` is False, check if `_strip_accents(col).lower()` matches any alias in `DIM_NAME_ALIASES.get(_strip_accents(dim_filter.dim_name).lower(), [])`.
3. In Step 2 member matching (`fetcher.py:492-510`):
   When matching member name `m_name`, normalize it: `norm_m = _strip_accents(m_name).lower().strip()`.
   Build acceptable forms: `acceptable_forms = {norm_m} | set(MEMBER_VALUE_ALIASES.get(norm_m, []))`.
   Match if `filtered_df[dim_col].astype(str).str.strip().map(lambda s: _strip_accents(s).lower()).isin(acceptable_forms)`.

### B. Unit Tests in `tests/test_semantic_fetcher.py`
Add tests:
- `test_fetcher_empirical_mapping_3340_to_3324_matches_quintil_column_and_members`
- `test_fetcher_empirical_mapping_3340_to_3390_matches_decil_column_and_members`
- `test_fetcher_empirical_mapping_3340_to_3295_relacion_q5_q1`

---

## 2. Test-Driven Development (TDD) Workflow

1. Add the failing tests to `tests/test_semantic_fetcher.py`.
2. Run red tests: `uv run pytest tests/test_semantic_fetcher.py -k "test_fetcher_empirical_mapping_3340" -v`
3. Implement aliases and matching in `src/statscepal/semantic/fetcher.py`.
4. Run green tests:
   `uv run pytest tests/test_semantic_fetcher.py -v`
   `uv run pytest tests/test_semantic_benchmark_200.py -v`
   `uv run pytest -m "not integration"`
5. Commit:
   `git add src/statscepal/semantic/fetcher.py tests/test_semantic_fetcher.py`
   `git commit -m "feat(semantic): support dimension and member aliases for empirical income distribution indicators (3324, 3390)"`
6. Write your task report to `C:\papx\statscepal\.superpowers\sdd\2026-10-17-retrospective-remediation-and-hardening-plan\task-4-report.md`.
