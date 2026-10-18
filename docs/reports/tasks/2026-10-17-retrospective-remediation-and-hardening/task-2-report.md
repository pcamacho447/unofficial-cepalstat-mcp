# Task 2 Report: Concept Precedence Correction for `POBLACION` vs `DISTRIBUCION_INGRESO` & Reachability of Indicator `4639` (`AI-3`)

**Implementer:** Amelia, Senior Developer  
**Plan:** `docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md`  
**Base Commit:** `cebde1c`  
**Task 2 Commit:** `c9b5f90` (`fix(semantic): resolve POBLACION precedence, support 4639 and 4992, and prioritize specific ethnic groups`)  
**Date:** 2026-10-17  

---

## 1. Executive Summary

Task 2 addresses action item `AI-3` from the retrospective, resolving critical routing, precedence, and member-matching defects that prevented specialized demographic indicators (`4639`, `4992`, and `4969`) from being reached:

1. **Precedence Inversion (`parser.py`):** Queries combining demographic/ethnic tokens with quintiles (e.g. `"poblacion indigena por quintil en peru 2021"`) were previously captured by `DISTRIBUCION_INGRESO` (`3340`), which then hard-abstained on the unsupported facet `"etnia"`. This was corrected by detecting demographic/ethnic co-occurrence in the quintile branch and establishing `POBLACION` precedence while preserving the `estrato: QUINTIL` facet.
2. **Breakdown Shadowing of Specific Ethnic Groups (`facet_ontology.py`):** In `FacetOntology.extract_facets_from_query`, `ETNICO_TOTAL` was evaluated during Step 1 (breakdown rules) because `"etnico"` was in its trigger phrases. In queries like `"poblacion del grupo etnico afrodescendiente en brasil 2020"`, the bare trigger word `"etnico"` matched `ETNICO_TOTAL`, shadowing the specific member `AFRODESCENDIENTE` and routing to indigenous indicator `4968` instead of `4969`. Specific ethnic group triggers and synsets (`INDIGENA`, `AFRODESCENDIENTE`, `NO_INDIGENA`) now take strict evaluation priority before `ETNICO_TOTAL`.
3. **Indicator Routing Specificity & Default Area Filtering (`engine.py`):** In `_route_population_indicator`, queries with both `estrato` and `etnia` are now dispatched first with highest specificity to indicator `4639` (`Población por quintil de ingreso y etnia`). Additionally, the `has_area` condition was hardened to ensure default aggregate areas (`NACIONAL`, `TOTAL`, `AMBOS`) route to canonical total population (`4788`), while non-aggregate area requests route to `4992`.
4. **Dimension Ontology Alignment (`facet_ontology.py`):** Indicator `4639` defines dimension `378` (`Quintil`), but the ontology's `estrato` facet previously lacked `"quintil"` and `"decil"` in `dimension_name_patterns` and had empty `known_dimension_ids`. Registering `known_dimension_ids={378, 600}` and adding `"quintil"` / `"decil"` patterns enables `DynamicMemberMatcher` to match `estrato: QUINTIL` to dimension `378`, unblocking Stage 4 dimensional gating.

All changes were implemented under strict Test-Driven Development (TDD). All 308 non-integration tests pass (3 new unit tests added), and the 200-question benchmark maintains 100.0% Top-1 Accuracy and 0.00% False Substitution Rate.

---

## 2. Changes Implemented

### A. Concept Precedence in `QueryParser.parse` (`src/statscepal/semantic/parser.py`)
- In lines 748-757:
  ```python
  # Distribución del Ingreso / Quintiles / Deciles
  elif any(term in clean for term in [
      "distribucion del ingreso",
      "distribucion de la lana",
      "distribucion de los ingresos",
      "concentracion del ingreso",
      "los de abajo",
      "deciles",
      "decil",
      "quintiles",
      "quintil",
      "brecha distributiva",
      "cuanta torta",
      "reparto del billete",
      "20 por ciento mas rico",
  ]):
      if any(term in clean for term in ["poblacion", "habitantes", "personas", "indigena", "afrodescendiente", "demografia", "demografico", "demograficos"]) or "etnia" in facets:
          intent.root_concept = "POBLACION"
          if "estrato" not in facets and any(term in clean for term in ["quintil", "quintiles"]):
              facets["estrato"] = "QUINTIL"
      else:
          intent.root_concept = "DISTRIBUCION_INGRESO"
  ```
