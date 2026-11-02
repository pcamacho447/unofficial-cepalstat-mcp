# Declarative Concept Ontology Implementation Plan (Phase 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the procedural 580-line `if/elif` concept matching cascade in `QueryParser` into a declarative, data-driven `ConceptOntology` engine (`src/unofficial_cepalstat_mcp/semantic/concept_ontology.py`), eliminating code duplication, unifying concept triggers and ambiguity routing, and preserving 100% benchmark accuracy with 0.00% FSR.

**Architecture:**
1. **Declarative Models (`concept_ontology.py`):** Define `ConceptDefinition`, `ConceptTriggerRule`, `SubConceptRule`, and `ConceptMatchResult` using frozen Pydantic models.
2. **Precompiled Matching Engine (`ConceptOntology`):** Index and precompile regular expressions and phrase lists ordered by descending length and priority (e.g. `DEUDA_PUBLICA` [150] evaluated before `PIB` [100] to correctly handle "... % del PIB"). Support sub-concept resolution and controlled ambiguity tagging.
3. **Delegation in `QueryParser` (`parser.py`):** Inject `concept_ontology` into `QueryParser`, replacing lines 780–1360 with a single high-performance call to `self.concept_ontology.extract_concept()`.

**Tech Stack:** Python 3.10+, Pydantic v2, Pytest, Regex.

