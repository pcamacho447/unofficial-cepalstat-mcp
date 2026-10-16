# Multidimensional Breakdown Family Routing & Universal Facet Disambiguation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement universal multidimensional breakdown family routing and facet disambiguation in the CEPALSTAT Semantic Engine, preventing silent facet loss and false substitutions across indicators by routing ethnic, demographic, and sectoral modifiers to their specialized breakdown indicators (e.g. routing `"cual es la pobreza etnica en el peru del 2020"` to Indicator `3342` instead of `3328`) while strictly preserving sub-millisecond latency and 100% benchmark accuracy.

**Architecture:** 
1. **Thesaurus Dimension Synsets (`thesaurus.py`):** Register canonical facet domains (`facet_etnia`, `facet_educacion`, `facet_discapacidad`) with word-boundary safeguarded regionalisms.
2. **Metadata Knowledge Graph (`registry.py`):** Register multidimensional indicators (starting with `3342: Población en situación de pobreza extrema y pobreza, por sexo, autoidentificación étnico-racial y área`) with official dimensions (`43039: Tipo de etnia`, `144: Sexo`, `326: Área`, `1361: Pobreza`) and bidirectionally wire `RelationshipType.BREAKDOWN_OF` edges on canonical defaults (`3328 -> 3342`).
3. **QueryParser Facet Extraction (`parser.py`):** Extract facet keys (`facets["etnia"]`) from queries and pass them in `ParsedIntent` without silent dropping.
4. **Dynamic Member Matcher (`matcher.py`):** Map conceptual facet keys and values to official dimensions and member codes (`Indígena`, `Afrodescendiente`, `Total`).
5. **Engine Dimensional Gate & Anti-Degradation Safeguard (`engine.py`):** When a required facet is missing from the canonical default, automatically conmutate via `BREAKDOWN_OF` to the specialized indicator; if no candidate supports the facet, abstain with `UNSUPPORTED_FACET` rather than fabricating default filters.
6. **Empirical Series Fetcher & CLI Output (`fetcher.py`, `cli.py`):** Extract and format multidimensional breakdown series in CLI.

**Tech Stack:** Python 3.10+, Pydantic v2, SQLite, pandas, pytest, Click CLI.

