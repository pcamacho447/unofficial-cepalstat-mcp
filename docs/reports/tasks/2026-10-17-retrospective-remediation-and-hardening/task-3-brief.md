# Task 3 Brief: Seed `DEFAULT_OFFICIAL_DIMENSIONS` for Vertical Slice Indicators & Protect Explicit Breakdowns (`AI-4`)

**Implementer:** Amelia, Senior Developer  
**Plan:** [`docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md)  
**Base Commit:** `c9b5f90`  

---

## 1. What to Build

### A. Seed `DEFAULT_OFFICIAL_DIMENSIONS` for the 10 Missing Vertical Slice Indicators
In `src/statscepal/semantic/registry.py`:
Currently, 10 indicators in `VERTICAL_SLICE_INDICATORS` declare non-empty `supported_facets` but are missing from `DEFAULT_OFFICIAL_DIMENSIONS`:
`127, 3331, 3337, 5097, 119, 340, 365, 1684, 3344, 3333`.

Add dimension entries for each of these 10 indicators in `DEFAULT_OFFICIAL_DIMENSIONS` using standard shared dimensions:
- `127` (*Tasa de desocupación por sexo*, `{'sexo', 'formalidad'}`):
  - `dim_id=144`, name=`"Sexo__ESTANDAR"` with members `146: "Ambos sexos"`, `265: "Hombres"`, `266: "Mujeres"`.
- `3331` (*Tasa de desempleo juvenil de 15 a 24 años*, `{'sexo', 'edad'}`):
  - `dim_id=144`, name=`"Sexo__ESTANDAR"` (`146: Ambos sexos, 265: Hombres, 266: Mujeres`).
  - `dim_id=43054`, name=`"Grupo de edad"` (`43058: "15 a 24 años"`).
- `3337` (*Salario mínimo real*, `{'area', 'edad'}`):
  - `dim_id=326`, name=`"Área geográfica"` (`327: Nacional, 330: Urbano, 331: Rural`).
- `5097` (*Tasa de desempleo, por sexo y edad - 19° CIET (%)*, `{'sexo', 'edad'}`):
  - `dim_id=144`, name=`"Sexo__ESTANDAR"` (`146: Ambos sexos, 265: Hombres, 266: Mujeres`).
  - `dim_id=43054`, name=`"Grupo de edad"` (`43059: "0 a 14 años"`, `43058: "15 a 24 años"`, `43060: "65 años y más"`).
- `119` (*Tasa de desocupación abierta en el área urbana, por sexo y años de educación*, `{'sexo', 'educacion', 'area'}`):
  - `dim_id=144`, name=`"Sexo__ESTANDAR"` (`146: Ambos sexos, 265: Hombres, 266: Mujeres`).
  - `dim_id=326`, name=`"Área geográfica"` (`327: Nacional, 330: Urbano, 331: Rural`).
- `340` (*Salario mínimo real*, `{'area', 'edad'}`):
  - `dim_id=326`, name=`"Área geográfica"` (`327: Nacional, 330: Urbano, 331: Rural`).
- `365` (*Índice de precios al consumidor general*, `{'rubro'}`):
  - `dim_id=29281`, name=`"Rubro"` (`29282: "General"`).
- `1684` (*Índice de precios al consumidor, alimentos y bebidas*, `{'canasta'}`):
  - `dim_id=79565`, name=`"Canasta de bienes"` (`79578: "Alimentos y bebidas no alcohólicas"`).
- `3344` (*Tasa de desocupación según sexo y edad*, `{'sexo', 'edad'}`):
  - `dim_id=144`, name=`"Sexo__ESTANDAR"` (`146: Ambos sexos, 265: Hombres, 266: Mujeres`).
  - `dim_id=43054`, name=`"Grupo de edad"` (`43059: "0 a 14 años"`, `43058: "15 a 24 años"`, `43060: "65 años y más"`).
- `3333` (*Relación de ingresos laborales por sexo*, `{'sexo'}`):
  - `dim_id=144`, name=`"Sexo__ESTANDAR"` (`146: Ambos sexos, 265: Hombres, 266: Mujeres`).

*Ensure all shared `dim_id` definitions use consistent member IDs and names so `test_default_official_dimensions_shared_dim_id_consistency` passes.*

Add an invariant test `test_vertical_slice_indicators_with_supported_facets_have_default_official_dimensions` in `tests/test_semantic_registry_200.py`.

### B. Protect Explicit User Breakdown Dimensions in `_filter_unconstrained_dimensions`
In `src/statscepal/semantic/fetcher.py`:
Update `_filter_unconstrained_dimensions` (or pass `response` / `breakdown_facets: set[str]`):
Extract all facet keys requested as breakdown:
```python
facet_keys_in_breakdown = {
    f_k.lower()
    for f_k, f_v in response.applied_filters.facets.items()
    if "_DESGLOSE" in str(f_v) or f_v in ("ETNICO_TOTAL", "ETNICO")
}
```
If any `bk` in `facet_keys_in_breakdown` matches the column name (e.g. `"sexo"` in `_strip_accents(col).lower()`, `"area"` in `_strip_accents(col).lower()`), DO NOT collapse that column to aggregate.

Add a unit test in `tests/test_semantic_fetcher.py`:
`test_fetcher_does_not_collapse_dimension_when_requested_as_breakdown`.

---

## 2. Test-Driven Development (TDD) Workflow

1. Add the failing tests to `tests/test_semantic_registry_200.py` and `tests/test_semantic_fetcher.py`.
2. Run red tests:
   `uv run pytest tests/test_semantic_registry_200.py -k test_vertical_slice_indicators_with_supported_facets_have_default_official_dimensions`
   `uv run pytest tests/test_semantic_fetcher.py -k test_fetcher_does_not_collapse_dimension_when_requested_as_breakdown`
3. Implement dimensions in `src/statscepal/semantic/registry.py` and safeguard in `src/statscepal/semantic/fetcher.py`.
4. Run green tests:
   `uv run pytest tests/test_semantic_registry_200.py tests/test_semantic_fetcher.py -v`
   `uv run pytest tests/test_semantic_benchmark_200.py -v`
   `uv run pytest -m "not integration"`
5. Commit:
   `git add src/statscepal/semantic/registry.py src/statscepal/semantic/fetcher.py tests/test_semantic_registry_200.py tests/test_semantic_fetcher.py`
   `git commit -m "feat(semantic): seed dimensions for vertical slice indicators and preserve explicit breakdown dimensions"`
6. Write your task report to `C:\papx\statscepal\.superpowers\sdd\2026-10-17-retrospective-remediation-and-hardening-plan\task-3-report.md`.