**Spec:** [`docs/superpowers/specs/2026-11-02-declarative-concept-ontology-spec.md`](file:///home/jorge/projects/unofficial-cepalstat-mcp/docs/superpowers/specs/2026-11-02-declarative-concept-ontology-spec.md)

---

## Global Constraints

- Preserve 0.00% False Substitution Rate (FSR) across all 390 certified benchmark queries.
- Preserve 100% mutation divergence across all 8 tests in `tests/test_semantic_mutations.py`.
- Preserve local latency budget strictly at $p50 < 0.5\text{ ms}$ and $p95 < 2.0\text{ ms}$.
- Zero static typing errors under `uv run mypy src/unofficial_cepalstat_mcp/`.
- Clean linting under `uv run ruff check .`.
- Run tests only with `uv run pytest -m "not integration"`.

---

## Review Focus

1. **Macro vs Fiscal Priority ("... % del PIB"):** Queries like `"deuda publica como % del PIB"` or `"balance primario % PIB"` must resolve to `DEUDA_PUBLICA` or `BALANCE_PRIMARIO`, never shadowed by `PIB`.
2. **Sub-Concept Modifiers:** `"ingresos tributarios en moneda nacional"` must resolve to `INGRESOS_TRIBUTARIOS_CORRIENTES` (845), while `"ingresos tributarios"` resolves to `INGRESOS_TRIBUTARIOS` (821); `"emisiones sin lulucf"` must resolve to `EMISIONES_GEI_SIN_LULUCF` (5682).
3. **Ambiguity Preservation:** Vague queries (e.g. `"actividad economica en chile"`, `"situacion laboral"`, `"precios en colombia"`) must preserve `is_ambiguous_measure = True` and their exact `ambiguous_candidate` tags.
4. **Demographic Breakdown & Gender Invariants:** `"poblacion indígena"` and `"brecha salarial"` must correctly preserve their facets and not strip necessary comparisons.
5. **Cold-Start & Resolution Latency:** The ontology must compile regexes once at module initialization or instantiation without re-compiling per query.

---

## Task Structure

### Task 1: Declarative Concept Models & Ontology Engine (`concept_ontology.py`)

**Files:**
- Create: `src/unofficial_cepalstat_mcp/semantic/concept_ontology.py`
- Create: `tests/test_concept_ontology.py`

**Interfaces:**
- Produces:
  - `ConceptTriggerRule(patterns: tuple[str, ...], is_regex: bool = False, exact_word_boundary: bool = True, ambiguous_candidate: str | None = None, requires_subterms: tuple[str, ...] = (), excludes_subterms: tuple[str, ...] = ())`
  - `SubConceptRule(sub_concept_key: str, triggers: tuple[str, ...], is_ambiguous: bool = False, ambiguous_candidate: str | None = None, facet_updates: dict[str, str] = Field(default_factory=dict))`
  - `ConceptDefinition(concept_key: str, description: str, domain: str, priority: int = 100, default_indicator_id: int | None = None, default_facets: dict[str, str] = Field(default_factory=dict), triggers: tuple[ConceptTriggerRule, ...] = (), sub_concept_rules: tuple[SubConceptRule, ...] = (), controlled_ambiguities: dict[str, str] = Field(default_factory=dict))`
  - `ConceptMatchResult(concept_key: str, matched_phrase: str, consumed_phrases: list[str], is_ambiguous_measure: bool = False, ambiguous_candidate: str | None = None, suggested_facets: dict[str, str] = Field(default_factory=dict))`
  - `ConceptOntology(definitions: Sequence[ConceptDefinition] | None = None)`
  - `DEFAULT_CONCEPT_DEFINITIONS: list[ConceptDefinition]`
  - `DEFAULT_CONCEPT_ONTOLOGY: ConceptOntology`

- [ ] **Step 1: Write comprehensive unit tests for `ConceptOntology`**

Create `tests/test_concept_ontology.py`:
- Test all major concepts: `PIB`, `POBREZA`, `EMPLEO`, `GINI`, `SALARIO_REAL`, `IPC_GENERAL`, `DEUDA_PUBLICA`, `BALANCE_PRIMARIO`, `INGRESOS_TRIBUTARIOS`, `GASTO_SOCIAL`, `GASTO_EDUCACION`, `BALANZA_COMERCIAL`, `CUENTA_CORRIENTE`, `INVERSION_EXTRANJERA_DIRECTA`, `TERMINOS_INTERCAMBIO`, `EMISIONES_GEI_LULUCF`, `EMISIONES_GEI_SIN_LULUCF`, `ENERGIA_RENOVABLE`, `AGUA_DULCE`, `POBLACION`.
- Test priority ordering: `"deuda como % del pib"` -> `DEUDA_PUBLICA` (not `PIB`).
- Test sub-concept resolution: `"ingresos tributarios en moneda nacional"` -> `INGRESOS_TRIBUTARIOS_CORRIENTES`.
- Test controlled ambiguities: `"actividad economica en ecuador"` -> `PIB` with `ECONOMIC_ACTIVITY`.
- Test regionalisms: `"pbi del peru"` -> `PIB`.
- Test latency: 1,000 extractions executed in < 15 ms (average < 0.015 ms per query).

- [ ] **Step 2: Run tests to verify red phase failure**

Run: `uv run pytest tests/test_concept_ontology.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'unofficial_cepalstat_mcp.semantic.concept_ontology'`).

- [ ] **Step 3: Implement `concept_ontology.py`**

In `src/unofficial_cepalstat_mcp/semantic/concept_ontology.py`:
- Implement models: `ConceptTriggerRule`, `SubConceptRule`, `ConceptDefinition`, `ConceptMatchResult`.
- Build `DEFAULT_CONCEPT_DEFINITIONS` mapping all 22+ concepts with the exact priorities, phrases, ambiguities, and sub-concept rules currently spread across `parser.py`.
- Implement `ConceptOntology`:
  - In `__init__`, precompile regexes for each trigger rule and sort rules by descending priority, then descending pattern length.
  - Implement `extract_concept(clean_query: str, thesaurus: Thesaurus | None = None, facets: dict[str, str] | None = None) -> ConceptMatchResult | None`.
- Expose `DEFAULT_CONCEPT_ONTOLOGY`.

- [ ] **Step 4: Run tests to verify green phase passing**

Run: `uv run pytest tests/test_concept_ontology.py -v`
Expected: PASS (all tests pass, latency benchmark < 0.05 ms).

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/concept_ontology.py tests/test_concept_ontology.py
git commit -m "feat(semantic): implement declarative ConceptOntology engine with precompiled priority triggers"
```

---

### Task 2: Refactor `QueryParser` to Delegate to `ConceptOntology` (`parser.py`)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/parser.py:354-1360`
- Test: All existing parser and semantic test suites

