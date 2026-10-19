# Unconsumed Semantic Tokens Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an Unconsumed Semantic Tokens Guard in the CEPALSTAT semantic parser and resolution engine to eradicate false substitutions by penalizing or abstaining on queries with unparsed domain-specific modifiers, while fixing the spurious `area=NACIONAL` facet in currency queries.

**Architecture:** Extend `ParsedIntent` to track `unconsumed_tokens` extracted by `QueryParser` using Spanish stopword filtering and token span subtraction. Introduce a Stage 3.5 Specificity Guard in `SemanticResolutionEngine` that audits remaining domain tokens against candidate indicator metadata, degrading status to `ALTERNATIVE_PROPOSED` (score 0.65) or `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) with explanatory hints. Fix `moneda nacional` in `thesaurus.py` and `parser.py` so currency expressions do not trigger geographic `area=NACIONAL`.

**Tech Stack:** Python 3.10+, Pydantic v2, pytest.

**Spec:** Motivation and empirical test cases from user CLI execution (false substitutions on manufacturing value added per capita `4211` -> `730`, agricultural minimum wage `3140` -> `3337`, expenditure-component quarterly GDP `294` -> `731`, and spurious `area=NACIONAL` facet on `moneda nacional`).

## Global Constraints

- Python 3.10+ modern typing syntax.
- All 329+ existing non-integration tests must pass without regression.
- False Substitution Rate must strictly equal 0.00% across the 200-question benchmark.
- Top-1 Accuracy across the 200 benchmark test cases must strictly remain 100.0%.
- Local resolution latency over SQLite and in-memory thesaurus must maintain p50 < 0.5 ms.
- Safe UTF-8 encoding for Windows console environments.
- Strict offline hermeticity: test suites must NEVER perform live network calls to CEPALSTAT.

---

### Task 1: Fix Currency Unit vs. Geographic Area Collision (`moneda nacional` -> `area=NACIONAL`)

**Files:**
- Modify: `src/statscepal/semantic/thesaurus.py:243-247`
- Modify: `src/statscepal/semantic/parser.py:382-393`
- Test: `tests/test_semantic_unconsumed_tokens_guard.py`

**Interfaces:**
- Consumes: `Thesaurus.match_synset`, `QueryParser.parse`
- Produces: `ParsedIntent` with `facets` free of spurious `area=NACIONAL` when query specifies `moneda nacional`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_semantic_unconsumed_tokens_guard.py
from statscepal.semantic import SemanticResolutionEngine
from statscepal.semantic.parser import QueryParser

def test_moneda_nacional_does_not_trigger_area_nacional_facet():
    parser = QueryParser()
    intent = parser.parse("ingresos tributarios del peru en moneda nacional en 2022")
    assert "area" not in intent.facets, f"Expected no area facet, got {intent.facets}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_unconsumed_tokens_guard.py::test_moneda_nacional_does_not_trigger_area_nacional_facet -v`
Expected: FAIL with `AssertionError: Expected no area facet, got {'area': 'NACIONAL'}`.

- [ ] **Step 3: Write minimal implementation**

In `src/statscepal/semantic/thesaurus.py`, update the `NACIONAL` synset in `DEFAULT_CANONICAL_SYNSETS`:
change `canonical_term="total nacional"` and synonyms to require multi-word explicit phrases (`"todo el pais"`, `"nivel nacional"`, `"area nacional"`, `"total nacional"`).

