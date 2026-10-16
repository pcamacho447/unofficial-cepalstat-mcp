# Task E2: Declarative Facet Ontology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single declarative `FacetOntology` module (`src/statscepal/semantic/facet_ontology.py`) that centralizes all canonical socioeconomic facets, dimension ID/name bindings, member value patterns, query trigger rules, and implicit-aggregate semantics—and expose a `statscepal catalog facet-audit` CLI command to audit harvested SQLite dimensions against the ontology.

**Architecture:** Introduce immutable Pydantic/dataclass models (`FacetDefinition`, `MemberPatternRule`, `QueryTriggerRule`, `FacetAuditReport`) in `src/statscepal/semantic/facet_ontology.py`. Wire `DynamicMemberMatcher` (`matcher.py`) to derive `DIMENSION_KEY_PATTERNS` and `MEMBER_VALUE_PATTERNS` directly from `DEFAULT_FACET_ONTOLOGY` while keeping backward-compatible module-level exports. Add `CatalogStore.get_distinct_dimensions()` and a `facet-audit` CLI subcommand to inspect harvested SQLite dimensions and report mapped vs. unmapped dimension gaps.

**Tech Stack:** Python 3.10+, Pydantic v2, SQLite3, re, unicodedata, pytest.

**Spec:** [docs/superpowers/plans/2026-10-16-epic-metadata-ingestion-generic-facet-routing.md](file:///C:/papx/statscepal/docs/superpowers/plans/2026-10-16-epic-metadata-ingestion-generic-facet-routing.md) (Section E2) and [.agents/rules/semantic-resolution-guardrails.md](file:///C:/papx/statscepal/.agents/rules/semantic-resolution-guardrails.md).

## Global Constraints
- Python 3.10+ modern typing syntax (`int | None`, `list[str]`, `dict[str, Any]`).
- All 246+ existing non-integration tests must remain passing without regression.
- False Substitution Rate must strictly equal 0.00% across the 200-question benchmark.
- Top-1 Accuracy across the 200 benchmark test cases must strictly remain 100.0%.
- Local resolution latency over SQLite and in-memory thesaurus must maintain $p50 < 0.5\text{ ms}$.
- All lexical and regex triggers must enforce strict word boundaries (`\b`) to prevent substring and regional slang collisions.
- Strict offline hermeticity: unit and CLI tests must NEVER perform live network calls.
- Safe ASCII/UTF-8 console output for Windows CP1252 environments.

---

## File Structure & Responsibilities

| File | Action | Responsibility |
|---|---|---|
| `src/statscepal/semantic/facet_ontology.py` | Create | Declarative facet ontology models (`FacetDefinition`, `QueryTriggerRule`, `FacetAuditReport`, `FacetOntology`) and `DEFAULT_FACET_ONTOLOGY` registry covering all socioeconomic and structural dimensions. |
| `src/statscepal/semantic/matcher.py` | Modify | Delegate `DIMENSION_KEY_PATTERNS`, `MEMBER_VALUE_PATTERNS`, and dimension/member resolution to `FacetOntology` while preserving backward-compatible exports. |
| `src/statscepal/catalog/store.py` | Modify | Add `get_distinct_harvested_dimensions() -> list[dict[str, Any]]` to query unique `(dim_id, dim_name, indicator_count)` from `indicator_dimensions`. |
| `src/statscepal/cli.py` | Modify | Add `statscepal catalog facet-audit [--json]` subcommand and handler to print coverage and gap reports over harvested SQLite dimensions. |
| `tests/test_semantic_facet_ontology.py` | Create | Unit and integration tests for `FacetOntology` models, dimension classification, implicit-aggregate semantics, matcher delegation, and CLI `facet-audit`. |

---

### Task 1: Core `FacetOntology` Data Models & Declarative Registry

**Files:**
- Create: `src/statscepal/semantic/facet_ontology.py`
- Test: `tests/test_semantic_facet_ontology.py`

**Interfaces:**
- Consumes: `strip_accents` from `statscepal.semantic.matcher` (or shared helper), `Dimension` from `statscepal.dimensions`.
- Produces:
  - `QueryTriggerRule(canonical_value: str, phrases: tuple[str, ...], require_word_boundary: bool = True)`
  - `FacetDefinition`:
    - `facet_key: str` (e.g., `"sexo"`, `"area"`, `"edad"`, `"etnia"`, `"estrato"`, `"quintil"`, `"educacion"`, `"formalidad"`, `"severidad"`, `"canasta"`, `"rubro"`, `"moneda"`, `"actividad"`)
    - `description: str`
    - `synset_domain: str | None` (e.g., `"facet_etnia"`, `"facet_sexo"`, `"facet_area"`, `"facet_edad"`, `"facet_severidad"`, `"facet_formalidad"`, `"facet_canasta"`)
    - `known_dimension_ids: frozenset[int]` (e.g., `{144}` for `sexo`, `{326, 1364}` for `area`, `{43039}` for `etnia`, `{1361, 500}` for `severidad`)
    - `dimension_name_patterns: tuple[str, ...]`
    - `member_value_patterns: dict[str, tuple[str, ...]]`
    - `implicit_aggregate_values: frozenset[str]` (values that can be satisfied implicitly by a national/total canonical indicator without forcing a breakdown swap, e.g., `frozenset({"NACIONAL"})` for `area`, `frozenset({"POBREZA_TOTAL"})` for `severidad`, `frozenset({"TOTAL", "AMBOS_SEXOS", "AMBOS"})` for `sexo`, and `frozenset()` for `etnia`, `edad`, `estrato`, `quintil`, `educacion`, `formalidad` where any request—including `"ETNICO_TOTAL"` or `"QUINTIL"`—requires the breakdown dimension to exist)
    - `total_member_patterns: tuple[str, ...]` (e.g., `("total", "ambos sexos", "total nacional", "nacional")`)
    - `query_triggers: tuple[QueryTriggerRule, ...]`
  - `FacetOntology`:
    - `get_facet(facet_key: str) -> FacetDefinition | None`
    - `all_facets() -> list[FacetDefinition]`
    - `is_critical_unhandled_facet(facet_key: str, facet_value: str) -> bool` (replaces hardcoded `if f == "etnia" or intent.facets.get(f) not in {"POBREZA_TOTAL", "TOTAL", "NACIONAL"}`)
    - `is_structural_dimension(dim_id: int, dim_name: str) -> bool` (identifies `País`, `Años`, `Trimestre`, `Mes` dimensions)
    - `classify_dimension(dim_id: int, dim_name: str) -> str | None` (returns matching `facet_key`, `"__structural__"`, or `None` if unmapped)
    - `build_dimension_key_patterns() -> dict[str, list[str]]`
    - `build_member_value_patterns() -> dict[str, list[str]]`
  - `DEFAULT_FACET_ONTOLOGY: FacetOntology` and `get_default_facet_ontology() -> FacetOntology`.

- [ ] **Step 1: Write failing tests for `FacetOntology` models, classification, and aggregate semantics**

```python
# In tests/test_semantic_facet_ontology.py
import pytest
from statscepal.semantic.facet_ontology import (
    DEFAULT_FACET_ONTOLOGY,
    FacetOntology,
    get_default_facet_ontology,
)


def test_default_facet_ontology_covers_core_facets():
    ontology = get_default_facet_ontology()
    expected_keys = {
        "sexo",
        "area",
        "edad",
        "etnia",
        "estrato",
        "quintil",
        "educacion",
        "formalidad",
        "severidad",
        "canasta",
        "rubro",
        "moneda",
        "actividad",
    }
    registered_keys = {f.facet_key for f in ontology.all_facets()}
    assert expected_keys.issubset(registered_keys)


def test_facet_ontology_implicit_aggregate_vs_critical_breakdown():
    ontology = DEFAULT_FACET_ONTOLOGY
    # Implicit national/total defaults do NOT force a breakdown swap if canonical indicator is aggregate
    assert not ontology.is_critical_unhandled_facet("area", "NACIONAL")
    assert not ontology.is_critical_unhandled_facet("severidad", "POBREZA_TOTAL")
    assert not ontology.is_critical_unhandled_facet("sexo", "TOTAL")
    assert not ontology.is_critical_unhandled_facet("sexo", "AMBOS_SEXOS")

    # Explicit breakdown values DO require the dimension (including ETNICO_TOTAL and QUINTIL)
    assert ontology.is_critical_unhandled_facet("etnia", "ETNICO_TOTAL")
    assert ontology.is_critical_unhandled_facet("etnia", "INDIGENA")
    assert ontology.is_critical_unhandled_facet("area", "RURAL")
    assert ontology.is_critical_unhandled_facet("sexo", "FEMENINO")
    assert ontology.is_critical_unhandled_facet("edad", "INFANCIA")
    assert ontology.is_critical_unhandled_facet("estrato", "QUINTIL")
    assert ontology.is_critical_unhandled_facet("educacion", "UNIVERSITARIA")


def test_facet_ontology_dimension_classification():
    ontology = DEFAULT_FACET_ONTOLOGY
    assert ontology.classify_dimension(208, "País__ESTANDAR") == "__structural__"
    assert ontology.classify_dimension(29117, "Años__ESTANDAR") == "__structural__"
    assert ontology.classify_dimension(144, "Sexo__ESTANDAR") == "sexo"
    assert ontology.classify_dimension(326, "Área geográfica") == "area"
    assert ontology.classify_dimension(43039, "Tipo de etnia") == "etnia"
    assert ontology.classify_dimension(999999, "Dimensión desconocida xyz") is None
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_semantic_facet_ontology.py`
Expected: Fails with `ModuleNotFoundError: No module named 'statscepal.semantic.facet_ontology'`.

- [ ] **Step 3: Implement `src/statscepal/semantic/facet_ontology.py`**
Create `facet_ontology.py` with `FacetDefinition`, `QueryTriggerRule`, `FacetOntology`, and `DEFAULT_FACET_ONTOLOGY` containing all canonical socioeconomic facets (`sexo`, `area`, `edad`, `etnia`, `estrato`, `quintil`, `educacion`, `formalidad`, `severidad`, `canasta`, `rubro`, `moneda`, `actividad`) and structural dimension detectors (`pais`, `anos`, `trimestre`, `mes`).

- [ ] **Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_semantic_facet_ontology.py`
Expected: 3 passed.

- [ ] **Step 5: Commit changes**
```bash
git add src/statscepal/semantic/facet_ontology.py tests/test_semantic_facet_ontology.py
git commit -m "feat(semantic): implement declarative FacetOntology models and default registry"
```

---

### Task 2: Wire `DynamicMemberMatcher` to `FacetOntology`

**Files:**
- Modify: `src/statscepal/semantic/matcher.py`
- Modify: `tests/test_semantic_facet_ontology.py`

**Interfaces:**
- Consumes: `DEFAULT_FACET_ONTOLOGY`, `FacetOntology` from `statscepal.semantic.facet_ontology`.
- Produces:
  - `DynamicMemberMatcher(ontology: FacetOntology | None = None)`
  - Backward-compatible `DIMENSION_KEY_PATTERNS` and `MEMBER_VALUE_PATTERNS` generated from `DEFAULT_FACET_ONTOLOGY`.
  - Dimension matching in `DynamicMemberMatcher.match_facets_to_dimensions()` checks both `known_dimension_ids` and `dimension_name_patterns` from `FacetOntology`.

- [ ] **Step 1: Write failing test for ontology-driven matching and known dimension ID binding**

```python
# In tests/test_semantic_facet_ontology.py
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.matcher import (
    DIMENSION_KEY_PATTERNS,
    MEMBER_VALUE_PATTERNS,
    DynamicMemberMatcher,
)


def test_matcher_derives_patterns_from_ontology_and_matches_by_dim_id():
    matcher = DynamicMemberMatcher()
    assert "etnia" in DIMENSION_KEY_PATTERNS
    assert "educacion" in DIMENSION_KEY_PATTERNS
    assert "INDIGENA" in MEMBER_VALUE_PATTERNS
    assert "FEMENINO" in MEMBER_VALUE_PATTERNS

    # Even if a dimension has a non-standard label, known_dimension_ids (e.g. 43039 for etnia) binds it in Group A
    dims = [
        Dimension(
            id=43039,
            name="Clasificación oficial CEPAL 43039",
            members=[
                Member(id=43041, name="Indígena"),
                Member(id=43043, name="Total"),
            ],
        )
    ]
    all_matched, applied, unhandled = matcher.match_facets_to_dimensions(
        3342, dims, {"etnia": "INDIGENA"}
    )
    assert all_matched is True
    assert unhandled == []
    assert len(applied) == 1
    assert applied[0].dim_id == 43039
    assert applied[0].member_id == 43041
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_semantic_facet_ontology.py -k test_matcher_derives_patterns_from_ontology_and_matches_by_dim_id`
Expected: Fails or falls into fallback group because `matcher.py` does not yet consult `known_dimension_ids` or accept `ontology`.

- [ ] **Step 3: Update `src/statscepal/semantic/matcher.py` to use `FacetOntology`**
- Populate `DIMENSION_KEY_PATTERNS` and `MEMBER_VALUE_PATTERNS` from `DEFAULT_FACET_ONTOLOGY`.
- Allow `DynamicMemberMatcher.__init__(self, ontology: FacetOntology | None = None)`.
- In `match_facets_to_dimensions`, place a dimension into `candidate_dims_a` if `d.id in facet_def.known_dimension_ids` OR `any(kp in d_name_norm for kp in key_patterns)`.

- [ ] **Step 4: Run tests to verify passing and zero regressions**
Run:
```bash
uv run pytest tests/test_semantic_facet_ontology.py tests/test_semantic_breakdowns.py -v
uv run pytest tests/test_semantic_benchmark_200.py -v
```
Expected: All pass with 100% accuracy and 0.00% FSR.

- [ ] **Step 5: Commit changes**
```bash
git add src/statscepal/semantic/matcher.py tests/test_semantic_facet_ontology.py
git commit -m "refactor(semantic): drive DynamicMemberMatcher from declarative FacetOntology"
```

---

### Task 3: Harvested Dimension Audit Engine & `statscepal catalog facet-audit` CLI

**Files:**
- Modify: `src/statscepal/catalog/store.py`
- Modify: `src/statscepal/semantic/facet_ontology.py`
- Modify: `src/statscepal/cli.py`
- Modify: `tests/test_semantic_facet_ontology.py`

**Interfaces:**
- Consumes: `CatalogStore`, `FacetOntology`.
- Produces:
  - `CatalogStore.get_distinct_harvested_dimensions() -> list[dict[str, Any]]`: returns rows with `dim_id`, `dim_name`, `indicator_count`, `sample_indicator_ids` ordered by `indicator_count DESC, dim_id ASC`.
  - `FacetOntology.audit_dimensions(dimension_rows: list[dict[str, Any]]) -> FacetAuditReport`:
    - `total_distinct_dimensions: int`
    - `structural_dimensions: list[dict[str, Any]]`
    - `mapped_dimensions: dict[str, list[dict[str, Any]]]` (grouped by `facet_key`)
    - `unmapped_dimensions: list[dict[str, Any]]`
    - `coverage_ratio: float` (ratio of mapped + structural over total distinct dimensions)
  - CLI command `statscepal catalog facet-audit [--json]`.

- [ ] **Step 1: Write failing tests for `get_distinct_harvested_dimensions`, `audit_dimensions`, and CLI `catalog facet-audit`**

```python
# In tests/test_semantic_facet_ontology.py
import json
from statscepal.catalog.store import CatalogStore
from statscepal.cli import main
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY


def test_store_and_ontology_facet_audit(tmp_path, capsys, monkeypatch):
    db_path = tmp_path / "audit_test.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    store.store_indicator_dimensions(
        3328,
        [
            Dimension(id=208, name="País__ESTANDAR", members=[Member(id=1, name="Chile")]),
            Dimension(id=326, name="Área geográfica", members=[Member(id=2, name="Urbana")]),
            Dimension(id=88888, name="Variable Experimental No Mapeada", members=[Member(id=3, name="X")]),
        ],
    )

    distinct_dims = store.get_distinct_harvested_dimensions()
    assert len(distinct_dims) == 3

    report = DEFAULT_FACET_ONTOLOGY.audit_dimensions(distinct_dims)
    assert report.total_distinct_dimensions == 3
    assert len(report.structural_dimensions) == 1
    assert "area" in report.mapped_dimensions
    assert len(report.unmapped_dimensions) == 1
    assert report.unmapped_dimensions[0]["dim_id"] == 88888

    # Test CLI invocation
    monkeypatch.setattr("statscepal.cli.CatalogStore", lambda: CatalogStore(db_path=db_path))
    exit_code = main(["catalog", "facet-audit"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "CEPALSTAT Facet Ontology Audit" in out
    assert "area" in out
    assert "Variable Experimental No Mapeada" in out
```

- [ ] **Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_semantic_facet_ontology.py -k test_store_and_ontology_facet_audit`
Expected: Fails with `AttributeError: 'CatalogStore' object has no attribute 'get_distinct_harvested_dimensions'`.

- [ ] **Step 3: Implement `get_distinct_harvested_dimensions`, `audit_dimensions`, and CLI `facet-audit`**
1. In `src/statscepal/catalog/store.py`:
   Add `get_distinct_harvested_dimensions()` querying `SELECT dim_id, dim_name, COUNT(DISTINCT indicator_id) AS indicator_count FROM indicator_dimensions GROUP BY dim_id, dim_name ORDER BY indicator_count DESC, dim_id ASC`.
2. In `src/statscepal/semantic/facet_ontology.py`:
   Add `FacetAuditReport` model and `FacetOntology.audit_dimensions(dimension_rows)`.
3. In `src/statscepal/cli.py`:
   Register `facet-audit` under `catalog_subparsers` with `--json` flag and formatted ASCII report output.

- [ ] **Step 4: Run test to verify it passes**
Run: `uv run pytest tests/test_semantic_facet_ontology.py -v`
Expected: All tests in `test_semantic_facet_ontology.py` pass.

- [ ] **Step 5: Run full non-integration and benchmark suites**
Run:
```bash
uv run pytest tests/test_semantic_benchmark_200.py -v
uv run pytest -m "not integration"
```
Expected: 100% pass, 0 regressions.

- [ ] **Step 6: Commit changes**
```bash
git add src/statscepal/catalog/store.py src/statscepal/semantic/facet_ontology.py src/statscepal/cli.py tests/test_semantic_facet_ontology.py
git commit -m "feat(semantic): add harvested dimension audit engine and 'catalog facet-audit' CLI"
```

---

## Plan Self-Review Checklist
- [x] Every acceptance criterion of Epic **E2 · Declarative Facet Ontology** is covered:
  - AC1: `src/statscepal/semantic/facet_ontology.py` with declarative models.
  - AC2: Standard socioeconomic facets (`sexo`, `area`, `etnia`, `edad`, `estrato`/`quintil`, `educacion`, `formalidad`, `severidad`, `canasta`, `rubro`, `moneda`, `actividad`).
  - AC3: Explicit aggregate/default member semantics (`implicit_aggregate_values` and `is_critical_unhandled_facet`) ready for E4 to drop the hardcoded set in `engine.py`.
  - AC4: `statscepal catalog facet-audit` CLI command reporting mapped vs. unmapped harvested dimensions.
- [x] Strict TDD steps with exact file paths, test code, and verification commands.
- [x] 100% offline hermeticity and benchmark invariants preserved.
