---
epic: 2026-10-17
date: 2026-10-17
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# Retrospective: Semantic Engine Code Hardening & Catalog Alignment (2026-10-17)

## Epic summary

- **Epics Audited:**
  1. **Semantic Engine Code Hardening** ([`docs/superpowers/plans/2026-10-17-semantic-engine-code-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-semantic-engine-code-hardening-plan.md))
  2. **Catalog Alignment & Empirical Fetch Hardening** ([`docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md))
- **Diff Range:** `f5d8b4a..ffeb0c6` (12 non-merge commits, 0 merge commits)
- **Stories / Tasks Completed (8/8 Done in SDD Ledgers):**
  - **Hardening Task 1** (`77abc62`): Generic multi-member breakdowns for `sexo`, `area`, `edad`, and `deciles` in `FacetOntology` and `QueryParser`.
  - **Hardening Task 2** (`6927d25`): Implicit aggregate collapse for unconstrained DataFrame dimensions and latest-year cross-section filtering in `SemanticDataFetcher`.
  - **Hardening Task 3** (`7c2f146`): BADEHOG household survey temporal calendar propagation across 9 indicators and dynamic DataFrame anchor rescue.
  - **Hardening Task 4** (`df2d68e`): Dynamic `conversational_hint` synthesis for Stage 3 controlled ambiguities in `SemanticResolutionEngine`.
  - **Alignment Task 1** (`591da03`): Empirical indicator ID mapping (`EMPIRICAL_INDICATOR_ID_MAP`) and synthetic member ID isolation (`SYNTHETIC_DIMENSION_MEMBER_IDS`).
  - **Alignment Task 2** (`1b6c651`): Human-readable country column priority, UN formal country name prefix matching, and `'Década'` temporal column parsing.
  - **Alignment Task 3** (`e539d28`): Latin American demonyms in `COUNTRY_LEXICON`, `POBLACION` root concept, and demographic/ethnic indicators (`4788`, `4968`, `4969`, `4992`, `4639`).
  - **Alignment Task 4** (`2bd03e6`): CLI annotation of mapped CEPALSTAT API Table IDs and end-to-end certification of live diagnostic queries.
