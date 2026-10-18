# Task 2 Brief: Concept Precedence Correction for `POBLACION` vs `DISTRIBUCION_INGRESO` & Reachability of Indicator `4639` (`AI-3`)

**Implementer:** Amelia, Senior Developer  
**Plan:** [`docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md)  
**Base Commit:** `cebde1c`  

---

## 1. What to Build

### A. Precedence in `src/statscepal/semantic/parser.py:736-808`
In `QueryParser.parse`:
Currently, `DISTRIBUCION_INGRESO` (checking for `"quintil"`, `"decil"`, etc. at lines 736-751) triggers before `POBLACION` (line 807).
When a query is `"poblacion indigena por quintil en peru 2021"`, it gets captured by `DISTRIBUCION_INGRESO` (`3340`), which then abstains on unsupported facet `"etnia"`.

**Fix:** In the `DISTRIBUCION_INGRESO` branch (or by checking `POBLACION` keywords):
If any demographic token (`"poblacion"`, `"habitantes"`, `"personas"`, or ethnic tokens `"indigena"`, `"afrodescendiente"`) is present alongside quintile/decile terms, assign:
`intent.root_concept = "POBLACION"`
and preserve the extracted `estrato` / `quintil` facet.

### B. Specific Ethnic Priority in `src/statscepal/semantic/facet_ontology.py`
In `FacetOntology.extract_facets_from_query` or the `etnia` `FacetDefinition`:
Currently, `ETNICO_TOTAL` is in `breakdown_values`, and its phrases include bare `"etnico"`, `"etnia"`.
In `"poblacion del grupo etnico afrodescendiente"`, `ETNICO_TOTAL` matches `"etnico"` during the breakdown phase, setting `facets["etnia"] = "ETNICO_TOTAL"` and missing `AFRODESCENDIENTE`.

**Fix:** Ensure specific member patterns/rules (`INDIGENA`, `AFRODESCENDIENTE`, `NO_INDIGENA`) take precedence over generic `ETNICO_TOTAL` (e.g. only match `ETNICO_TOTAL` if neither `INDIGENA` nor `AFRODESCENDIENTE` nor `NO_INDIGENA` is in the query, or evaluate specific triggers first).

### C. Routing in `src/statscepal/semantic/engine.py:43-53`
In `_route_population_indicator(facets: dict[str, str]) -> int`:
```python
@staticmethod
def _route_population_indicator(facets: dict[str, str]) -> int:
    has_etnia = "etnia" in facets
    has_estrato = "estrato" in facets or "quintil" in facets
    area_val = facets.get("area")
    has_area = "area" in facets and area_val not in (None, "NACIONAL", "TOTAL", "AMBOS")

    # 1. Quintiles and ethnicity -> 4639 (highest specificity)
    if has_estrato and has_etnia:
        return 4639
    # 2. Specific ethnicity breakdowns:
    if facets.get("etnia") == "AFRODESCENDIENTE":
        return 4969
    if has_etnia:
        return 4968
    # 3. Area breakdown without ethnicity -> 4992
    if has_area:
        return 4992
    # 4. Canonical total population -> 4788
    return 4788
```

### D. Unit Tests in `tests/test_semantic_breakdowns.py`
Add tests:
- `test_poblacion_por_quintil_y_etnia_routes_to_indicator_4639`
- `test_poblacion_especifica_afrodescendiente_no_bloqueada_por_etnico_total`
- `test_poblacion_por_area_urbana_rural_routes_to_indicator_4992`

---

## 2. Test-Driven Development (TDD) Workflow

1. Add the failing tests to `tests/test_semantic_breakdowns.py`.
2. Run red tests: `uv run pytest tests/test_semantic_breakdowns.py -k "test_poblacion_por_quintil or test_poblacion_especifica or test_poblacion_por_area" -v`
3. Implement the fixes in `src/statscepal/semantic/parser.py`, `src/statscepal/semantic/facet_ontology.py`, and `src/statscepal/semantic/engine.py`.
4. Run green tests:
   `uv run pytest tests/test_semantic_breakdowns.py -v`
   `uv run pytest tests/test_semantic_benchmark_200.py -v`
   `uv run pytest tests/test_semantic_facet_coverage.py -v`
   `uv run pytest -m "not integration"`
5. Commit:
   `git add src/statscepal/semantic/parser.py src/statscepal/semantic/facet_ontology.py src/statscepal/semantic/engine.py tests/test_semantic_breakdowns.py`
   `git commit -m "fix(semantic): resolve POBLACION precedence, support 4639 and 4992, and prioritize specific ethnic groups"`
6. Write your task report to `C:\papx\statscepal\.superpowers\sdd\2026-10-17-retrospective-remediation-and-hardening-plan\task-2-report.md`.