In `src/statscepal/semantic/parser.py`:
When `"moneda nacional"` is detected in `clean`, ensure that `area` is not mapped to `NACIONAL` unless explicit phrases like `"area nacional"` or `"nivel nacional"` are present.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_unconsumed_tokens_guard.py::test_moneda_nacional_does_not_trigger_area_nacional_facet -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/semantic/thesaurus.py src/statscepal/semantic/parser.py tests/test_semantic_unconsumed_tokens_guard.py
git commit -m "fix(semantic): prevent currency expression 'moneda nacional' from triggering geographic area facet"
```

---

### Task 2: Implement Token Span Subtraction & Unconsumed Semantic Tokens in `QueryParser`

**Files:**
- Modify: `src/statscepal/semantic/parser.py`
- Test: `tests/test_semantic_unconsumed_tokens_guard.py`

**Interfaces:**
- Consumes: `QueryParser.parse`, `ParsedIntent`
- Produces: `ParsedIntent.unconsumed_tokens: list[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_semantic_unconsumed_tokens_guard.py
def test_unconsumed_tokens_extraction_on_domain_modifiers():
    parser = QueryParser()
    
    # 1. Clean query with no modifiers
    intent1 = parser.parse("pib per capita de bolivia en 2020")
    assert intent1.unconsumed_tokens == [], f"Expected empty, got {intent1.unconsumed_tokens}"

    # 2. Manufacturing modifier
    intent2 = parser.parse("valor agregado manufacturero por habitante en mexico")
    assert "manufacturero" in intent2.unconsumed_tokens, f"Expected 'manufacturero' in {intent2.unconsumed_tokens}"

    # 3. Agricultural modifier
    intent3 = parser.parse("salario minimo agricola en guatemala")
    assert "agricola" in intent3.unconsumed_tokens, f"Expected 'agricola' in {intent3.unconsumed_tokens}"

    # 4. Expenditure component modifier
    intent4 = parser.parse("pib trimestral por componente del gasto en brasil")
    assert any(t in intent4.unconsumed_tokens for t in ["componente", "gasto"]), f"Expected expenditure tokens in {intent4.unconsumed_tokens}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_unconsumed_tokens_guard.py::test_unconsumed_tokens_extraction_on_domain_modifiers -v`
Expected: FAIL with `AttributeError: 'ParsedIntent' object has no attribute 'unconsumed_tokens'`.

- [ ] **Step 3: Write minimal implementation**

1. In `src/statscepal/semantic/parser.py`:
   - Add `unconsumed_tokens: list[str] = Field(default_factory=list)` to `ParsedIntent`.
   - Define `SPANISH_STOPWORDS: frozenset[str]` containing grammatical words, prepositions, articles, and statistical fillers (`de`, `del`, `en`, `el`, `la`, `los`, `las`, `un`, `una`, `y`, `por`, `para`, `con`, `sin`, `ano`, `anos`, `tasa`, `nivel`, `indicador`, `datos`, etc.).
   - During `parse()`, collect all matched strings into `consumed_phrases`:
     - Matched country names and demonyms.
     - Matched years, decade/quinquennium phrases.
     - Matched frequency words (`trimestral`, `anual`, `mensual`).
     - Matched polarity terms.
     - Matched root concept triggers (e.g. `pib per capita`, `salario minimo`, `pib trimestral`, `impuestos`, etc.).
     - Matched facet triggers (e.g. `rural`, `afrodescendiente`, etc.).
     - Currency expressions (e.g. `moneda nacional`, `dolares`).
   - Extract words from `clean` and remove all tokens belonging to `consumed_phrases` or `SPANISH_STOPWORDS`.
   - Assign the result to `intent.unconsumed_tokens`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_unconsumed_tokens_guard.py::test_unconsumed_tokens_extraction_on_domain_modifiers -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/semantic/parser.py tests/test_semantic_unconsumed_tokens_guard.py
git commit -m "feat(semantic): track unconsumed semantic domain tokens in ParsedIntent"
```

---

### Task 3: Stage 3.5 Specificity Guard in `SemanticResolutionEngine`

**Files:**
- Modify: `src/statscepal/semantic/engine.py`
- Modify: `src/statscepal/semantic/models.py`
- Test: `tests/test_semantic_unconsumed_tokens_guard.py`

**Interfaces:**
- Consumes: `ParsedIntent.unconsumed_tokens`, `Indicator` metadata
- Produces: `SemanticResolutionResponse` with audited status (never false 1.0 when domain modifiers are unconsumed)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_semantic_unconsumed_tokens_guard.py
from statscepal.semantic import ResolutionStatus

def test_guard_prevents_false_substitution_on_manufacturing_gdp():
    engine = SemanticResolutionEngine()
    resp = engine.resolve("valor agregado manufacturero por habitante en mexico")
    # Must NOT resolve as general GDP with score 1.0
    assert resp.status in (ResolutionStatus.ABSTAINED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    if resp.status == ResolutionStatus.ALTERNATIVE_PROPOSED:
        assert resp.selected_candidate.relevance_score <= 0.70
    assert "manufacturero" in (resp.conversational_hint or "") or "manufacturero" in resp.abstention_reason

def test_guard_downgrades_on_agricultural_minimum_wage():
    engine = SemanticResolutionEngine()
    resp = engine.resolve("salario minimo agricola en guatemala")
    # Must NOT be score 1.0 RESOLVED
    assert resp.status in (ResolutionStatus.ALTERNATIVE_PROPOSED, ResolutionStatus.ABSTAINED)
    if resp.status == ResolutionStatus.ALTERNATIVE_PROPOSED:
        assert resp.selected_candidate.relevance_score <= 0.70
        assert "agricola" in (resp.conversational_hint or "") or "agrícola" in (resp.conversational_hint or "")

def test_guard_prevents_false_substitution_on_quarterly_gdp_expenditure():
    engine = SemanticResolutionEngine()
    resp = engine.resolve("pib trimestral por componente del gasto en brasil")
    # Must NOT resolve to 731 with score 1.0
    assert resp.status in (ResolutionStatus.ABSTAINED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    if resp.selected_candidate and resp.selected_candidate.indicator_id == 731:
        assert resp.status != ResolutionStatus.RESOLVED or resp.selected_candidate.relevance_score < 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_unconsumed_tokens_guard.py -k "test_guard" -v`
Expected: FAIL because currently all three return `status=RESOLVED` with `relevance_score=1.0`.

- [ ] **Step 3: Write minimal implementation**

In `src/statscepal/semantic/engine.py`:
Insert Stage 3.5 Specificity Audit:
1. If `intent.unconsumed_tokens`:
   - Inspect whether the candidate indicator's name or metadata covers the unconsumed tokens.
   - If unconsumed tokens contain critical specificity terms (`manufacturero`, `agricola`, `gasto`, `componente`, `subyacente`, `cobre`, etc.) that are absent from the indicator:
     - For severe conceptual divergence (e.g. `manufacturero` vs total GDP `730`, or `componente del gasto` vs GDP growth `731`):
       - If no exact candidate exists, return `status = ResolutionStatus.ABSTAINED` with `abstention_reason = "UNRESOLVED_SPECIFICITY: " + ", ".join(unconsumed)` and an informative conversational hint.
     - For general fallback (e.g. `salario minimo agricola` falling back to general minimum wage `3337`):
       - Degrade `status = ResolutionStatus.ALTERNATIVE_PROPOSED`.
       - Set `selected.relevance_score = 0.65`.
       - Provide conversational hint explaining the coverage limitation:
         `"Nota: Se propone el indicador general 3337 ('Salario mínimo real'), pero la consulta solicitaba la especificidad: 'agrícola'. Para el indicador sectorial consulte el catálogo de CEPALSTAT (ID 3140)."`
       - Add decision audit log to `trace`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_unconsumed_tokens_guard.py -v`
Expected: PASS.

- [ ] **Step 5: Run full benchmark & regression suite**

Run:
`uv run pytest tests/test_semantic_benchmark_200.py -v`
`uv run pytest tests/test_semantic_motivating_remediations.py -v`
`uv run pytest -m "not integration"`
Expected: ALL 329+ tests PASS, benchmark remains 100% Top-1 Accuracy and 0.00% FSR.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/semantic/engine.py tests/test_semantic_unconsumed_tokens_guard.py
git commit -m "feat(semantic): enforce unconsumed semantic tokens guard to eliminate false substitutions"
```

---

### Task 4: End-to-End CLI Verification & Certification

**Files:**
- Test: Manual CLI execution with `--explain`

- [ ] **Step 1: Execute test queries via CLI**

Execute:
- `uv run statscepal semantic resolve "valor agregado manufacturero por habitante en mexico" --explain`
- `uv run statscepal semantic resolve "salario minimo agricola en guatemala" --explain`
- `uv run statscepal semantic resolve "pib trimestral por componente del gasto en brasil" --explain`
- `uv run statscepal semantic resolve "ingresos tributarios del peru en moneda nacional en 2022" --explain`

Verify:
- None of the 3 problematic queries return `RESOLVED` with score 1.0.
- `moneda nacional` no longer has `area=NACIONAL`.
- Hints and audit logs clearly describe the unconsumed terms.

- [ ] **Step 2: Commit plan document**

```bash
git add docs/superpowers/plans/2026-10-18-unconsumed-semantic-tokens-guard-plan.md
git commit -m "docs: add implementation plan for unconsumed semantic tokens guard"
```
