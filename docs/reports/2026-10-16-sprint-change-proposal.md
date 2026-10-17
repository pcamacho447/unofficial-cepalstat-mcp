# Sprint Change Proposal: Metadata Ingestion & Generic Facet Routing

- **Date:** 2026-10-16
- **Status:** Approved (Incremental Review)
- **Scope Classification:** Major (Fundamental Architectural Course Correction)
- **Initiator:** Developer Agent & User Review

---

## 1. Issue Summary

### 1.1 Context & Trigger
During the implementation of multidimensional breakdown routing (plan `semantic-multidimensional-breakdown-family-routing-plan`), the query:
```
statscepal semantic resolve "cual es la pobreza etnica en el peru del 2020"
```
originally suffered from **silent facet degradation**: because the requested ethnic facet was not handled, the engine quietly collapsed to the canonical aggregate indicator `3328` (*Pobreza por área*), fabricating an aggregate filter (`area=NACIONAL`) and reporting a false answer.

While this was resolved for poverty by manually wiring Indicator `3342` and hardcoding ethnic checks, the user noted:
> *"tenemos que tener eso planificado sino como haremos primero planteeense con bmad party mood y brainstorm como podemos cerrar ese tema no solo para pobreza sino para todos los indicadores"*

### 1.2 Core Problem Statement
The semantic engine's facet-routing mechanism depended entirely on **hand-curated indicators and ad-hoc code branches**. Specifically:
1. Only **45 out of 1,739 indicators** (2.6%) in the master catalog are registered in `VERTICAL_SLICE_INDICATORS`.
2. Only **11 indicators** (0.6%) have registered official dimensions, and only **1 indicator** supports `etnia`, `educacion`, `quintil`, or `decil`.
3. The relational metadata tables specified in [Architecture v2 (Decision 7)](file:///C:/papx/statscepal/docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md) (`indicator_dimensions`, `dimension_members`, `indicator_relationships`) were created in SQLite but **remained completely empty (0 rows)** because no automated harvesting/ingestion pipeline was executed.
4. `engine.py`, `parser.py`, and `matcher.py` had accumulated 6+ hardcoded references to `"etnia"` and explicit aggregate sets `{"POBREZA_TOTAL", "TOTAL", "NACIONAL"}`. Adding new dimensions manually scales at $O(N \times M)$ developer effort and risks codebase bloat.
5. The 200-question benchmark suite was saturated at **100.0% accuracy**, providing false confidence while failing to detect unhandled dimensional requests across the broader catalog.

---

## 2. Impact Analysis

### 2.1 Epic Impact
- **Existing Epics:** The completed vertical slice and multi-year temporal series epics remain valid and untouched.
- **New Epic Required:** **Epic `E1–E5`: Metadata Ingestion & Generic Facet Routing**.
- **Policy Invariant:** Complete freeze on adding new hand-registered facet families in `registry.py` / `engine.py` until the generic ingestion and ontology pipeline is deployed.

### 2.2 Artifact Impact
- **Architecture v2 (`specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md`):** Updated Decision 7 (automated harvester, in-memory index for 1,739 indicators with $p50 < 0.5\text{ ms}$) and Phase C roadmap.
- **Rules (`.agents/rules/semantic-resolution-guardrails.md`):** Updated to forbid hardcoded `if facet == ...` branches, enforce generic parameterization via `FacetOntology`, and require hermetic offline test suites.
- **Benchmark Spec (`specs/2026-10-15-benchmark-y-corte-vertical-spec.md`):** Introduction of the dual-benchmark strategy (Canonical 200-cases + Multidimensional Facet Coverage Suite).

### 2.3 Technical & Performance Impact
- **Database:** Local cache SQLite (`.statscepal_cache.db`) will store ~1,739 indicators, ~5,000 dimensions, and ~30,000 members.
- **Memory & Latency:** In-memory adjacency and inverted indices loaded on startup ensure local resolution stays strictly within $p50 < 0.5\text{ ms}$.
- **Network & CI:** Harvesting is a one-time/scheduled CLI command (`statscepal catalog harvest`). CI and unit tests will run 100% offline using hermetic fixtures.

---

## 3. Recommended Approach

### Selected Path: Hybrid / Direct Adjustment
- **Keep all completed work:** No rollback of the ethnic routing or temporal series implementations.
- **Direct Adjustment:** Implement the 5-stage epic (`E1–E5`) to transition from a manual 45-indicator slice to catalog-wide generic resolution.

### Action Plan (E1–E5):
1. **E1 · Dimension Metadata Harvester:** Build `statscepal catalog harvest` with resumption, backoff, and UTC content hashing to populate `indicator_dimensions` and `dimension_members`.
2. **E2 · Facet Ontology:** Create `FacetOntology` as a single declarative module mapping canonical facets to dimension patterns, member codes, and aggregate definitions.
3. **E3 · Automatic `BREAKDOWN_OF` Inference:** Algorithmically derive breakdown edges where child indicators share the parent's concept root and expand dimensions, populating `indicator_relationships` with `provenance='inferred'`.
4. **E4 · Generic Stage 4 Gate:** Refactor `engine.py`, `parser.py`, and `matcher.py` to be 100% ontology-driven with an in-memory index over the full catalog.
5. **E5 · Facet-Coverage Benchmark:** Create `tests/test_semantic_facet_coverage.py` generating $Faceta \times Familia$ test cases with an invariant of 0.00% False Substitution Rate.

---

## 4. Detailed Approved Changes

### 4.1 Epic Creation
Created `docs/superpowers/plans/2026-10-16-epic-metadata-ingestion-generic-facet-routing.md` defining tasks E1 through E5, acceptance criteria, and sequencing.

### 4.2 Architecture v2 Amendment
Updated `docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md`:
- Clarified Decision 7 for automated ingestion and in-memory compilation.
- Redefined Phase C to focus on full-catalog harvesting and generic routing.

### 4.3 Rules Amendment
Updated `.agents/rules/semantic-resolution-guardrails.md`:
- Explicit prohibition of hardcoded string literals for facets in engine logic.
- Definition of `provenance` ('curated' vs 'inferred') for graph edges.
- Enforced offline hermeticity for CI test runs.

### 4.4 Benchmark Expansion
Updated `docs/specs/2026-10-15-benchmark-y-corte-vertical-spec.md` to mandate dual benchmarking.

---

## 5. Implementation Handoff

### Scope: Major / Replan Execution
- **Lead Agent:** Developer Agent (`Amelia`) with Architectural Supervision (`Winston`).
- **Next Steps:**
  1. Author the detailed task plan for Task E1 (Dimension Metadata Harvester) using `writing-plans`.
  2. Implement `CatalogStore.harvest` and CLI command with mock fixtures.
  3. Validate against the CEPALSTAT API in staging.
