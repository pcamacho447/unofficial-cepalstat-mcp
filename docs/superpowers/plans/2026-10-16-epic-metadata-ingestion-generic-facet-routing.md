# Epic: Metadata Ingestion & Generic Facet Routing

**Goal:** Ensure every CEPALSTAT indicator's native dimensions drive facet routing automatically, so the Zero Facet Loss and 0.00% FSR invariant holds across the full catalog (~1,739 indicators), not just the 45 hand-registered ones.

**Policy Freeze:** No new hand-registered facet families in `registry.py` / `engine.py` until E1+E2 are merged.

---

## E1 · Dimension Metadata Harvester
**User Story:** As the semantic engine, I need all ~1,739 indicators' official dimensions and members stored locally in SQLite, so that resolution can inspect dimensional capabilities without network latency.

**Acceptance Criteria:**
1. Command `statscepal catalog harvest [--ids ...] [--resume] [--rate N] [--force]` connects to `/cepalstat/api/v1/indicator/{id}/dimensions` and populates `indicator_dimensions` and `dimension_members` via `CatalogStore.store_indicator_dimensions()`.
2. Harvesting is resumable: checks existing entries and skips already-harvested indicator IDs unless `--force` is passed.
3. Implements rate-limiting, exponential backoff, and robust error recovery on network drops.
4. Each record is stamped with `harvested_at` (UTC timestamp) and a `content_hash` for change detection.
5. Emits a structured harvest progress/summary report (`total`, `harvested`, `failed`, `members_count`) targeting ≥ 95% catalog coverage.
6. CI unit tests run 100% offline using captured JSON mock fixtures (`tests/fixtures/dimensions/*.json`).

---

## E2 · Declarative Facet Ontology
**User Story:** As a maintainer, I want to declare canonical facets in a single declarative configuration module instead of writing hardcoded `if-elif` checks across five different engine files.

**Acceptance Criteria:**
1. Create `src/statscepal/semantic/facet_ontology.py` with declarative data models (`FacetDefinition`, `DimensionBinding`, `MemberBinding`).
2. Declares standard socioeconomic facets:
   - `sexo`: pattern triggers, dimension pattern/IDs (144), member patterns (Mujer, Hombre, Total).
   - `area`: pattern triggers, dimension pattern/IDs (326), member patterns (Urbana, Rural, Nacional/Total).
   - `etnia`: pattern triggers, dimension pattern/IDs (43039), member patterns (Indígena, Afrodescendiente, Total).
   - `edad`: tramos etarios (Infancia, Juventud, Adulto Mayor, Total).
   - `estrato` / `quintil` / `decil`: estratos socioeconómicos y distribución.
   - `educacion`: nivel educativo alcanzado.
   - `formalidad`: empleo formal / informal.
3. Each facet definition explicitly specifies its canonical aggregate/default member semantics, eliminating the hardcoded `{"POBREZA_TOTAL", "TOTAL", "NACIONAL"}` string set in `engine.py`.
4. Provides an audit tool (`statscepal catalog facet-audit`) that reports which harvested dimensions in SQLite are mapped by the ontology and highlights unmapped dimensions.

---

## E3 · Automatic `BREAKDOWN_OF` Inference
**User Story:** As the engine, I need breakdown edges automatically discovered across all indicator families without manually entering bidirectional graph edges for hundreds of indicators.

**Acceptance Criteria:**
1. Implement relationship inference engine (`statscepal/semantic/graph_builder.py`):
   - Derives `B BREAKDOWN_OF A` when:
     1. $A$ and $B$ share a common concept root (catalog thematic path + normalized name stem + same measure/unit).
     2. $\text{dimensions}(B) \supsetneq \text{dimensions}(A)$ in terms of known facet bindings.
2. Inferred edges are written to SQLite table `indicator_relationships` with column `provenance = 'inferred'`.
3. Hand-curated edges in `VERTICAL_SLICE_INDICATORS` have `provenance = 'curated'` and strictly take precedence over inferred edges.
4. Generates an edge summary report for verification, ensuring 0 false edges on the 45 reference indicators.

---

## E4 · Generic Stage 4 Dimensional Gate
**User Story:** As an API/CLI user, any query requesting specific breakdown dimensions must be properly routed to the correct multidimensional indicator or explicitly abstained, across the entire catalog.

**Acceptance Criteria:**
1. Refactor `src/statscepal/semantic/engine.py` Stage 4 to operate entirely via `FacetOntology` and the relational graph.
2. Zero hardcoded string literals for facets (no `"etnia"` branches) in `engine.py`, `parser.py`, and `matcher.py`.
3. At startup, `MetadataRegistry` loads dimensions and relationships from SQLite into an optimized in-memory index; static Python dicts become fallback seeds only.
4. The ethnic poverty routing (`pobreza etnica` -> `3342`) and all 200 benchmark test cases continue to pass with 100.0% accuracy and 0.00% False Substitution Rate.
5. Local resolution latency maintains $p50 < 0.5\text{ ms}$ over the entire catalog in memory.

---

## E5 · Multidimensional Facet-Coverage Benchmark
**User Story:** As a maintainer, I need a benchmark that actively verifies multidimensional breakdown routing and prevents silent facet degradation across families.

**Acceptance Criteria:**
1. Create `tests/test_semantic_facet_coverage.py` generating systematic $Faceta \times Familia$ queries.
2. Covers positive test cases (supported breakdown -> conmuted indicator + correct member ID).
3. Covers negative/adversarial test cases (unsupported breakdown -> returns `ABSTAINED` with reason `UNSUPPORTED_FACET`).
4. Includes edge-case lexical stress tests (verifying boundary isolation for terms like "raza", "rama", "edad").
5. Reports per-facet precision, recall, and False Substitution Rate (mandating 0.00% FSR).

---

## Implementation Sequencing
```
[E1: Harvester] ───> [E2: Facet Ontology]
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
    [E3: Inferred Edges]       [E4: Generic Gate]
               └────────────┬────────────┘
                            ▼
              [E5: Coverage Benchmark]
```
