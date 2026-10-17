# Task 1 Report: Generic Multi-Member Breakdowns in FacetOntology & QueryParser

## Summary
Successfully implemented generic multi-member breakdowns across `sexo`, `area`, `edad`, and `estrato` (`DECIL`) in `FacetOntology` and `QueryParser`. Generic queries such as `"pobreza por sexo"`, `"pobreza por area"`, `"pobreza por edad"`, and `"distribucion del ingreso por deciles"` now accurately resolve to their respective indicator breakdowns with `is_breakdown=True` without false collapsing to implicit national or total aggregates.

- **Status:** DONE
- **Commit:** `77abc62e8ffb702ac2bcf7227e839e919080aca8`
- **Working Tree:** Clean (excluding untracked plan document)

---

## Changes Implemented

### 1. `src/statscepal/semantic/facet_ontology.py`
- **Facet `sexo`:**
  - Added `"SEXO_DESGLOSE": ("hombres", "mujeres")` to `member_value_patterns`.
  - Added `breakdown_values=frozenset({"SEXO_DESGLOSE"})`.
  - Prepended `QueryTriggerRule(canonical_value="SEXO_DESGLOSE", phrases=("por sexo", "segun sexo", "por genero", "segun genero"))` to `query_triggers`.
- **Facet `area`:**
  - Added `"AREA_DESGLOSE": ("urbano", "rural")` to `member_value_patterns`.
  - Added `breakdown_values=frozenset({"AREA_DESGLOSE"})`.
  - Prepended `QueryTriggerRule(canonical_value="AREA_DESGLOSE", phrases=("por area", "segun area", "por area geografica", "segun area geografica", "urbano y rural", "urbana y rural"))` to `query_triggers`.
- **Facet `edad`:**
  - Added `"EDAD_DESGLOSE": ("0 a 14", "15 a 24", "65")` to `member_value_patterns`.
  - Added `breakdown_values=frozenset({"EDAD_DESGLOSE"})`.
  - Prepended `QueryTriggerRule(canonical_value="EDAD_DESGLOSE", phrases=("por edad", "segun edad", "por grupo de edad", "por grupos de edad", "segun grupo de edad", "segun grupos de edad"))` to `query_triggers`.
- **Facet `estrato`:**
  - Updated `breakdown_values=frozenset({"QUINTIL", "DECIL"})`.
  - Maintained `member_value_patterns["DECIL"] = ("decil", "deciles")`.
- **`FacetOntology.extract_facets_from_query`:**
  - Added prioritized evaluation of `QueryTriggerRule`s for `breakdown_values` before single-term synsets to ensure multi-word phrases like `"urbano y rural"` and generic `"por area"` are not shadowed by single-token matches.

### 2. `src/statscepal/semantic/parser.py`
- **Area Extraction:**
  - Added upfront detection of `"urbano y rural"` / `"urbana y rural"` directly mapping to `"AREA_DESGLOSE"` prior to single-token checks.
- **Generic Ontology Facet Extraction:**
  - Updated facet absorption loop to retain generic breakdown values (`AREA_DESGLOSE`, `SEXO_DESGLOSE`, `EDAD_DESGLOSE`) and overwrite implicit aggregate values (`NACIONAL`, `AMBOS`, `TOTAL`) while preserving explicit specific non-aggregate facet selections.
- **Implicit Aggregate Guardrails:**
  - Ensured root concept default setters (`if "area" not in facets: facets["area"] = "NACIONAL"` and `if "sexo" not in facets: facets["sexo"] = "AMBOS"`) do not overwrite existing breakdown values.

### 3. `tests/test_semantic_breakdowns.py`
- Appended `test_generic_breakdowns_for_sexo_area_edad_and_deciles` asserting:
  1. `"pobreza por sexo en peru 2022"` swaps to 3341 and binds `Sexo__ESTANDAR` with `is_breakdown=True` containing `Hombres` and `Mujeres`.
  2. `"pobreza por area en peru 2022"` stays on 3328 and binds `Área geográfica` with `is_breakdown=True` containing `Urbano` and `Rural`.
  3. `"pobreza por edad en peru 2022"` swaps to 3341 and binds `Grupo de edad` with `is_breakdown=True` containing at least 3 age groups.
  4. `"distribucion del ingreso por deciles en peru 2022"` resolves to 3340 and binds `Estrato de ingreso` with `is_breakdown=True` containing `Primer decil`, `Décimo decil`, `Deciles`.

---

## Verification Results

| Suite / Test | Result | Execution Time |
|---|---|---|
| `test_generic_breakdowns_for_sexo_area_edad_and_deciles` (RED test) | FAILED (assert 3328 in (3341, 3342)) | 1.37s |
| `test_generic_breakdowns_for_sexo_area_edad_and_deciles` (GREEN test) | PASSED | 1.62s |
| `tests/test_semantic_breakdowns.py` (Full) | 10 passed | 1.72s |
| `tests/test_semantic_facet_coverage.py` (Facet Coverage Matrix) | 17 passed | 1.17s |
| `tests/test_semantic_benchmark_200.py` (200-Question Benchmark) | 11 passed (100.0% Top-1, 0.00% FSR) | 1.25s |
| `uv run pytest -m "not integration"` (Full Non-Integration Suite) | 290 passed, 3 deselected | 33.52s |

---

## Constraints Verification
- **Python 3.10+ modern typing syntax:** Confirmed.
- **Offline Hermeticity:** Confirmed, no live HTTP requests made.
- **Benchmark Top-1 Accuracy:** 100.0% maintained.
- **False Substitution Rate:** 0.00% maintained.
- **Resolution Latency:** Maintained well within p50 < 0.5 ms.
- **Diff Hygiene:** Only the 3 designated files were modified.

## Concerns / Notes
None. Ready to proceed to Task 2.
