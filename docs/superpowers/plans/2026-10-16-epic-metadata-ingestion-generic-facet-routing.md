# Epic: Metadata Ingestion & Generic Facet Routing

**Status:** ✅ **COMPLETED & CERTIFIED** (Stages E1 through E5)  
**Lead Implementer:** Amelia (Senior Software Engineer)  
**System Architect & Reviewer:** Winston  
**Econometrician & Domain Auditor:** Raúl (CEPAL Macro-Structuralist Econometrician)  
**Target Invariant:** Zero Facet Loss and 0.00% False Substitution Rate (FSR) across the full catalog (~1,739 indicators).

---

## 1. Executive Summary & Verification Matrix

| Stage | Milestone | Status | Commits | Primary Artifacts | Key Metrics |
|---|---|:---:|---|---|---|
| **E1** | Dimension Metadata Harvester | ✅ Certified | `3a5d8b7..06cb4d4` | `store.py`, `harvester.py`, `cli.py` | 100% offline hermeticity, rate-limited, resumable harvesting |
| **E2** | Declarative Facet Ontology | ✅ Certified | `2997146..7af873b` | `facet_ontology.py`, `matcher.py` | 13 canonical facets declared, audit CLI `catalog facet-audit` |
| **E3** | Automatic `BREAKDOWN_OF` Inference | ✅ Certified | `e75ee56..2901cd8` | `graph_builder.py`, `cli.py` | Relational provenance, strict-superset inference, 0 false edges |
| **E4** | Generic Stage 4 Dimensional Gate | ✅ Certified | `baf7a40..ec78705` | `engine.py`, `registry.py`, `parser.py` | 0 hardcoded facet literals, SQLite in-memory index, AST certified |
| **E5** | Multidimensional Facet-Coverage Benchmark | ✅ Certified | `6c1f564..aa2108e` | `facet_coverage_cases.json`, `test_semantic_facet_coverage.py` | 70/70 (100.0% Top-1), 0.00% FSR, $p50 = 1.46\text{ ms}$, 278 regression tests passing |

---

## 2. Stage-by-Stage Implementation Records

### E1 · Dimension Metadata Harvester
- **User Story:** As the semantic engine, I need all ~1,739 indicators' official dimensions and members stored locally in SQLite, so that resolution can inspect dimensional capabilities without network latency.
- **Implementation Highlights:**
  - Implemented `CatalogStore.store_indicator_dimensions()` and `CatalogStore.get_indicator_dimensions()` in `src/statscepal/catalog/store.py` with tables `indicator_dimensions` and `dimension_members`.
  - Added CLI command `statscepal catalog harvest [--ids ...] [--resume] [--rate N] [--force]` in `src/statscepal/cli.py`.
  - Implemented exponential backoff and rate-limiting in `src/statscepal/catalog/harvester.py`.
  - Offline CI tests run with hermetic JSON fixtures in `tests/fixtures/dimensions/`.
- **Commits:** `3a5d8b7..06cb4d4`
- **Plan Reference:** [`2026-10-16-task-e1-dimension-metadata-harvester-plan.md`](2026-10-16-task-e1-dimension-metadata-harvester-plan.md)

---

### E2 · Declarative Facet Ontology
- **User Story:** As a maintainer, I want to declare canonical facets in a single declarative configuration module instead of writing hardcoded `if-elif` checks across five different engine files.
- **Implementation Highlights:**
  - Created declarative Pydantic models `FacetDefinition`, `QueryTriggerRule`, `MemberPatternRule`, `FacetAuditReport`, and `FacetOntology` in `src/statscepal/semantic/facet_ontology.py`.
  - Declared all 13 canonical facets: `etnia`, `sexo`, `area`, `severidad`, `edad`, `quintil`, `estrato`, `educacion`, `formalidad`, `canasta`, `rubro`, `moneda`, `actividad`.
  - Integrated `FacetOntology` into `DynamicMemberMatcher` (`src/statscepal/semantic/matcher.py`), eliminating static pattern dictionaries.
  - Added diagnostic CLI subcommand `statscepal catalog facet-audit [--json]` in `src/statscepal/cli.py` evaluating harvested dimension coverage.
- **Commits:** `2997146..7af873b`
- **Plan Reference:** [`2026-10-16-task-e2-declarative-facet-ontology-plan.md`](2026-10-16-task-e2-declarative-facet-ontology-plan.md)

---

### E3 · Automatic `BREAKDOWN_OF` Inference
- **User Story:** As the engine, I need breakdown edges automatically discovered across all indicator families without manually entering bidirectional graph edges for hundreds of indicators.
- **Implementation Highlights:**
  - Extended SQLite table `indicator_relationships` with column `provenance TEXT DEFAULT 'curated'` and non-destructive PRAGMA migration in `src/statscepal/catalog/store.py`. Curated edges strictly take precedence over inferred edges.
  - Implemented `GraphBuilder` (`src/statscepal/semantic/graph_builder.py`) with canonical stem normalization (`extract_name_stem`), facet classification via `FacetOntology`, strict-superset breakdown inference ($F_{\text{child}} \supsetneq F_{\text{parent}}$), and measure/unit compatibility guardrails.
  - Zero false edges verified on curated reference indicators (`false_curated_edges == 0`).
  - Added CLI command `statscepal catalog build-graph [--no-persist] [--no-seed-curated] [--json]` in `src/statscepal/cli.py`.