**Interfaces:**
- Consumes: `ConceptOntology`, `DEFAULT_CONCEPT_ONTOLOGY`, `ConceptMatchResult`
- Produces:
  - `QueryParser(catalog_profile, thesaurus, ontology, concept_ontology: ConceptOntology | None = None)`
  - Replaces ~580 lines of procedural `if/elif` in `QueryParser.parse()` with declarative extraction.

- [ ] **Step 1: Run existing parser tests to ensure baseline passes**

Run: `uv run pytest tests/test_parser*.py -v`
Expected: PASS.

- [ ] **Step 2: Refactor `QueryParser` to use `ConceptOntology`**

In `src/unofficial_cepalstat_mcp/semantic/parser.py`:
1. Import `ConceptOntology` and `DEFAULT_CONCEPT_ONTOLOGY` from `.concept_ontology`.
2. Add `concept_ontology: ConceptOntology | None = None` to `QueryParser.__init__`, storing `self.concept_ontology = concept_ontology or DEFAULT_CONCEPT_ONTOLOGY`.
3. In `QueryParser.parse(query)`:
   - Call `self.concept_ontology.extract_concept(clean, thesaurus=self.thesaurus, facets=facets)`.
   - If a match is found:
     - Set `intent.root_concept = match.concept_key`.
     - Set `intent.is_ambiguous_measure = match.is_ambiguous_measure`.
     - Set `intent.ambiguous_candidate = match.ambiguous_candidate`.
     - Extend `consumed_phrases` with `match.consumed_phrases`.
     - Apply any `match.suggested_facets` to `facets` (respecting existing facet priority).
   - Remove redundant lines 784–1325 procedural `if/elif` ladder.
   - Retain downstream post-processing (gender breakdown invariant, gasto social/educación facet harmonization, currency area defaults, token deconstruction).

- [ ] **Step 3: Run all parser and semantic tests to verify parity**

Run: `uv run pytest tests/test_parser*.py tests/test_semantic_*.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/parser.py
git commit -m "refactor(semantic): replace procedural concept if/elif cascade in QueryParser with ConceptOntology"
```

---

### Task 3: Full Certification Gate, Mutation Divergence & Documentation Sync

**Files:**
- Modify: `AGENTS.md`
- Modify: `.agents/rules/semantic-resolution-guardrails.md`
- Run: Full test suite, benchmarks, linters, and package build.

- [ ] **Step 1: Execute all certified benchmarks & mutation suites**

Run:
```bash
uv run pytest tests/test_semantic_benchmark_200.py tests/test_adversarial_benchmark_40.py tests/test_catalog_scale_benchmark_100.py tests/test_independent_holdout_benchmark_50.py tests/test_semantic_mutations.py -v
```
Expected:
- 390 certified queries pass with **0.00% FSR**.
- 8/8 mutation operators pass.
- Latency $p50 < 0.5\text{ ms}$.

- [ ] **Step 2: Run full quality gate**

Run:
```bash
uv run ruff check .
uv run mypy src/unofficial_cepalstat_mcp/
uv build
uv run pytest -m "not integration" -q
```
Expected:
- `All checks passed!`
- `Success: no issues found in 35 source files`
- `Successfully built dist/...`
- `560+ passed, 3 deselected, 0 failed`

- [ ] **Step 3: Update Guardrails and Documentation**

- In `.agents/rules/semantic-resolution-guardrails.md`: update Invariant 2 to reflect that both `FacetOntology` and `ConceptOntology` are declarative, and procedural concept cascades in `parser.py` are strictly prohibited.
- In `AGENTS.md`: sync line references and note the completion of Phase 5.

- [ ] **Step 4: Commit**

```bash
git add .agents/rules/semantic-resolution-guardrails.md AGENTS.md
git commit -m "docs(governance): record Phase 5 declarative ConceptOntology refactor in guardrails and AGENTS.md"
```