- **Unfinished Stories (`pending_stories`):**
  - Automated `sprint-status.yaml` completeness check did not run (`{"ok": false, "error": "[Errno 2] No such file or directory: '_bmad-output/implementation-artifacts/sprint-status.yaml'"}`). User explicitly confirmed proceeding without `sprint-status.yaml`. Both SDD ledgers ([`.superpowers/sdd/2026-10-17-semantic-engine-code-hardening-plan/progress.md`](file:///C:/papx/statscepal/.superpowers/sdd/2026-10-17-semantic-engine-code-hardening-plan/progress.md) and [`.superpowers/sdd/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan/progress.md`](file:///C:/papx/statscepal/.superpowers/sdd/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan/progress.md)) confirm 8/8 tasks completed (`[x]`).
- **Evidence Inventory:**
  - **Available:** Master implementation plans (`docs/superpowers/plans/2026-10-17-*.md`), SDD task briefs and implementer reports (`.superpowers/sdd/2026-10-17-*/task-*-brief.md`, `task-*-report.md`), full git commit history and `git_evidence.py` metrics (`f5d8b4a..ffeb0c6`), previous retrospective ([`docs/reports/2026-10-16-epic-generic-facet-routing-retrospective.md`](file:///C:/papx/statscepal/docs/reports/2026-10-16-epic-generic-facet-routing-retrospective.md)), and conversation transcript logs.
  - **Missing:** `_bmad-output/implementation-artifacts/sprint-status.yaml` (not used in SDD workflow; tracked via `.superpowers/sdd/*/progress.md`).

### Per-File Churn Inventory (`git_evidence.py` over `f5d8b4a..ffeb0c6`)

| File Path | Added | Deleted | Net | Commits |
|---|---:|---:|---:|---:|
| [`src/statscepal/semantic/fetcher.py`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py) | 376 | 74 | +302 | 4 |
| [`tests/test_semantic_fetcher.py`](file:///C:/papx/statscepal/tests/test_semantic_fetcher.py) | 253 | 0 | +253 | 4 |
| [`src/statscepal/semantic/registry.py`](file:///C:/papx/statscepal/src/statscepal/semantic/registry.py) | 235 | 16 | +219 | 3 |
| [`src/statscepal/semantic/parser.py`](file:///C:/papx/statscepal/src/statscepal/semantic/parser.py) | 110 | 11 | +99 | 2 |
| [`tests/test_semantic_breakdowns.py`](file:///C:/papx/statscepal/tests/test_semantic_breakdowns.py) | 96 | 0 | +96 | 2 |
| [`src/statscepal/semantic/facet_ontology.py`](file:///C:/papx/statscepal/src/statscepal/semantic/facet_ontology.py) | 64 | 5 | +59 | 2 |
| [`tests/test_semantic_multi_year.py`](file:///C:/papx/statscepal/tests/test_semantic_multi_year.py) | 50 | 0 | +50 | 1 |
| [`src/statscepal/semantic/engine.py`](file:///C:/papx/statscepal/src/statscepal/semantic/engine.py) | 28 | 1 | +27 | 2 |
| [`tests/test_semantic_generic_gate.py`](file:///C:/papx/statscepal/tests/test_semantic_generic_gate.py) | 26 | 0 | +26 | 1 |
| [`src/statscepal/cli.py`](file:///C:/papx/statscepal/src/statscepal/cli.py) | 6 | 0 | +6 | 1 |
| [`.agents/rules/semantic-resolution-guardrails.md`](file:///C:/papx/statscepal/.agents/rules/semantic-resolution-guardrails.md) | 40 | 0 | +40 | 1 |
| [`docs/reports/resumen_avances_motor_semantico.md`](file:///C:/papx/statscepal/docs/reports/resumen_avances_motor_semantico.md) | 119 | 75 | +44 | 1 |
| [`docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md) | 656 | 0 | +656 | 1 |
| [`docs/superpowers/plans/2026-10-17-semantic-engine-code-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-semantic-engine-code-hardening-plan.md) | 650 | 0 | +650 | 1 |

---

## Findings

### Aggregate Views

1. **Architecture Delta (`src/statscepal/semantic/fetcher.py:11-14, 137-198, 524-590`)**:
   - **Evidence:** Commit `591da03` introduced a direct import from `statscepal.semantic.registry` (`EMPIRICAL_INDICATOR_ID_MAP`, `SYNTHETIC_DIMENSION_MEMBER_IDS`) into `fetcher.py`. Indicator routing is now split between Stage 3/4 (`engine.py`) and Stage 6 (`fetcher._resolve_empirical_indicator_id` at `fetcher.py:185-198`, which inspects `response.applied_filters.facets.get("estrato", "")` to route `3340` between `3295`, `3324`, and `3390`). In addition, `fetcher.py` maintains its own `_STRUCTURAL_AND_META_COLS` (`L55-L89`) and `_AGGREGATE_MEMBER_PRIORITY` (`L91-L106`) rather than delegating to `FacetOntology.is_structural_dimension` (`facet_ontology.py:159-189`) and `FacetOntology.is_aggregate_member_name` (`facet_ontology.py:148-157`).
   - **Disposition:** *Defer* (Consolidate ontology/structural delegation in a follow-up refactoring story).
   - **Prevention:** Require Stage 6 (`fetcher.py`) to consume `FacetOntology` helpers directly rather than defining parallel constant tables.

2. **Duplication Map (`fetcher.py`, `parser.py`, `facet_ontology.py`, `thesaurus.py`)**:
   - **Evidence:**
     - `strip_accents` / `_strip_accents` is implemented in 4 separate files: [`facet_ontology.py:16-21`](file:///C:/papx/statscepal/src/statscepal/semantic/facet_ontology.py#L16-L21), [`parser.py:19-24`](file:///C:/papx/statscepal/src/statscepal/semantic/parser.py#L19-L24), [`thesaurus.py:10-15`](file:///C:/papx/statscepal/src/statscepal/semantic/thesaurus.py#L10-L15), and [`fetcher.py:17-20`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L17-L20).
     - UN parenthetical country prefix matching (`c_norm == norm_t_name or c_norm.startswith(norm_t_name + " (")`) is duplicated 3 times inside `SemanticDataFetcher.fetch_resolved_data` ([`fetcher.py:320-337`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L320-L337), [`fetcher.py:340-365`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L340-L365), and [`fetcher.py:397-428`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L397-L428)).
     - Scalar year fallback extraction is duplicated twice in `fetch_resolved_data` ([`fetcher.py:714-725`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L714-L725) and [`fetcher.py:839-850`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L839-L850)).
   - **Disposition:** *Defer* (Action Item #7).
   - **Prevention:** Extract shared normalization utilities (`strip_accents`, country matching, year extraction) before adding multi-branch callers.

3. **God-Class / Method Size Growth (`fetcher.py:200-901`, `parser.py:235-811`, `engine.py:59-679`)**:
   - **Evidence:** Across the 8 tasks, [`SemanticDataFetcher.fetch_resolved_data`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L200-L901) grew by `+302` net lines to **702 lines** (mixing 9 distinct responsibilities in one method). [`QueryParser.parse`](file:///C:/papx/statscepal/src/statscepal/semantic/parser.py#L235-L811) is **577 lines** and [`SemanticResolutionEngine.resolve`](file:///C:/papx/statscepal/src/statscepal/semantic/engine.py#L59-L679) is **621 lines**.
   - **Disposition:** *Defer* (Action Item #7: Decompose `fetch_resolved_data` into stage helper methods).
   - **Prevention:** Enforce a maximum method length threshold (150 lines) during SDD code reviews.

4. **Pattern Divergence (`engine.py:42-53, 188-189`)**:
   - **Evidence:** Commit `e539d28` added [`SemanticResolutionEngine._route_population_indicator`](file:///C:/papx/statscepal/src/statscepal/semantic/engine.py#L42-L53) and invoked it in Stage 3 (`engine.py:188-189`). While this preserved the Stage 4 AST generic gate test (`test_engine_stage4_has_zero_hardcoded_facet_or_indicator_literals`), it bypasses Stage 4 `BREAKDOWN_OF` graph traversal for `POBLACION` (leaving `swapped_from=None` on `4968`, `4969`, `4992`, `4639`) and routes implicit `"area": "NACIONAL"` to `4992` because `if "area" in facets:` does not check `self.ontology.is_critical_unhandled_facet("area", facets["area"])`.
   - **Disposition:** *Fix now* (Action Item #3).
   - **Prevention:** Route breakdown swaps through Stage 4's generic `BREAKDOWN_OF` traversal or check `is_critical_unhandled_facet` before switching away from the canonical default `4788`.

5. **Spec-to-Implementation Reconciliation**:
   - **Evidence:** All 8 tasks across both 2026-10-17 plans were implemented. Where Plan 2 referenced conceptual symbols (`MemberMatchRule` in `facet_ontology.py` and `CONCEPT_TO_INDICATORS` in `engine.py`), commit `e539d28` adapted them to the actual codebase structures (`FacetDefinition.member_value_patterns` at [`facet_ontology.py:455-464`](file:///C:/papx/statscepal/src/statscepal/semantic/facet_ontology.py#L455-L464) and `OFFICIAL_25_CANONICAL_DEFAULTS["POBLACION"] = 4788` at [`registry.py:888`](file:///C:/papx/statscepal/src/statscepal/semantic/registry.py#L888)).
   - **Disposition:** *Accept as-is* (Recorded so future runs do not re-flag the symbol adaptation).
   - **Prevention:** Verify exact class and dictionary symbol names in source files before writing code snippets into implementation plans.

---

### Code Review Lenses (`Adversarial`, `Edge-Case Hunter`, `Verification Gap`) & Runtime Behavior Check

1. **[F1 — Adversarial + Edge-Case + Verification-Gap] Synthetic Member IDs `43040..43043` in `DEFAULT_OFFICIAL_DIMENSIONS[3342]` Collide with Real CEPALSTAT Member IDs (`src/statscepal/semantic/registry.py:63-71, 258-281`, `src/statscepal/semantic/fetcher.py:235-238`)**:
   - **Evidence:** `DEFAULT_OFFICIAL_DIMENSIONS[3342]` defines `dim_id=43039` (`"Tipo de etnia"`) with sequential placeholder IDs `43040="Afrodescendiente"`, `43041="Indígena"`, `43042="No indígena ni afrodescendiente"`, `43043="Total"`. In commit `e539d28`, `DEFAULT_OFFICIAL_DIMENSIONS[4639]` (`registry.py:258-266`) registered the real CEPALSTAT member IDs for the same `dim_id=43039`: `77477="Indígena"`, `43044="Afrodescendiente"`, `43043="No indígena ni afrodescendiente"`, `43040="Total"`. Because `43040..43043` are not in `SYNTHETIC_DIMENSION_MEMBER_IDS`, a live fetch on `3342` for `"Afrodescendiente"` sends `members=[43040]` (which is `"Total"` in the real API), and Step 2 filters for `"Afrodescendiente"`, resulting in an empty DataFrame.
   - **Disposition:** *Fix now* (Action Item #1).
   - **Prevention:** Add a cross-indicator dimension consistency test verifying that shared `dim_id` definitions in `DEFAULT_OFFICIAL_DIMENSIONS` never assign conflicting member IDs.

2. **[F2 — Adversarial + Edge-Case + Verification-Gap] Accent-Insensitive Matching Omitted in `SemanticDataFetcher` Step 5 `breakdown_cols` (`src/statscepal/semantic/fetcher.py:690-701`)**:
   - **Evidence:** Step 2 (`fetcher.py:438-445`) matches dimension columns using `_strip_accents(cl).replace("__estandar", "") == _strip_accents(dl).replace("__estandar", "")`, but Step 5 (`fetcher.py:697`) checks `cl == dl or cl.replace("__estandar", "") == dl.replace("__estandar", "")` without `_strip_accents`. When `dim_name` in `DEFAULT_OFFICIAL_DIMENSIONS[4968, 4969, 4992]` (`"Area Geografica"`) is matched against a DataFrame column with diacritics (`"Área geográfica"`), Step 5 fails to populate `breakdown_cols`, omitting `"member"` labels from `series`.
   - **Disposition:** *Fix now* (Action Item #2).
   - **Prevention:** Unify Step 2 and Step 5 column matching into a single accent-insensitive helper method.

3. **[F3 — Adversarial + Edge-Case + Verification-Gap] Cross-Story Precedence Collision Leaves Indicator `4639` Unreachable and Untested (`src/statscepal/semantic/parser.py:736-751, 807-808`, `src/statscepal/semantic/engine.py:43-53`, `src/statscepal/semantic/facet_ontology.py:276-290, 484-486`)**:
   - **Evidence:**
     - In `QueryParser.parse`, `DISTRIBUCION_INGRESO` (`parser.py:736-751`, matching `"quintil"`, `"quintiles"`, `"decil"`, `"deciles"`) executes before `POBLACION` (`parser.py:807-808`), so `"poblacion indigena por quintil"` resolves to `DISTRIBUCION_INGRESO` (`3340`) and abstains on `UNSUPPORTED_FACET="etnia"`.
     - In `engine._route_population_indicator` (`engine.py:45-48`), `facets.get("etnia") == "AFRODESCENDIENTE"` (`-> 4969`) is evaluated before `("estrato" in facets or "quintil" in facets) and "etnia" in facets` (`-> 4639`).
     - In `FacetOntology.extract_facets_from_query` (`facet_ontology.py:276-290`), `breakdown_values` triggers run first; because `ETNICO_TOTAL` includes bare `"etnia"`/`"etnico"`, queries like `"poblacion del grupo etnico afrodescendiente"` lock in `ETNICO_TOTAL` and skip `"AFRODESCENDIENTE"`.
     - Neither `4639` nor `4992` has unit tests in `tests/`.
   - **Disposition:** *Fix now* (Action Item #3).
   - **Prevention:** Require at least one end-to-end resolution test per newly registered indicator ID in every SDD task brief.

4. **[F4 — Runtime Behavior Check + Adversarial] 10 Indicators in `VERTICAL_SLICE_INDICATORS` Declare `supported_facets` Without Entries in `DEFAULT_OFFICIAL_DIMENSIONS` (`src/statscepal/semantic/registry.py:42-268, 312-884`, `src/statscepal/semantic/engine.py:291-305, 364-370`)**:
   - **Evidence:** Exercising `engine.resolve("tasa de desocupacion por sexo en chile 2022")` at runtime returned `indicator_id=127` with `facets={'sexo': 'SEXO_DESGLOSE'}` and `applied_filters.dimensions=[]`. Indicators `127`, `3331`, `3337`, `5097`, `119`, `340`, `365`, `1684`, `3344`, and `3333` declare `supported_facets` in `VERTICAL_SLICE_INDICATORS` (so Stage 4 sees the facet as supported and does not swap), but have no dimensions in `DEFAULT_OFFICIAL_DIMENSIONS` (or SQLite `indicator_dimensions`), leaving `applied_filters.dimensions=[]` and causing `SemanticDataFetcher._filter_unconstrained_dimensions` to collapse `Sexo__ESTANDAR` to `"Ambos sexos"`.
   - **Disposition:** *Fix now* (Action Item #4).
   - **Prevention:** Add a registry invariant test asserting that every indicator in `VERTICAL_SLICE_INDICATORS` with non-empty `supported_facets` has corresponding dimension definitions in `DEFAULT_OFFICIAL_DIMENSIONS` (and guard `_filter_unconstrained_dimensions` against collapsing dimensions requested as breakdowns in `response.applied_filters.facets`).

5. **[F5 — Adversarial + Edge-Case + Verification-Gap] Dimension/Member Schema Mismatch and Missing Tests on Dynamic Mapping `3340 -> 3295 / 3324 / 3390` (`src/statscepal/semantic/fetcher.py:185-198, 431-484`, `src/statscepal/semantic/registry.py:140-160`)**:
   - **Evidence:** Stage 4 binds `3340` to `DEFAULT_OFFICIAL_DIMENSIONS[3340]` (`dim_name="Estrato de ingreso"`, members `"Primer quintil"`, `"Quinto quintil"`, `"Primer decil"`, `"Décimo decil"`). When `_resolve_empirical_indicator_id` remaps `3340` to `3324` (`"Quintil"`, `"Quintil 1".."Quintil 5"`) or `3390` (`"Decil"`, `"Decil 1".."Decil 10"`), the column and member names differ, and `tests/` has 0 tests exercising `3295`, `3324`, or `3390`.
   - **Disposition:** *Fix now* (Action Item #5).
   - **Prevention:** Require empirical indicator mapping tests to validate DataFrame column and member filtering against the target table's schema.

6. **[F6 — Adversarial + Edge-Case] CLI Omits `conversational_hint` on `ALTERNATIVE_PROPOSED`, Multi-Year Partial Anchor Rescue Skipped, and Multi-Country Top-Level Payload Misattribution (`src/statscepal/cli.py:639-650`, `src/statscepal/semantic/fetcher.py:568-590, 787-802`)**:
   - **Evidence:**
     - `cli.py:639-650` only prints `res.conversational_hint` inside the `else:` branch when `res.selected_candidate` is `None`, hiding the dynamic hints created for `ALTERNATIVE_PROPOSED` in commit `df2d68e`.
     - `fetcher.py:569` checks `if not observed_requested and avail_years:`, skipping dynamic anchor rescue when a multi-year query has at least one observed year, and does not update `response.status` to `RESOLVED_WITH_ANCHORS`.
     - `fetcher.py:787-802` pairs `latest_item = series[-1]` (last country's value) with `response.applied_filters.country_name` (first country's name).
   - **Disposition:** *Fix now* (Action Item #6).
   - **Prevention:** Include CLI output assertions for `ALTERNATIVE_PROPOSED` hints and multi-country top-level payload fields in unit tests.

7. **[F8 — Verification Gap & Adversarial] Identical Max Years in Multi-Country Latest-Year Test & Unreachable `"ñ"` Keys in `COUNTRY_LEXICON` (`tests/test_semantic_fetcher.py:273-301`, `src/statscepal/semantic/parser.py:58-59, 101-104, 113-116, 125-128, 236`)**:
   - **Evidence:** `test_fetcher_multi_country_without_year_filters_to_latest_year_per_country` uses `2022` as the max year for both Perú and Chile, which cannot distinguish per-country `groupby` from global `max()`. In `parser.py`, `clean = strip_accents(query)` strips `"ñ"` to `"n"` before scanning `COUNTRY_LEXICON`, making the 14 accented `"ñ"` keys dead entries.
   - **Disposition:** *Defer* (Action Item #8).
   - **Prevention:** Construct multi-group test fixtures with distinct group extrema (`2021` vs `2022`).

---

## Behavior verification

Runtime flows were executed directly via `uv run statscepal semantic resolve ... --explain` and `uv run python -c ...`:

1. **Live User Query 1 (Multi-country food inflation 2018–2023):**
   - Command: `uv run statscepal semantic resolve "necesito los datos de la inflacion de alimentos de mexico, peru, argentina, chile, colombia y paraguay del año 2018 al 2023" --explain`
   - Observed: Resolved to `ID 2929` (`score 1.0`), extracted all 6 countries (`MEX, PER, ARG, CHL, COL, PRY`) and range `2018-2023`, and stripped synthetic member `79578` at fetch time.
2. **Live User Query 2 (Multi-country headline inflation 2018–2023):**
   - Command: `uv run statscepal semantic resolve "necesito los datos de la inflacion de peru, argentina, chile, colombia y paraguay del año 2018 al 2023" --explain`
   - Observed: Resolved to `ID 2928` (`score 1.0`), mapped dynamically via `_resolve_empirical_indicator_id` to `2484` (*Tasa de crecimiento anual del IPC: diciembre a diciembre*).
3. **Live User Query 3 (Ethnic population with demonym `'peruana'`):**
   - Command: `uv run statscepal semantic resolve "necesito datos etnicos de la poblacion peruana" --explain`
   - Observed: Resolved to `ID 4968` (`score 1.0`), extracted `Perú (PER)` from `"peruana"`, bound dimension `Condición Indígena (ID: 78149)` with breakdown `[Indígena (ID: 78150), No Indígena (ID: 78152)]`.
4. **BADEHOG Multi-Country Temporal Audit & Ambiguity Hints:**
   - Query `"indice de gini en peru, colombia y chile en 2021"` resolved to `3289` (`RESOLVED_WITH_ANCHORS`), isolating `CHL` as unobserved in `[2021]` with official anchors `2020` and `2022` while preserving `PER` and `COL`.
   - Query `"cuentas fiscales de chile 2022"` returned `ALTERNATIVE_PROPOSED` with dynamic `conversational_hint` naming primary `ID 1240` and alternatives `ID 1241, ID 1242`.
5. **Generic Breakdown Edge Case Discovered at Runtime:**
   - Query `"pobreza por sexo en chile 2022"` swapped `3328 -> 3341` and bound `Sexo__ESTANDAR` with `is_breakdown=True` (`['Hombres', 'Mujeres']`).
   - Query `"tasa de desocupacion por sexo en chile 2022"` resolved to `127` with `facets={'sexo': 'SEXO_DESGLOSE'}` but `applied_filters.dimensions=[]` because `127` is not seeded in `DEFAULT_OFFICIAL_DIMENSIONS` (recorded as Finding F4 / Action Item #4).

---

## Previous-retro follow-through

- **Prior Retrospective Checked:** [`docs/reports/2026-10-16-epic-generic-facet-routing-retrospective.md`](file:///C:/papx/statscepal/docs/reports/2026-10-16-epic-generic-facet-routing-retrospective.md) (Epic E1–E5).
- **`sprint-status.yaml` Status:** `_bmad-output/implementation-artifacts/sprint-status.yaml` does not exist in this repository (`[Errno 2] No such file or directory`), so there were no machine-tracked `action_items` selectors to transition via `--set-action-status`.
- **Guardrail Follow-Through Evidence:** The architectural guardrails established after Epic E1–E5 in [`.agents/rules/semantic-resolution-guardrails.md`](file:///C:/papx/statscepal/.agents/rules/semantic-resolution-guardrails.md) were maintained (303/303 non-integration tests passing, 100.0% Top-1 Accuracy, 0.00% FSR, `test_semantic_generic_gate.py` 5/5 passing) and expanded in commit `ffeb0c6` with Sections 5–11.

---

## Action items

| ID | Type | Action | Owner | Source Finding |
|---|---|---|---|---|
| **AI-1** | Remediation (Fix Now) | Align `DEFAULT_OFFICIAL_DIMENSIONS[3342]` member IDs on `dim_id=43039` with real CEPALSTAT member IDs (`77477`, `43044`, `43043`, `43040`) or add `43040..43043` to `SYNTHETIC_DIMENSION_MEMBER_IDS`, and add a fetch unit test for `3342`. | Amelia (Dev) | F1 (`registry.py:63-71, 258-281`) |
| **AI-2** | Remediation (Fix Now) | Add `_strip_accents` normalization to Step 5 `breakdown_cols` matching in `SemanticDataFetcher.fetch_resolved_data` (`src/statscepal/semantic/fetcher.py:697`) and unify column lookup with Step 2. | Amelia (Dev) | F2 (`fetcher.py:690-701`) |
| **AI-3** | Remediation (Fix Now) | Fix `POBLACION` vs `DISTRIBUCION_INGRESO` precedence in `QueryParser.parse` (`parser.py:736-808`), check `4639` before `4969` and check `is_critical_unhandled_facet` in `_route_population_indicator` (`engine.py:43-53`), refine `ETNICO_TOTAL` trigger precedence (`facet_ontology.py:276-290, 484`), and add tests for `4639` and `4992`. | Amelia (Dev) | F3 (`parser.py:736-808`, `engine.py:43-53`) |
| **AI-4** | Remediation (Fix Now) | Seed `DEFAULT_OFFICIAL_DIMENSIONS` for the 10 `VERTICAL_SLICE_INDICATORS` that declare `supported_facets` (`127`, `3331`, `3337`, `5097`, `119`, `340`, `365`, `1684`, `3344`, `3333`) and prevent `_filter_unconstrained_dimensions` from collapsing dimensions requested as breakdowns in `response.applied_filters.facets`. | Amelia (Dev) | F4 (`registry.py:42-268`, `fetcher.py:137-182`) |
| **AI-5** | Remediation (Fix Now) | Support dimension/member alias matching when `_resolve_empirical_indicator_id` remaps `3340 -> 3295 / 3324 / 3390` (`"Estrato de ingreso"` -> `"Quintil"` / `"Decil"`) and add unit tests for `3295`, `3324`, and `3390` in `tests/test_semantic_fetcher.py`. | Amelia (Dev) | F5 (`fetcher.py:185-198, 431-484`) |
| **AI-6** | Remediation (Fix Now) | Print `res.conversational_hint` for `ALTERNATIVE_PROPOSED` in `src/statscepal/cli.py:639-650`, rescue dynamic anchors per missing year in multi-year queries while promoting status to `RESOLVED_WITH_ANCHORS` (`fetcher.py:568-590`), and use `latest_item.get("country")` in top-level `payload["country"]` (`fetcher.py:787-802`). | Amelia (Dev) | F6 (`cli.py:639-650`, `fetcher.py:568-802`) |
| **AI-7** | Refactoring (Deferred) | Decompose `SemanticDataFetcher.fetch_resolved_data` (702 lines) into cohesive stage helper methods and centralize `strip_accents`, structural column detection, and aggregate member priority in `facet_ontology.py`. | Winston / Amelia | Aggregate Views 1, 2, 3 (`fetcher.py:200-901`) |
| **AI-8** | Test & Lexicon Hygiene (Deferred) | Use distinct per-country max years (`2021` vs `2022`) in `test_fetcher_multi_country_without_year_filters_to_latest_year_per_country` (`tests/test_semantic_fetcher.py:273-301`) and remove dead accented `"ñ"` keys from `COUNTRY_LEXICON` (`parser.py:58-128`). | Amelia (Dev) | F8 (`tests/test_semantic_fetcher.py:273-301`) |

---

## Acceptance verdict

- **Verdict:** **`accepted-with-open-items`**
- **Criteria Source:** **`declared`** (Defined in [`docs/superpowers/plans/2026-10-17-semantic-engine-code-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-semantic-engine-code-hardening-plan.md) and [`docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md`](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md)).
- **Evidence Behind the Verdict:**
  1. All 8 planned tasks across both epics were completed and verified (`f5d8b4a..ffeb0c6`).
  2. All 303 non-integration unit and benchmark tests pass (`0 failed`), preserving **100.0% Top-1 Accuracy** and **0.00% False Substitution Rate** on both the 200-question benchmark and the 70-case 13-facet coverage matrix, with $p50 < 0.3\text{ ms}$ in-memory resolution latency.
  3. All 3 motivating live user queries resolve and fetch accurately end-to-end.
  4. Six concrete cross-story boundary remediations (**AI-1 through AI-6**) and two structural refactoring/hygiene items (**AI-7, AI-8**) were surfaced by the multi-lens retrospective audit and are tracked above for human-approved execution.

---

## Open questions

1. **Execution of Fix-Now Action Items (AI-1 to AI-6):** Would you like to execute a focused remediation sprint right now to close **AI-1 through AI-6** (fixing the `3342` member ID collision, `breakdown_cols` accent stripping, `4639` population-by-quintile reachability, `DEFAULT_OFFICIAL_DIMENSIONS` seeding for the 10 vertical-slice indicators, `3340` empirical column matching, and CLI `conversational_hint` display)?
2. **`SemanticDataFetcher` Decomposition (AI-7):** Should the decomposition of `SemanticDataFetcher.fetch_resolved_data` (702 lines) be bundled with the remediation pass or scheduled as a separate refactoring story?