- **Commits:** `e75ee56..2901cd8`
- **Plan Reference:** [`2026-10-16-task-e3-automatic-breakdown-inference-plan.md`](2026-10-16-task-e3-automatic-breakdown-inference-plan.md)

---

### E4 · Generic Stage 4 Dimensional Gate
- **User Story:** As an API/CLI user, any query requesting specific breakdown dimensions must be properly routed to the correct multidimensional indicator or explicitly abstained, across the entire catalog.
- **Implementation Highlights:**
  - Delegated query facet extraction in `QueryParser` to `FacetOntology.extract_facets_from_query()`, eliminating the hardcoded `facets["etnia"]` block.
  - Added bulk loaders `get_all_indicator_dimensions()`, `get_all_indicator_metadata()`, and `get_all_master_indicators()` in `CatalogStore`.
  - Refactored `SemanticRegistry` to construct fast in-memory caches (`_indicators_cache`, `_dimensions_cache`, `_relationships_cache`) from fallback seeds overlaid with SQLite catalog data, with automatic metadata and supported-facets synthesis for uncurated indicators.
  - Refactored Stage 4 in `SemanticResolutionEngine.resolve` to operate generically via `self.ontology.is_critical_unhandled_facet()`, `self.registry.get_supported_facets()`, and `self.registry.get_relationships()`.
  - **Zero Hardcoded Literals:** Eradicated all `"etnia"`, `POBREZA_TOTAL`, `3342`, and `DEFAULT_OFFICIAL_DIMENSIONS` literals from `engine.py`, verified permanently by AST source inspection tests.
- **Commits:** `baf7a40..ec78705`
- **Plan Reference:** [`2026-10-16-task-e4-generic-stage4-dimensional-gate-plan.md`](2026-10-16-task-e4-generic-stage4-dimensional-gate-plan.md)

---

### E5 · Multidimensional Facet-Coverage Benchmark
- **User Story:** As a maintainer, I need a benchmark that actively verifies multidimensional breakdown routing and prevents silent facet degradation across families.
- **Implementation Highlights:**
  - Created systematic benchmark dataset `tests/benchmark/facet_coverage_cases.json` with 70 curated cases across all 13 canonical facets and 16 socioeconomic families (27 positive breakdowns, 27 adversarial abstentions, 16 boundary isolations).
  - Implemented lexical boundary isolation suite in `tests/test_semantic_facet_coverage.py` verifying strict word boundary isolation (`\b`) for words like `"razón"` vs `"raza"`, `"panorama"`/`"programa"` vs `"rama"`, `"sociedad"` vs `"edad"`, `"línea aérea"` vs `"área"`, and `"nexo"` vs `"sexo"`.
  - Verified root concept protection for composite domain queries (e.g. `"gasto público en educación"` -> `GASTO_EDUCACION`, ID 4406).
  - Implemented automated evaluation harness, latency measurement ($p50 < 2.0\text{ ms}$), per-facet health test, and clean ASCII summary table.
- **Commits:** `6c1f564..aa2108e`
- **Plan Reference:** [`2026-10-16-task-e5-multidimensional-facet-coverage-benchmark-plan.md`](2026-10-16-task-e5-multidimensional-facet-coverage-benchmark-plan.md)

---

## 3. Architecture Lifecycle & Invariant Verification

```
┌─────────────────────────────────────────────────────────────┐
│                      QUERY INGESTION                        │
│  QueryParser -> FacetOntology.extract_facets_from_query()   │
│  (Strict word-boundary matching, zero hardcoded facets)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               STAGE 4: GENERIC DIMENSIONAL GATE             │
│  1. Unhandled Facets = requested - registry.supported_facets│
│  2. Filter by ontology.is_critical_unhandled_facet()        │
│  3. Traverse registry.get_relationships(BREAKDOWN_OF)       │
│  4. DynamicMemberMatcher binds concrete dim_id & member_id  │
│  5. Honest Abstention (UNSUPPORTED_FACET) if no valid swap  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    OFFLINE VERIFICATION                     │
│  - 200/200 Benchmark (100.0% Top-1, 0.00% FSR, p50=0.98 ms)│
│  - 70/70 Facet Coverage (100.0% Top-1, 0.00% FSR, p50=1.46) │
│  - 278/278 Full Regression Suite Passing Cleanly            │
└─────────────────────────────────────────────────────────────┘
```

The epic is completed and certified for production usage.