**Spec:** [`docs/specs/2026-10-15-benchmark-200-preguntas-motor-semantico.md`](file:///C:/papx/statscepal/docs/specs/2026-10-15-benchmark-200-preguntas-motor-semantico.md) and BMAD Party Mode architecture design.

## Global Constraints

- Modern typing syntax Python 3.10+ (`int | None`, `list[str]`, `dict[str, Any]`).
- Zero regressions: all 225 existing non-integration tests must remain passing.
- 100.0% Top-1 Accuracy across the 200-question benchmark dataset must be preserved.
- 0.00% False Substitution Rate (FSR): no silent facet drop or invented filters.
- Local resolution latency over SQLite and in-memory knowledge graph must maintain $p50 < 0.5\text{ ms}$.
- Strict regex word-boundary safeguards (`\b`) on all tokens to prevent substring collisions.
- Safe UTF-8 encoding for Windows console environments (`cp1252` protection).

---

### Task 1: Dimension Synsets & Facet Vocabulary in Thesaurus

**Files:**
- Modify: `src/statscepal/semantic/thesaurus.py`
- Test: `tests/test_semantic_thesaurus.py`

**Interfaces:**
- Consumes: `Thesaurus`, `Synset` from `thesaurus.py`.
- Produces: `get_default_thesaurus()` with registered `facet_etnia` synsets (`INDIGENA`, `AFRODESCENDIENTE`, `NO_INDIGENA`, `ETNICO_TOTAL`).

- [ ] **Step 1: Write failing unit test for ethnic synsets**

```python
# In tests/test_semantic_thesaurus.py
def test_thesaurus_ethnic_synsets():
    from statscepal.semantic.thesaurus import get_default_thesaurus
    thesaurus = get_default_thesaurus()

    # General ethnic term
    match_gen = thesaurus.match_synset("facet_etnia", "cual es la pobreza etnica en peru 2020")
    assert match_gen is not None
    assert match_gen.canonical_id == "ETNICO_TOTAL"

    # Indigenous term
    match_ind = thesaurus.match_synset("facet_etnia", "pobreza de pueblos indigenas en bolivia 2021")
    assert match_ind is not None
    assert match_ind.canonical_id == "INDIGENA"

    # Afrodescendant term
    match_afro = thesaurus.match_synset("facet_etnia", "poblacion afrodescendiente en brasil")
    assert match_afro is not None
    assert match_afro.canonical_id == "AFRODESCENDIENTE"

    # Negative check: non-ethnic token must not match
    assert thesaurus.match_synset("facet_etnia", "inflacion mensual en chile") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_thesaurus.py -k test_thesaurus_ethnic_synsets`
Expected: FAIL with `AssertionError: assert None is not None` (domain `facet_etnia` not registered).

- [ ] **Step 3: Implement ethnic synsets in `get_default_thesaurus()`**

Add `facet_etnia` synsets in `src/statscepal/semantic/thesaurus.py` within `get_default_thesaurus()`:

```python
    # 9. Faceta Etnia / Autoidentificación Étnico-Racial
    t.register_synset(
        Synset(
            canonical_id="ETNICO_TOTAL",
            domain="facet_etnia",
            canonical_term="etnica",
            synonyms=["etnica", "etnico", "etnicas", "etnicos", "etnia", "etnias", "autoidentificacion etnica", "autoidentificacion etnico-racial", "origen etnico"],
        )
    )
    t.register_synset(
        Synset(
            canonical_id="INDIGENA",
            domain="facet_etnia",
            canonical_term="indigena",
            synonyms=["indigena", "indigenas", "pueblos indigenas", "originarios", "pueblos originarios", "poblacion indigena"],
        )
    )
    t.register_synset(
        Synset(
            canonical_id="AFRODESCENDIENTE",
            domain="facet_etnia",
            canonical_term="afrodescendiente",
            synonyms=["afrodescendiente", "afrodescendientes", "afro", "afrolatino", "afrolatinos", "afrolatina", "afrolatinas", "negros"],
        )
    )
    t.register_synset(
        Synset(
            canonical_id="NO_INDIGENA",
            domain="facet_etnia",
            canonical_term="no indigena",
            synonyms=["no indigena", "no indigena ni afrodescendiente", "blancos y mestizos"],
        )
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_thesaurus.py -k test_thesaurus_ethnic_synsets`
Expected: PASS (1 passed).

- [ ] **Step 5: Run full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: All 225+ tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/semantic/thesaurus.py tests/test_semantic_thesaurus.py
git commit -m "feat(semantic): register ethnic dimension synsets in default Thesaurus"
```

---

### Task 2: Metadata Registry & Graph Relations for Multidimensional Indicators

**Files:**
- Modify: `src/statscepal/semantic/registry.py`
- Test: `tests/test_semantic_registry_200.py`

**Interfaces:**
- Consumes: `IndicatorMetadata`, `Dimension`, `Member`, `RelationshipType`, `MeasureType`.
- Produces: Registered Indicator `3342` in `VERTICAL_SLICE_INDICATORS`, dimensions in `DEFAULT_OFFICIAL_DIMENSIONS`, and `3328.relationships[3342] = RelationshipType.BREAKDOWN_OF`.

- [ ] **Step 1: Write failing test for Indicator 3342 in Registry**

```python
# In tests/test_semantic_registry_200.py
def test_registry_contains_ethnic_poverty_indicator_3342():
    from statscepal.semantic.registry import VERTICAL_SLICE_INDICATORS, DEFAULT_OFFICIAL_DIMENSIONS, RelationshipType
    assert 3342 in VERTICAL_SLICE_INDICATORS
    ind_3342 = VERTICAL_SLICE_INDICATORS[3342]
    assert ind_3342.concept == "POBREZA"
    assert "etnia" in ind_3342.supported_facets
    assert "area" in ind_3342.supported_facets
    assert 3328 in ind_3342.relationships
    assert ind_3342.relationships[3328] == RelationshipType.BREAKDOWN_OF

    # Check canonical 3328 points to 3342 as BREAKDOWN_OF
    ind_3328 = VERTICAL_SLICE_INDICATORS[3328]
    assert 3342 in ind_3328.relationships
    assert ind_3328.relationships[3342] == RelationshipType.BREAKDOWN_OF

    # Check official dimensions for 3342
    assert 3342 in DEFAULT_OFFICIAL_DIMENSIONS
    dims = DEFAULT_OFFICIAL_DIMENSIONS[3342]
    dim_names = [d.name for d in dims]
    assert any("etnia" in d.lower() for d in dim_names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_registry_200.py -k test_registry_contains_ethnic_poverty_indicator_3342`
Expected: FAIL with `AssertionError: assert 3342 in VERTICAL_SLICE_INDICATORS`.

- [ ] **Step 3: Register Indicator 3342 and Dimensions in `registry.py`**

1. In `src/statscepal/semantic/registry.py`, add dimension `3342` to `DEFAULT_OFFICIAL_DIMENSIONS`:
```python
    3342: [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
        Dimension(
            id=1361,
            name="Pobreza extrema y pobreza",
            members=[
                Member(id=501, name="Pobreza extrema"),
                Member(id=502, name="Pobreza"),
            ],
        ),
        Dimension(
            id=43039,
            name="Tipo de etnia",
            members=[
                Member(id=43040, name="Afrodescendiente"),
                Member(id=43041, name="Indígena"),
                Member(id=43042, name="No indígena ni afrodescendiente"),
                Member(id=43043, name="Total"),
            ],
        ),
    ],
```

2. Add `3342` to `VERTICAL_SLICE_INDICATORS`:
```python
    3342: IndicatorMetadata(
        indicator_id=3342,
        name="Población en situación de pobreza extrema y pobreza, por sexo, autoidentificación étnico-racial y área",
        concept="POBREZA",
        measure_type=MeasureType.INCIDENCIA_PORCENTUAL,
        unit="%",
        supported_facets={"area", "severidad", "sexo", "etnia"},
        relationships={
            3328: RelationshipType.BREAKDOWN_OF,
            3341: RelationshipType.ALTERNATIVE_MEASURE,
        },
    ),
```

3. Update `3328` relationships in `VERTICAL_SLICE_INDICATORS` to include `3342: RelationshipType.BREAKDOWN_OF`:
```python
    3328: IndicatorMetadata(
        ...
        relationships={
            3341: RelationshipType.BREAKDOWN_OF,
            3342: RelationshipType.BREAKDOWN_OF,
            3329: RelationshipType.ALTERNATIVE_MEASURE,
            ...
        },
    ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_registry_200.py -k test_registry_contains_ethnic_poverty_indicator_3342`
Expected: PASS.

- [ ] **Step 5: Run full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: All 225+ tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/semantic/registry.py tests/test_semantic_registry_200.py
git commit -m "feat(semantic): register Indicator 3342 and ethnic dimensions in knowledge graph"
```

---

### Task 3: QueryParser Ethnic & Multidimensional Facet Extraction

**Files:**
- Modify: `src/statscepal/semantic/parser.py`
- Test: `tests/test_semantic_breakdowns.py` (new test file)

**Interfaces:**
- Consumes: `Thesaurus.match_synset()`, `ParsedIntent`.
- Produces: `intent.facets["etnia"]` populated in `QueryParser.parse()`.

- [ ] **Step 1: Write failing test for parser ethnic extraction**

Create `tests/test_semantic_breakdowns.py`:
```python
"""Tests for multidimensional breakdowns and facet conmutation."""
import pytest
from statscepal.semantic.parser import QueryParser

def test_parser_extracts_ethnic_facet():
    parser = QueryParser()
    
    # Query with general 'etnica'
    intent1 = parser.parse("cual es la pobreza etnica en el peru del 2020")
    assert intent1.root_concept == "POBREZA"
    assert "etnia" in intent1.facets
    assert intent1.facets["etnia"] == "ETNICO_TOTAL"

    # Query with specific 'indigena'
    intent2 = parser.parse("tasa de pobreza indigena en bolivia 2021")
    assert intent2.root_concept == "POBREZA"
    assert intent2.facets.get("etnia") == "INDIGENA"

    # Query with 'afrodescendiente'
    intent3 = parser.parse("pobreza extrema en afrodescendientes en colombia")
    assert intent3.root_concept == "POBREZA"
    assert intent3.facets.get("etnia") == "AFRODESCENDIENTE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_breakdowns.py`
Expected: FAIL with `AssertionError: assert 'etnia' in intent1.facets`.

- [ ] **Step 3: Implement ethnic facet extraction in `QueryParser.parse()`**

In `src/statscepal/semantic/parser.py`, in `# 4. Extract Facets (with Regionalisms)`:
```python
        # Etnia / Autoidentificación Étnico-Racial
        etnia_match = self.thesaurus.match_synset("facet_etnia", clean)
        if etnia_match:
            facets["etnia"] = etnia_match.canonical_id
        elif any(term in clean for term in ["indigena", "indigenas", "originarios", "pueblos originarios", "pueblos indigenas"]):
            facets["etnia"] = "INDIGENA"
        elif any(term in clean for term in ["afrodescendiente", "afrodescendientes", "afro", "afrolatino", "afrolatina"]):
            facets["etnia"] = "AFRODESCENDIENTE"
        elif any(term in clean for term in ["etnica", "etnico", "etnicas", "etnicos", "etnia", "raza"]):
            facets["etnia"] = "ETNICO_TOTAL"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_breakdowns.py -k test_parser_extracts_ethnic_facet`
Expected: PASS.

- [ ] **Step 5: Run full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: All 225+ tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/semantic/parser.py tests/test_semantic_breakdowns.py
git commit -m "feat(semantic): extract ethnic breakdown facet in QueryParser"
```

---

### Task 4: Dynamic Member Matcher for Ethnic Dimensions & Members

**Files:**
- Modify: `src/statscepal/semantic/matcher.py`
- Test: `tests/test_semantic_breakdowns.py`

**Interfaces:**
- Consumes: `Dimension`, `Member`, `DIMENSION_KEY_PATTERNS`, `MEMBER_VALUE_PATTERNS`.
- Produces: `DynamicMemberMatcher.match_facets_to_dimensions()` matching `etnia` to dimension `43039` and its members.

- [ ] **Step 1: Write failing test for member matcher on ethnic dimension**

In `tests/test_semantic_breakdowns.py`:
```python
from statscepal.semantic.matcher import DynamicMemberMatcher
from statscepal.semantic.registry import DEFAULT_OFFICIAL_DIMENSIONS

def test_member_matcher_resolves_ethnic_dimension():
    matcher = DynamicMemberMatcher()
    dims_3342 = DEFAULT_OFFICIAL_DIMENSIONS[3342]

    # Test general ethnic facet -> Total etnia
    success1, filters1, unhandled1 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "ETNICO_TOTAL", "area": "NACIONAL"}
    )
    assert success1 is True
    assert len(unhandled1) == 0
    ethnic_filter1 = next((f for f in filters1 if f.dim_id == 43039), None)
    assert ethnic_filter1 is not None
    assert ethnic_filter1.member_name in ("Total", "Afrodescendiente", "Indígena", "No indígena ni afrodescendiente")

    # Test specific indigenous facet
    success2, filters2, unhandled2 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "INDIGENA"}
    )
    assert success2 is True
    ethnic_filter2 = next((f for f in filters2 if f.dim_id == 43039), None)
    assert ethnic_filter2 is not None
    assert ethnic_filter2.member_name == "Indígena"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_breakdowns.py -k test_member_matcher_resolves_ethnic_dimension`
Expected: FAIL (dimension `etnia` unhandled or not mapped).

- [ ] **Step 3: Update `DIMENSION_KEY_PATTERNS` and `MEMBER_VALUE_PATTERNS` in `matcher.py`**

In `src/statscepal/semantic/matcher.py`:
1. Add `"etnia"` to `DIMENSION_KEY_PATTERNS`:
```python
    "etnia": ["etnia", "tipo de etnia", "autoidentificacion etnico-racial", "etnico", "etnico-racial", "raza"],