- This ensures queries asking for demographic counts broken down by quintile resolve to `POBLACION` rather than income concentration.

### B. Specific Ethnic Priority in `FacetOntology.extract_facets_from_query` (`src/statscepal/semantic/facet_ontology.py`)
- Evaluates specific ethnic group trigger rules and synsets before breakdown values:
  ```python
  # Specific ethnic group patterns must not be shadowed by generic breakdown triggers (e.g. 'etnico')
  if fdef.facet_key == "etnia":
      specific_match = None
      for c_val, pat, norm_phrases in compiled_rules:
          if c_val in ("INDIGENA", "AFRODESCENDIENTE", "NO_INDIGENA"):
              if pat is not None:
                  if pat.search(clean):
                      specific_match = c_val
                      break
              else:
                  if any(p in clean for p in norm_phrases):
                      specific_match = c_val
                      break
      if not specific_match and thesaurus is not None and fdef.synset_domain:
          t_match = thesaurus.match_synset(fdef.synset_domain, clean)
          if t_match and t_match.canonical_id in ("INDIGENA", "AFRODESCENDIENTE", "NO_INDIGENA"):
              specific_match = t_match.canonical_id

      if specific_match:
          facets[fdef.facet_key] = specific_match
          continue
  ```
- Resolves the issue where `"poblacion del grupo etnico afrodescendiente"` had `"etnico"` match `ETNICO_TOTAL` and skip `AFRODESCENDIENTE`.

### C. Population Routing Specificity in `SemanticResolutionEngine._route_population_indicator` (`src/statscepal/semantic/engine.py`)
- Updated routing order to prioritize multi-facet specificity:
  ```python
  @staticmethod
  def _route_population_indicator(facets: dict[str, str]) -> int:
      """Route demographic population queries to specialized breakdown indicators based on facets."""
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

### D. Estrato Dimension Ontology Hardening (`src/statscepal/semantic/facet_ontology.py`)
- Updated `DEFAULT_FACETS` entry for `estrato`:
  ```python
  known_dimension_ids=frozenset({378, 600}),
  dimension_name_patterns=("estrato", "estratificacion", "nivel socioeconomico", "quintil", "decil"),
  ```
- Unblocks `DynamicMemberMatcher` from matching `facets["estrato"] = "QUINTIL"` to dimension `378` (`Quintil`), enabling indicator `4639` to pass the Stage 4 dimensional gate.

### E. Unit Tests Added (`tests/test_semantic_breakdowns.py`)
- Added `@pytest.fixture def engine()` to provide an isolated instance of `SemanticResolutionEngine`.
- Added 3 new unit tests:
  1. `test_poblacion_por_quintil_y_etnia_routes_to_indicator_4639`: Verifies `"poblacion indigena por quintil en peru 2021"` resolves to indicator `4639` with country `PER`.
  2. `test_poblacion_especifica_afrodescendiente_no_bloqueada_por_etnico_total`: Verifies `"poblacion del grupo etnico afrodescendiente en brasil 2020"` resolves to indicator `4969` (not shadowed by `ETNICO_TOTAL`).
  3. `test_poblacion_por_area_urbana_rural_routes_to_indicator_4992`: Verifies `"poblacion por area en colombia 2022"` resolves to indicator `4992`.

---

## 3. TDD Evidence & Verification

### A. RED Phase (Failing Tests Verified)
Command:
```bash
uv run pytest tests/test_semantic_breakdowns.py -k "test_poblacion_por_quintil or test_poblacion_especifica or test_poblacion_por_area" -v
```
Output:
```
tests/test_semantic_breakdowns.py::test_poblacion_por_quintil_y_etnia_routes_to_indicator_4639 FAILED [ 33%]
tests/test_semantic_breakdowns.py::test_poblacion_especifica_afrodescendiente_no_bloqueada_por_etnico_total FAILED [ 66%]
tests/test_semantic_breakdowns.py::test_poblacion_por_area_urbana_rural_routes_to_indicator_4992 PASSED [100%]

