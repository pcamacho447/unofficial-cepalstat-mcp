# Semantic False Substitution, Gender Gap & Tax Disambiguation Hardening Plan

This plan remediates the three critical semantic and econometric issues identified in interactive testing:
1. **Underlying Inflation False Substitution**: "Inflación subyacente en Chile" must resolve to official core inflation indicator `4145` (annual) / `764` (index), NEVER falsely substituting general CPI `2928` / `2484`.
2. **Gender Income Gap Facet Mutilation**: "Brecha de ingresos laborales entre mujeres y hombres en Argentina" must resolve to canonical ratio indicator `3333` (empirical `2288`: *Relación del ingreso medio entre mujeres y hombres*), preserving comparison integrity rather than filtering solely to `Mujeres` on single-gender level indicator `3339`.
3. **Tax Revenues Disconnect & Silent Assumption**: "Ingresos tributarios del Perú en 2022" must resolve `info 1242` gracefully via alias mapping to API table `821`, explicitly log the default assumption of `% del PIB` in the execution trace, and emit a `conversational_hint` advertising nominal currency indicator `845`.

## User Review Required

> [!IMPORTANT]
> - All 317 existing non-integration tests must remain green.
> - Benchmark 200 questions must strictly maintain 100.0% Top-1 Accuracy and 0.00% False Substitution Rate.
> - Strict offline hermeticity (no live network calls in unit/benchmark tests).

---

## File Structure & Proposed Changes

### Semantic Engine & Registry
- `src/statscepal/semantic/registry.py`:
  - Register indicator `4145` (*Tasa de crecimiento anual del índice de precios al consumidor subyacente: diciembre a diciembre*) with concept `"IPC_SUBYACENTE"`.
  - Add indicator `845` (*Ingresos tributarios por tipo de impuestos, en moneda nacional a precios corrientes*) as `ALTERNATIVE_MEASURE` to `1242` / `821`.
  - Add `4145` and `845` to `CONCEPT_INDICATOR_INDEX`, `DEFAULT_OFFICIAL_DIMENSIONS`, and `EMPIRICAL_INDICATOR_ID_MAP`.
- `src/statscepal/semantic/parser.py`:
  - Pre-empt generic inflation triggers (`IPC_GENERAL`) when query contains `"subyacente"`, `"core"`, or `"inflacion basica"`, assigning `intent.root_concept = "IPC_SUBYACENTE"`.
  - Expand `BRECHA_SALARIAL` trigger to match `"brecha de ingresos"`, `"brecha de ingresos laborales"`, `"diferencia de ingresos entre"`, `"relacion de ingreso medio entre mujeres y hombres"`.
  - In `facet_ontology.py` and `parser.py`, prevent unilateral `sexo="MUJERES"` or `sexo="HOMBRES"` facet binding when query mentions both sexes or a gender gap/ratio concept.
  - Detect underspecified denomination for `INGRESOS_TRIBUTARIOS` and support explicit `"moneda nacional"` / `"corrientes"` routing to `845`.
- `src/statscepal/semantic/engine.py`:
  - Ensure `conversational_hint` and audit logs record the default `% del PIB` assumption and note alternative `845` when query is underspecified.

### CLI
- `src/statscepal/cli.py`:
  - In `statscepal info <indicator_id>`, check `EMPIRICAL_INDICATOR_ID_MAP` if the given ID is a synthetic official_25 ID (such as `1242 -> 821`, `2928 -> 2484`, `729 -> 2204`). If mapped, fetch and display the empirical table metadata with a note indicating the mapping.

---

## Detailed Implementation Tasks

### Task 1: Underlying Inflation (`IPC_SUBYACENTE`) & Hard Abstention from IPC General

**Files to modify:**
- `src/statscepal/semantic/parser.py`
- `src/statscepal/semantic/registry.py`
- `tests/test_semantic_motivating_remediations.py` (new)

**Step-by-step instructions:**
1. Create `tests/test_semantic_motivating_remediations.py` with failing test:
   ```python
   def test_inflacion_subyacente_routes_to_4145_and_never_2928(engine):
       res = engine.resolve("inflacion subyacente en chile")
       assert res.status == ResolutionStatus.RESOLVED
       assert res.selected_candidate.indicator_id == 4145
       assert res.selected_candidate.indicator_id != 2928
   ```
2. Run test to verify it fails:
   `uv run pytest tests/test_semantic_motivating_remediations.py -k test_inflacion_subyacente -v`
3. In `src/statscepal/semantic/registry.py`:
   - Add `4145` to `VERTICAL_SLICE_INDICATORS` with concept `"IPC_SUBYACENTE"` and measure type `TASA_CRECIMIENTO_ANUAL`.
   - Add `"IPC_SUBYACENTE": 4145` to `CONCEPT_INDICATOR_INDEX`.
   - Add `4145: []` to `DEFAULT_OFFICIAL_DIMENSIONS`.
   - Ensure `4145: 4145` in `EMPIRICAL_INDICATOR_ID_MAP`.
4. In `src/statscepal/semantic/parser.py`:
   - Prioritize `"subyacente"`, `"core"`, `"inflacion basica"` before `IPC_GENERAL` in the Precios section:
     ```python
     elif any(term in clean for term in ["subyacente", "core", "inflacion basica", "precios subyacentes"]):
         intent.root_concept = "IPC_SUBYACENTE"
     ```
5. Run test to verify it passes:
   `uv run pytest tests/test_semantic_motivating_remediations.py -k test_inflacion_subyacente -v`
6. Commit:
   `git add src/statscepal/semantic/registry.py src/statscepal/semantic/parser.py tests/test_semantic_motivating_remediations.py`
   `git commit -m "fix(semantic): resolve underlying inflation to 4145 and prevent false substitution to general CPI"`