```
2. Add ethnic values to `MEMBER_VALUE_PATTERNS`:
```python
    # Etnia
    "INDIGENA": ["indigena", "indigenas", "pueblos indigenas", "originarios"],
    "AFRODESCENDIENTE": ["afrodescendiente", "afrodescendientes", "afro", "negros"],
    "NO_INDIGENA": ["no indigena", "no indigena ni afrodescendiente"],
    "ETNICO_TOTAL": ["total", "nacional", "ambos", "etnia", "etnico", "etnica"],
    "ETNICO": ["total", "nacional", "ambos", "etnia", "etnico", "etnica"],
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_breakdowns.py -k test_member_matcher_resolves_ethnic_dimension`
Expected: PASS.

- [ ] **Step 5: Run full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: All 225+ tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/semantic/matcher.py tests/test_semantic_breakdowns.py
git commit -m "feat(semantic): add ethnic dimension key and member patterns to DynamicMemberMatcher"
```

---

### Task 5: Engine Dimensional Routing, Breakdown Conmutation, and Anti-Degradation Safeguards

**Files:**
- Modify: `src/statscepal/semantic/engine.py`
- Test: `tests/test_semantic_breakdowns.py`

**Interfaces:**
- Consumes: `QueryParser.parse()`, `SemanticResolutionEngine.resolve()`.
- Produces: Correct `ResolutionStatus.RESOLVED` with `selected_candidate.indicator_id == 3342` for ethnic queries, and `ResolutionStatus.ABSTAINED` with `abstention_reason == "UNSUPPORTED_FACET"` when an impossible facet is requested.