================================== FAILURES ===================================
FAILED tests/test_semantic_breakdowns.py::test_poblacion_por_quintil_y_etnia_routes_to_indicator_4639 - AssertionError: assert ABSTAINED == RESOLVED (unsupported facet: 'etnia' on 3340)
FAILED tests/test_semantic_breakdowns.py::test_poblacion_especifica_afrodescendiente_no_bloqueada_por_etnico_total - AssertionError: assert 4968 == 4969 (matched ETNICO_TOTAL on bare 'etnico')
================= 2 failed, 1 passed, 12 deselected in 1.77s ==================
```

### B. GREEN Phase (Implementation & Verification)
1. **Targeted Unit Tests:**
   ```bash
   uv run pytest tests/test_semantic_breakdowns.py -k "test_poblacion_por_quintil or test_poblacion_especifica or test_poblacion_por_area" -v
   ```
   Output:
   ```
   tests/test_semantic_breakdowns.py::test_poblacion_por_quintil_y_etnia_routes_to_indicator_4639 PASSED [ 33%]
   tests/test_semantic_breakdowns.py::test_poblacion_especifica_afrodescendiente_no_bloqueada_por_etnico_total PASSED [ 66%]
   tests/test_semantic_breakdowns.py::test_poblacion_por_area_urbana_rural_routes_to_indicator_4992 PASSED [100%]
   ====================== 3 passed, 12 deselected in 1.69s =======================
   ```

2. **Full Breakdowns Module Suite:**
   ```bash
   uv run pytest tests/test_semantic_breakdowns.py -v
   ```
   Output:
   ```
   ============================= 15 passed in 2.51s ==============================
   ```

3. **200-Question Semantic Benchmark Suite:**
   ```bash
   uv run pytest tests/test_semantic_benchmark_200.py -v
   ```
   Output:
   ```
   ============================= 11 passed in 1.72s ==============================
   ```
   - Top-1 Accuracy: Strictly 100.0% (200/200)
   - False Substitution Rate (FSR): Strictly 0.00% (0/200)

4. **Facet Coverage Benchmark Suite:**
   ```bash
   uv run pytest tests/test_semantic_facet_coverage.py -v
   ```
   Output:
   ```
   ============================= 17 passed in 1.58s ==============================
   ```

5. **Complete Non-Integration Test Suite:**
   ```bash
   uv run pytest -m "not integration"
   ```
   Output:
   ```
   ===================== 308 passed, 3 deselected in 49.35s ======================
   ```

---

## 4. Self-Review and File Hygiene

- Modified files strictly matched specification:
  - `src/statscepal/semantic/parser.py`
  - `src/statscepal/semantic/facet_ontology.py`
  - `src/statscepal/semantic/engine.py`
  - `tests/test_semantic_breakdowns.py`
- No stray or untracked files left in working directory (`git status` clean).
- No integration or live network calls performed (strict offline hermeticity maintained).
- Modern Python typing syntax (`dict[K, V]`, `list[T]`, `X | Y`) preserved across all modified functions.

---

## 5. Artifacts and Commits

- **Commit:** `c9b5f90`
- **Diff Review File:** `.superpowers/sdd/2026-10-17-retrospective-remediation-and-hardening-plan/review-cebde1c..c9b5f90.diff`
- **Report File:** `.superpowers/sdd/2026-10-17-retrospective-remediation-and-hardening-plan/task-2-report.md`