---

### Task 2: Gender Income Gap Concept Expansion (`3333` / `2288`) & Comparative Facet Integrity

**Files to modify:**
- `src/statscepal/semantic/parser.py`
- `src/statscepal/semantic/facet_ontology.py`
- `tests/test_semantic_motivating_remediations.py`

**Step-by-step instructions:**
1. Add failing tests to `tests/test_semantic_motivating_remediations.py`:
   ```python
   def test_brecha_ingresos_laborales_mujeres_y_hombres_routes_to_3333(engine):
       res = engine.resolve("brecha de ingresos laborales entre mujeres y hombres en argentina")
       assert res.status == ResolutionStatus.RESOLVED
       assert res.selected_candidate.indicator_id == 3333
       assert "sexo" not in res.query_intent.facets
   ```
2. Run test to verify it fails:
   `uv run pytest tests/test_semantic_motivating_remediations.py -k test_brecha_ingresos_laborales -v`
3. In `src/statscepal/semantic/parser.py`:
   - Expand `BRECHA_SALARIAL` detection to include phrases with `"brecha de ingresos"`, `"brecha de ingresos laborales"`, `"diferencia de ingresos entre"`, `"relacion de ingreso medio entre mujeres y hombres"`, `"brecha salarial de genero"`.
   - In facet extraction, if clean query contains both `"mujeres"` and `"hombres"`, or contains a gap/ratio concept on gender, do not set `sexo="MUJERES"`.
4. Run test to verify it passes:
   `uv run pytest tests/test_semantic_motivating_remediations.py -k test_brecha_ingresos_laborales -v`
5. Commit:
   `git add src/statscepal/semantic/parser.py src/statscepal/semantic/facet_ontology.py tests/test_semantic_motivating_remediations.py`
   `git commit -m "fix(semantic): route gender income gap queries to 3333 and protect comparison against unilateral sex filtering"`

---

### Task 3: Tax Revenues: Alias Resolution in CLI `info`, Explicit Nominal Routing, and Underspecification Trace/Hint

**Files to modify:**
- `src/statscepal/semantic/parser.py`
- `src/statscepal/semantic/registry.py`
- `src/statscepal/semantic/engine.py`
- `src/statscepal/cli.py`
- `tests/test_semantic_motivating_remediations.py`
- `tests/test_cli_semantic.py`

**Step-by-step instructions:**
1. Add failing tests:
   ```python
   def test_ingresos_tributarios_underspecified_generates_conversational_hint_and_alternative(engine):
       res = engine.resolve("quiero que me des los ingresos tributarios del peru en 2022")
       assert res.status == ResolutionStatus.RESOLVED
       assert res.selected_candidate.indicator_id == 1242
       assert res.conversational_hint is not None
       assert "845" in res.conversational_hint

   def test_ingresos_tributarios_moneda_nacional_routes_to_845(engine):
       res = engine.resolve("ingresos tributarios en moneda nacional en peru 2022")
       assert res.status == ResolutionStatus.RESOLVED
       assert res.selected_candidate.indicator_id == 845
   ```
2. In `cli.py`:
   - In `_handle_info`: Check `EMPIRICAL_INDICATOR_ID_MAP.get(parsed.indicator_id)`. If present and different, use empirical ID for retrieval and print header:
     `=== Indicator {emp_id} (Mapped from official_25 canonical ID {parsed.indicator_id}) ===`
3. In `registry.py`:
   - Register indicator `845` with concept `"INGRESOS_TRIBUTARIOS_CORRIENTES"` as `ALTERNATIVE_MEASURE` to `1242`.
   - Add `845: 845` in `EMPIRICAL_INDICATOR_ID_MAP`.
4. In `parser.py` & `engine.py`:
   - If query asks for `"en moneda nacional"` / `"a precios corrientes"` for tax revenues, assign root concept `INGRESOS_TRIBUTARIOS_CORRIENTES`.
   - If query is generic ("ingresos tributarios"), select `1242`, log default `% del PIB` assumption in trace, and emit hint referencing `845`.
5. Run tests to verify they pass:
   `uv run pytest tests/test_semantic_motivating_remediations.py -v`
   `uv run pytest tests/test_cli_semantic.py -v`
6. Commit:
   `git add src/statscepal/semantic/parser.py src/statscepal/semantic/registry.py src/statscepal/semantic/engine.py src/statscepal/cli.py tests/test_semantic_motivating_remediations.py tests/test_cli_semantic.py`
   `git commit -m "feat(semantic,cli): support tax revenue alias in info, explicit nominal routing, and conversational hint for default GDP share"`

---

### Task 4: End-to-End Regression Verification & 200-Question Benchmark Certification

**Files to modify:**
- `tests/test_semantic_motivating_remediations.py`

**Step-by-step instructions:**
1. Run benchmark suite:
   `uv run pytest tests/test_semantic_benchmark_200.py -v`
   Verify: 100.0% Top-1 Accuracy, 0.00% False Substitution Rate.
2. Run full non-integration test suite:
   `uv run pytest -m "not integration"`
   Verify: all 317+ tests pass.
3. Verify interactive CLI executions:
   - `uv run statscepal semantic resolve "inflacion subyacente en chile" --explain`
   - `uv run statscepal semantic resolve "brecha de ingresos laborales entre mujeres y hombres en argentina" --explain`
   - `uv run statscepal semantic resolve "quiero que me des los ingresos tributarios del peru en 2022" --explain`
   - `uv run statscepal info 1242`
4. Commit any polish and archival reports:
   `git commit -m "test(semantic): certify end-to-end fixes for underlying inflation, gender gap, and tax revenues"`