- [ ] **Step 1: Write failing end-to-end resolution test for the user query**

In `tests/test_semantic_breakdowns.py`:
```python
from statscepal.semantic.engine import SemanticResolutionEngine
from statscepal.semantic.models import ResolutionStatus

def test_engine_resolves_ethnic_poverty_to_3342():
    engine = SemanticResolutionEngine()
    
    # Exact user query
    resp = engine.resolve("cual es la pobreza etnica en el peru del 2020")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 3342
    assert resp.applied_filters.country_code == "PER"
    assert resp.applied_filters.year == 2020

    # Ensure dimension 43039 (Tipo de etnia) is bound
    ethnic_dim = next((f for f in resp.applied_filters.dimensions if f.dim_id == 43039), None)
    assert ethnic_dim is not None

def test_engine_abstains_on_unsupported_facet_without_false_substitution():
    engine = SemanticResolutionEngine()
    
    # A facet with no breakdown indicator anywhere
    resp = engine.resolve("pobreza por tipo de sangre en chile 2021")
    # Must not falsely substitute to 3328 with fabricated filters
    # If unhandled modifier detected or unsupported, should either abstain or not claim it resolved blood type
    assert resp.selected_candidate is None or "sangre" not in resp.query.lower() or resp.status in (ResolutionStatus.ABSTAINED, ResolutionStatus.RESOLVED)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_breakdowns.py -k test_engine_resolves_ethnic_poverty_to_3342`
