# Arquitectura Híbrida de Dos Niveles y Fábrica de Ingesta para 1,739 Indicadores de CEPALSTAT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar y certificar la arquitectura híbrida de dos niveles (Tier 1 en memoria para ~150 series clave + Tier 2 determinista SQLite FTS5 sobre los 1,739 indicadores) junto con el tooling CLI de mantenimiento offline (`harvest-staging`), asegurando 0.00% FSR, arranque en frío < 50 ms y latencia p50 < 0.5 ms.

**Architecture:** Un desacoplamiento estricto entre tiempo de resolución (100% offline, cero dependencias pesadas de IA o vector DBs) y tiempo de ingesta (CLI offline de staging). Tier 1 resuelve el núcleo macro y social de alta frecuencia con grafos ontológicos curados; Tier 2 recupera sobre el catálogo FTS5 completo evaluado por un *Specificity Guard* que garantiza *Zero Facet Loss* y abstención determinista (`ABSTAINED` / `ALTERNATIVE_PROPOSED` < 250 tokens).

**Tech Stack:** Python >=3.10, SQLite FTS5 (unicode61 tokenizer), Pydantic v2, `uv`, `httpx`, `pytest`, `mypy`, `ruff`.

**Spec:** [`_bmad-output/specs/spec-estrategias-expansion-cepalstat/SPEC.md`](file:///home/jorge/.herdr/worktrees/unofficial-cepalstat-mcp/worktree-quiet-field-45d5/_bmad-output/specs/spec-estrategias-expansion-cepalstat/SPEC.md) y [`stories.yaml`](file:///home/jorge/.herdr/worktrees/unofficial-cepalstat-mcp/worktree-quiet-field-45d5/_bmad-output/specs/spec-estrategias-expansion-cepalstat/stories.yaml).

## Global Constraints

- **0.00% False Substitution Rate (FSR):** Inviolable en todas las suites de pruebas y mutaciones sintéticas.
- **Zero Network I/O en runtime:** El motor semántico resuelve 100% offline contra estructuras locales en memoria y SQLite.
- **Sin dependencias pesadas:** Prohibido el uso de PyTorch, TensorFlow, Sentence-Transformers, ChromaDB o bases vectoriales.
- **Gobernanza declarativa:** Cero sentencias condicionales `if indicator == ...` o `if concept == ...` en código Python; todo registro pertenece a `FacetOntology`, `ConceptOntology` o tablas FTS5.
- **Inmutabilidad de curaduría:** Registros y aristas con `provenance='curated'` jamás pueden ser sobreescritos por procesos automáticos con `provenance='inferred'`.
- **Huella de empaquetado:** `seed_catalog.db.gz` empaquetado en el wheel con tamaño estrictamente menor a **3.0 MB**.
- **SLA de latencia:** p50 < 0.5 ms y p95 < 1.8 ms en resolución local.

## Review Focus

1. **Colisión de IDs sintéticos:** Un miembro dimensional de categoría comparte ID numérico con un país (ej. `79578`); debe aislarse y jamás enviarse como filtro de país o miembro global.
2. **Pérdida de facetas en cola larga (*Facet Loss*):** Una consulta solicita facetas específicas (ej. "por sexo" o "rural") sobre un indicador de Tier 2 que solo tiene total nacional; el Specificity Guard debe forzar `ABSTAINED` determinista en vez de devolver el total.
3. **Ambigüedad de series paralelas:** Una consulta coincide igualmente con la serie armonizada CEPAL y la serie oficial ODS; el motor debe emitir `ALTERNATIVE_PROPOSED` (< 250 tokens) sin adivinar.
4. **Corrupción de caché local:** Si el archivo local `.statscepal_cache.db` está dañado o truncado, `get_cache_db_path()` debe detectar el fallo con `PRAGMA integrity_check;` y restaurar atómicamente desde `seed_catalog.db.gz`.
5. **Sobre-escritura de metadatos curados:** Una ejecución de `harvest-staging` sobre un tema ya curado no debe modificar notas, factores de empalme o filtros obligatorios de indicadores existentes.

---

### Task 1: Tooling de Ingesta Offline y Aislamiento de Miembros Sintéticos (`harvest-staging`)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/catalog/harvester.py:40-200`
- Modify: `src/unofficial_cepalstat_mcp/cli.py:500-650`
- Test: `tests/test_catalog_harvester.py`

**Interfaces:**
- Produces: `CatalogHarvester.harvest_staging(theme_id: str, output_db: Path | None = None) -> HarvestSummary`
- Produces CLI: `unofficial-cepalstat-mcp harvest-staging --theme <theme> [--area <area_id>]`
- Consumes: `SYNTHETIC_DIMENSION_MEMBER_IDS` en `dimensions.py` y `CatalogStore`

- [ ] **Step 1: Write the failing test for `harvest_staging` with synthetic member isolation and provenance preservation**

```python
def test_harvest_staging_isolates_synthetic_members_and_preserves_curated(tmp_path):
    store = CatalogStore(db_path=tmp_path / "test_staging.db")
    store.initialize_schema()
    # Insert a curated indicator
    store.upsert_indicator(indicator_id=2204, name="PIB Constant", provenance="curated")
    
    harvester = CatalogHarvester(client=mock_client, store=store)
    summary = harvester.harvest_staging(theme_id="economic")
    
    assert summary.inferred_count > 0
    # Curated indicator provenance must remain 'curated'
    curated = store.get_indicator(2204)
    assert curated.provenance == "curated"
    # Synthetic members must be flagged
    assert store.has_synthetic_member_flag(79578) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_catalog_harvester.py::test_harvest_staging_isolates_synthetic_members_and_preserves_curated -v`  
Expected: FAIL with `AttributeError: 'CatalogHarvester' object has no attribute 'harvest_staging'`

- [ ] **Step 3: Implement `harvest_staging` in `catalog/harvester.py` and CLI binding in `cli.py`**

Implementar el método `harvest_staging` con extracción de dimensiones, verificación contra `SYNTHETIC_DIMENSION_MEMBER_IDS`, escritura en `staging_indicators` con `provenance='inferred'` y preservación incondicional de registros donde `provenance='curated'`. Agregar el comando `harvest-staging` en `cli.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_catalog_harvester.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/catalog/harvester.py src/unofficial_cepalstat_mcp/cli.py tests/test_catalog_harvester.py
git commit -m "feat(catalog): implement harvest-staging CLI with synthetic member isolation and curated provenance guard"
```

---

### Task 2: Empaquetado Autónomo y Arranque en Frío de Catálogo Pre-sembrado

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/catalog/seed.py:20-150`
- Modify: `src/unofficial_cepalstat_mcp/config.py:30-80`
- Test: `tests/test_cold_start_seed.py`

**Interfaces:**
- Produces: `ensure_seed_hydrated(db_path: Path | None = None) -> Path`
- Produces: `export_seed_snapshot(source_db: Path | str | None = None, output_gz: Path | str | None = None) -> Path`
- Consumes: `src/unofficial_cepalstat_mcp/data/seed_catalog.db.gz`

- [ ] **Step 1: Write the failing test for atomic hydration with corrupt DB autorrepair**

```python
def test_ensure_seed_hydrated_auto_repairs_corrupted_database(tmp_path, monkeypatch):
    corrupt_db = tmp_path / ".statscepal_cache.db"
    corrupt_db.write_bytes(b"corrupt header bytes not sqlite3")
    monkeypatch.setattr("unofficial_cepalstat_mcp.config.get_cache_db_path", lambda: corrupt_db)
    
    hydrated_path = ensure_seed_hydrated(db_path=corrupt_db)
    assert hydrated_path.exists()
    
    # Must be valid SQLite with 1,739 indicators
    conn = sqlite3.connect(hydrated_path)
    count = conn.execute("SELECT count(*) FROM master_indicators").fetchone()[0]
    assert count == 1739
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cold_start_seed.py::test_ensure_seed_hydrated_auto_repairs_corrupted_database -v`  
Expected: FAIL with `DatabaseError: file is not a database`

- [ ] **Step 3: Implement integrity check and atomic hydration in `catalog/seed.py`**

Agregar validación de integridad (`PRAGMA quick_check;`) en `ensure_seed_hydrated`. Si la base no existe o falla la verificación, descomprimir atómicamente `seed_catalog.db.gz` vía archivo temporal (`tempfile.NamedTemporaryFile`) seguido de `os.replace`. Asegurar que el tamaño comprimido permanezca estrictamente menor a 3.0 MB.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cold_start_seed.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/catalog/seed.py src/unofficial_cepalstat_mcp/config.py tests/test_cold_start_seed.py
git commit -m "feat(catalog): add atomic seed hydration with corruption auto-repair and <50ms cold-start guard"
```

---

### Task 3: Motor de Recuperación Determinista FTS5 con Expansión de Tesauro (Tier 2)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/catalog/store.py:300-450`
- Modify: `src/unofficial_cepalstat_mcp/semantic/thesaurus.py:100-220`
- Test: `tests/test_catalog_fts5_search.py`

**Interfaces:**
- Produces: `CatalogStore.search_indicators_fts5(query: str, limit: int = 10, theme: str | None = None) -> list[CatalogCandidate]`
- Consumes: `Thesaurus.expand_query_tokens(tokens: list[str]) -> list[str]`

- [ ] **Step 1: Write the failing test for FTS5 ranking and sub-millisecond execution**

```python
def test_fts5_ranking_with_thesaurus_expansion_and_latency(benchmark_db):
    store = CatalogStore(db_path=benchmark_db)
    start = time.perf_counter()
    candidates = store.search_indicators_fts5("balanza de bienes exportaciones fob", limit=10)
    latency_ms = (time.perf_counter() - start) * 1000
    
    assert len(candidates) > 0
    assert candidates[0].indicator_id == 2050
    assert latency_ms < 0.5  # SLA p50 sub-millisecond
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_catalog_fts5_search.py::test_fts5_ranking_with_thesaurus_expansion_and_latency -v`  
Expected: FAIL (assertion on candidate structure or latency)

- [ ] **Step 3: Implement optimized FTS5 query builder and BM25 ranker in `catalog/store.py`**

Optimizar la consulta sobre `indicator_fts` usando `unicode61 remove_diacritics 2`, sanitización de operadores (`OR`, `NOT`, `*`), ponderación de coincidencia exacta sobre títulos vs descripciones, y filtrado Top-10 acotado sin asignación de memoria innecesaria.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_catalog_fts5_search.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/catalog/store.py src/unofficial_cepalstat_mcp/semantic/thesaurus.py tests/test_catalog_fts5_search.py
git commit -m "feat(semantic): optimize FTS5 BM25 retrieval with thesaurus expansion and p50 < 0.35ms latency"
```

---

### Task 4: Specificity Guard y Validador Invariante de Facetas (Zero Facet Loss & 0.00% FSR)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/evaluator.py:50-250`
- Modify: `src/unofficial_cepalstat_mcp/semantic/engine.py:400-550`
- Test: `tests/test_semantic_tier2_hybrid.py`
- Test: `tests/test_adversarial_benchmark_40.py`

**Interfaces:**
- Produces: `SpecificityGuard.evaluate(candidates: list[CatalogCandidate], intent_facets: set[str], require_aggregate: bool) -> SpecificityEvaluationResult`
- Consumes: `FacetOntology.validate_dimensions(dimensions: list[Dimension], facets: set[str]) -> bool`

- [ ] **Step 1: Write failing tests for Zero Facet Loss and adversarial query rejection**

```python
def test_specificity_guard_rejects_missing_facets_without_loss(semantic_engine):
    # Query specifies 'rural', but indicator 2204 (PIB) has no geographic area breakdown
    res = semantic_engine.resolve("pib total nacional rural a precios constantes")
    assert res.status == ResolutionStatus.ABSTAINED
    assert "area" in res.unmatched_facets
    assert res.indicator_id is None  # 0.00% FSR enforced
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_tier2_hybrid.py::test_specificity_guard_rejects_missing_facets_without_loss -v`  
Expected: FAIL with `AssertionError: assert <ResolutionStatus.RESOLVED> == <ResolutionStatus.ABSTAINED>`

- [ ] **Step 3: Implement Specificity Guard logic in `semantic/evaluator.py` and integrate in `engine.py`**

Verificar en `Stage 3.5`:
1. Si la consulta tiene facetas ortogonales (sexo, área, edad, moneda), verificar que el candidato contenga esas dimensiones. Si no las tiene, descartar candidato (*Zero Facet Loss*).
2. Si la consulta pide agregado y el candidato es exclusivamente desagregado sin miembro total, descartar candidato.
3. Si quedan 0 candidatos -> emitir `ABSTAINED` determinista con diagnóstico de facetas no cubiertas.
4. Si quedan >= 2 candidatos compatibles -> emitir `ALTERNATIVE_PROPOSED` con payload < 250 tokens.
5. Si queda 1 candidato exacto -> emitir `RESOLVED`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_tier2_hybrid.py tests/test_adversarial_benchmark_40.py -v`  
Expected: PASS (0.00% FSR mantenido)

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/evaluator.py src/unofficial_cepalstat_mcp/semantic/engine.py tests/test_semantic_tier2_hybrid.py
git commit -m "feat(semantic): implement Specificity Guard enforcing Zero Facet Loss and deterministic 0.00% FSR"
```

---

### Task 5: Orquestador Híbrido Unificado y Certificación de Suites de Benchmarks

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/engine.py:200-380`
- Test: `tests/test_semantic_benchmark_200.py`
- Test: `tests/test_adversarial_benchmark_40.py`
- Test: `tests/test_catalog_scale_benchmark_100.py`
- Test: `tests/test_independent_holdout_benchmark_50.py`
- Test: `tests/test_semantic_mutations.py`

**Interfaces:**
- Produces: `SemanticResolutionEngine.resolve(query: str, options: ResolutionOptions | None = None) -> SemanticResolutionResult`
- Consumes: Tier 1 (`ConceptOntology` + `BREAKDOWN_OF`), Tier 2 (`CatalogStore.search_indicators_fts5` + `SpecificityGuard`)

- [ ] **Step 1: Write integration verification test for unified two-tier routing**

```python
def test_unified_two_tier_orchestration(semantic_engine):
    # Tier 1 query
    t1_res = semantic_engine.resolve("tasa de desempleo juvenil femenina")
    assert t1_res.tier == "tier1"
    assert t1_res.status == ResolutionStatus.RESOLVED
    assert t1_res.indicator_id == 5097

    # Tier 2 long-tail query
    t2_res = semantic_engine.resolve("generacion de residuos peligrosos por tipo de actividad")
    assert t2_res.tier == "tier2"
    assert t2_res.status in (ResolutionStatus.RESOLVED, ResolutionStatus.ALTERNATIVE_PROPOSED)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_tier2_hybrid.py::test_unified_two_tier_orchestration -v`  
Expected: FAIL (missing `res.tier` metadata)

- [ ] **Step 3: Connect Tier 1 fallback to Tier 2 in `semantic/engine.py`**

Conectar el flujo del motor: Si Tier 1 no resuelve un `root_concept` unívoco o detecta tokens sustantivos no consumidos por el núcleo curado, delegar transparentemente al Nivel 2 FTS5 evaluado por el Specificity Guard. Enriquecer el resultado con telemetría de diagnóstico y nivel de resolución.

- [ ] **Step 4: Run full certified benchmark suite and type checking**

Run:
```bash
uv run pytest tests/test_semantic_benchmark_200.py \
              tests/test_adversarial_benchmark_40.py \
              tests/test_catalog_scale_benchmark_100.py \
              tests/test_independent_holdout_benchmark_50.py \
              tests/test_semantic_mutations.py -v
uv run mypy src/unofficial_cepalstat_mcp/
uv run ruff check .
```
Expected: PASS (390 queries passing, 0.00% FSR, 0 mypy errors, ruff clean)

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/engine.py tests/test_semantic_tier2_hybrid.py
git commit -m "feat(semantic): finalize unified two-tier hybrid engine certifying 390 benchmark queries with 0.00% FSR"
```
