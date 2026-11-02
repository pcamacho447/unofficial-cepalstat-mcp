# Declarative Concept Ontology Specification (Phase 5)

**Date:** 2026-11-02  
**Status:** Approved  
**Scope:** `src/unofficial_cepalstat_mcp/semantic/concept_ontology.py`, `src/unofficial_cepalstat_mcp/semantic/parser.py`, `tests/`  

---

## 1. Context & Motivation

In previous phases, the CEPALSTAT Semantic Resolution Engine achieved:
- Real canonical catalog indicator alignment with automated multi-dimensional graph switching (`BREAKDOWN_OF`).
- Declarative facet extraction via [`FacetOntology`](file:///home/jorge/projects/unofficial-cepalstat-mcp/src/unofficial_cepalstat_mcp/semantic/facet_ontology.py).
- Non-interpolation with empirical anchor points (`RESOLVED_WITH_ANCHORS`).
- Measure modifier protection, non-LAC geographic abstention diagnostics, typo suggestions ("¿Quisiste decir...?"), and Tier-2 BM25 length damping.

However, root concept extraction in [`QueryParser`](file:///home/jorge/projects/unofficial-cepalstat-mcp/src/unofficial_cepalstat_mcp/semantic/parser.py) remains an procedural 580-line chain of `if / elif` statements (lines 780 to 1360). Adding a regionalism or a new socioeconomic concept (e.g., "PBI", "presión fiscal", "empleo formal") currently requires manually editing procedural parser code in multiple places rather than updating a structured declarative registry.

This violates architectural principle #15 and convention #3 in [`AGENTS.md`](file:///home/jorge/projects/unofficial-cepalstat-mcp/AGENTS.md), which proscribes hardcoded `if == "..."` branching in favor of declarative ontologies.

---

## 2. Architectural Objectives

1. **Declarative Concept Definitions (`ConceptDefinition`):**
   Model each CEPALSTAT socioeconomic concept (e.g. `POBREZA`, `PIB`, `EMPLEO`, `GINI`, `SALARIO_REAL`, `IPC_GENERAL`, `DEUDA_PUBLICA`, `BALANCE_PRIMARIO`, `INGRESOS_TRIBUTARIOS`, `GASTO_SOCIAL`, `GASTO_EDUCACION`, `BALANZA_COMERCIAL`, `CUENTA_CORRIENTE`, `INVERSION_EXTRANJERA_DIRECTA`, `TERMINOS_INTERCAMBIO`, `EMISIONES_GEI_LULUCF`, `EMISIONES_GEI_SIN_LULUCF`, `ENERGIA_RENOVABLE`, `AGUA_DULCE`, `POBLACION`, `BRECHA_SALARIAL`) as a declarative Pydantic data structure containing:
   - `concept_key`: Canonical identifier (matching `OFFICIAL_25_CANONICAL_DEFAULTS`).
   - `domain`: Broad macroeconomic / social area (`pobreza`, `macro`, `laboral`, `precios`, `fiscal`, `externo`, `ambiental`, `demografia`).
   - `priority`: Matching precedence (e.g. `DEUDA_PUBLICA` [150] before `PIB` [100] so `"deuda como % del PIB"` resolves to `DEUDA_PUBLICA`).
   - `triggers`: Direct triggers (phrases or regexes) with word-boundary enforcement.
   - `controlled_ambiguities`: Mappings from vague expressions to ambiguous candidates (e.g. `"actividad economica" -> "ECONOMIC_ACTIVITY"`, `"economia de" -> "MACRO_ECONOMY"`).
   - `sub_concept_rules`: Declarative conditions to resolve sub-concepts based on qualifying sub-phrases (e.g. `INGRESOS_TRIBUTARIOS_CORRIENTES` when `"moneda nacional"` or `"precios corrientes"` is present; `EMISIONES_GEI_SIN_LULUCF` when `"sin lulucf"` is present).
   - `default_facets`: Implied default facet mappings (e.g. `{"area": "NACIONAL"}` for `POBREZA`).

2. **Decoupled Engine (`ConceptOntology`):**
   - Precompiles all patterns into an indexed, priority-ordered matching pipeline.
   - Provides `extract_concept(clean_query: str, thesaurus: Thesaurus | None, facets: dict[str, str]) -> ConceptMatchResult | None`.
   - Executes with zero allocations in the hot path, preserving $p50 < 0.5\text{ ms}$ latency budget.

3. **Lean `QueryParser` Refactor:**
   - Delegate root concept resolution from `QueryParser.parse()` to `self.concept_ontology.extract_concept(...)`.
   - Reduce `parser.py` by over 500 lines of procedural branching without altering any parsing semantics.

---

## 3. Invariants & Verification

- **0.00% False Substitution Rate (FSR):** Zero change in resolution outcomes across all 390 certified benchmark queries (200 canonical, 40 adversarial, 100 catalog scale, 50 hold-out).
- **100% Mutation Divergence:** All 8 mutation tests in `tests/test_semantic_mutations.py` must pass.
- **Strict Latency Budget:** Local resolution latency must remain $p50 < 0.5\text{ ms}$ and $p95 < 2.0\text{ ms}$.
- **Zero Static Typing Errors:** `uv run mypy src/unofficial_cepalstat_mcp/` must return 0 errors.
- **Clean Linting:** `uv run ruff check .` must pass completely.