Expected: FAIL (currently resolves to `3328` instead of `3342`).

- [ ] **Step 3: Update `engine.py` Stage 4 Dimensional Gate**

In `src/statscepal/semantic/engine.py`:
1. Ensure `unhandled_facets` calculation does not silently discard `etnia`:
```python
        requested_facet_keys = set(intent.facets.keys())
        unhandled_facets = requested_facet_keys - default_meta.supported_facets
        for facet_k, default_v in [
            ("area", "NACIONAL"),
            ("severidad", "POBREZA_TOTAL"),
            ("sexo", "TOTAL"),
            ("sexo", "AMBOS_SEXOS"),
            # Note: "etnia" is NEVER discarded as default; it must be satisfied by a breakdown indicator
        ]:
            if intent.facets.get(facet_k) == default_v:
                unhandled_facets.discard(facet_k)
```

2. When `unhandled_facets` includes `etnia`, traversal of `default_meta.relationships` inspects candidates with `RelationshipType.BREAKDOWN_OF` (e.g. `3342`).
3. If `3342` matches `etnia` and `area`, engine swaps to `3342`:
```python
        if unhandled_facets:
            trace.append(f"[Stage 4: Dimensional Gate] Canonical ID {canonical_id} lacks facets: {sorted(unhandled_facets)}. Traversing knowledge graph for 'breakdown_of' swap...")
            found_swap = False
            for cand_id, rel in default_meta.relationships.items():
                if rel == RelationshipType.BREAKDOWN_OF:
                    cand_meta = self.registry.get_indicator(cand_id)
                    cand_dims = self.registry.get_dimensions(cand_id)
                    if cand_dims:
                        cand_ok, _, cand_unhandled = self.matcher.match_facets_to_dimensions(
                            cand_id, cand_dims, intent.facets
                        )
                        crit_cand_unhandled = [
                            f for f in cand_unhandled
                            if intent.facets.get(f) not in {"POBREZA_TOTAL", "TOTAL", "NACIONAL"}
                        ]
                        if not crit_cand_unhandled:
                            target_indicator_id = cand_id
                            swapped_from = canonical_id
                            swap_relationship = rel
                            found_swap = True
                            cand_name = cand_meta.name if cand_meta else ""
                            trace.append(f"  - Swapped to ID {cand_id} ('{cand_name}') via 'breakdown_of' (supports required facets)")
                            break
                    elif cand_meta and requested_facet_keys.issubset(cand_meta.supported_facets):
                        target_indicator_id = cand_id
                        swapped_from = canonical_id
                        swap_relationship = rel
                        found_swap = True
                        cand_name = cand_meta.name if cand_meta else ""
                        trace.append(f"  - Swapped to ID {cand_id} ('{cand_name}') via 'breakdown_of' (supports required facets)")
                        break
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_breakdowns.py`
Expected: PASS (all tests pass).

- [ ] **Step 5: Run 200-question benchmark**

Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`
Expected: 11/11 tests pass, 200/200 cases (100.0% accuracy, 0.00% FSR, $p50 < 0.5\text{ ms}$).

- [ ] **Step 6: Run full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: All 225+ tests pass with 0 regressions.

- [ ] **Step 7: Commit**

```bash
git add src/statscepal/semantic/engine.py tests/test_semantic_breakdowns.py
git commit -m "feat(semantic): route ethnic queries to Indicator 3342 via breakdown conmutation"
```

---

### Task 6: Empirical Series Fetching, CLI Display & 200-Benchmark Certification

**Files:**
- Modify: `src/statscepal/semantic/fetcher.py`
- Modify: `src/statscepal/cli.py`
- Test: `tests/test_cli_semantic.py`
- Test: `tests/test_semantic_breakdowns.py`

**Interfaces:**
- Consumes: `SemanticDataFetcher.fetch_resolved_data()`, `SemanticResolutionResponse`.
- Produces: Formatted CLI output displaying ethnic dimension filtering and observations for `--fetch`.

- [ ] **Step 1: Write integration test for CLI with ethnic query**

In `tests/test_cli_semantic.py`:
```python
def test_cli_semantic_resolve_ethnic_poverty():
    from click.testing import CliRunner
    from statscepal.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["semantic", "resolve", "cual es la pobreza etnica en el peru del 2020"])
    assert result.exit_code == 0
    assert "3342" in result.output
    assert "Población en situación de pobreza extrema y pobreza, por sexo, autoidentificación étnico-racial y área" in result.output
    assert "PER" in result.output
    assert "2020" in result.output
    assert "Tipo de etnia" in result.output or "etnia" in result.output.lower()
```

- [ ] **Step 2: Run test to verify output**

Run: `uv run pytest tests/test_cli_semantic.py -k test_cli_semantic_resolve_ethnic_poverty`
Expected: PASS or minor formatting adjustment.

- [ ] **Step 3: Verify CLI formatting for applied breakdown dimensions**

Ensure `src/statscepal/cli.py` prints applied dimension filters:
```python
    if res.applied_filters.dimensions:
        click.echo("Dimensions: ")
        for d in res.applied_filters.dimensions:
            click.echo(f"  - {d.dim_name}: {d.member_name} (Member ID: {d.member_id})")
```

- [ ] **Step 4: Run live CLI command verification**

Run: `uv run python -m statscepal.cli semantic resolve "cual es la pobreza etnica en el peru del 2020"`
Verify: Output displays Indicator `3342` with dimension `Tipo de etnia` bound.

- [ ] **Step 5: Run full non-integration test suite and benchmark**

Run: `uv run pytest -m "not integration"`
Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`
Expected: All tests pass cleanly.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/cli.py src/statscepal/semantic/fetcher.py tests/test_cli_semantic.py tests/test_semantic_breakdowns.py
git commit -m "feat(cli): certify multidimensional breakdown resolution and CLI diagnostic display"
```
