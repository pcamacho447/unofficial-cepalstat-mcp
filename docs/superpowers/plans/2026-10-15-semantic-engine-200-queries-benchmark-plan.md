# Benchmark de 200 Preguntas Empíricas del Motor Semántico CEPALSTAT - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar, ejecutar y documentar una batería masiva de 200 preguntas empíricas en lenguaje natural (10 clusters temáticos $\times$ 20 preguntas) sobre el motor semántico de CEPALSTAT, garantizando $\ge 98.0\%$ Top-1 Accuracy, $0.0\%$ False Substitution Rate y latencia $p50 < 2.0\text{ ms}$.

**Architecture:** El sistema amplía el catálogo semántico en SQLite (`CatalogStore`) a 25 indicadores oficiales de CEPALSTAT, expande el parser léxico (`QueryParser`) con desarmadores de modificadores contextuales para jergas complejas (desambiguación de *"guita"*, *"plata"*, *"pega"*, *"chamba"*), compila un benchmark JSON de 200 casos rigurosos con matriz de cobertura 8-4-4-2-2 por cluster, y ejecuta la suite automatizada con emisión de trazas de auditoría paso a paso (`execution_trace`).

**Tech Stack:** Python 3.10+, SQLite3 relacional, Pydantic v2, pytest, uv, CEPALSTAT REST API.

**Spec:** [`docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md`](file:///C:/papx/statscepal/docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md) y [`docs/specs/2026-10-15-guia-verificacion-y-trazabilidad-motor-semantico.md`](file:///C:/papx/statscepal/docs/specs/2026-10-15-guia-verificacion-y-trazabilidad-motor-semantico.md).

## Global Constraints

- Python 3.10+ modern typing syntax (`int | None`, `dict[str, Any]`).
- All 166 existing non-integration tests must remain passing without regression.
- False Substitution Rate must strictly equal 0.0% (no untyped indicator swaps).
- Top-1 Accuracy across the 200 benchmark test cases must be >= 98.0% (target 100.0%).
- Zero filter invention: unknown facets or non-statistical terms must trigger `ABSTAINED` with `UNSUPPORTED_FACET`.
- Local resolution latency over SQLite must maintain p50 < 2.0 ms.
- Safe UTF-8 encoding for Windows console environments (`cp1252` protection).

---

## File Structure & Responsibilities

| File | Responsibility |
| :--- | :--- |
| `src/statscepal/semantic/registry.py` | Registro de los 25 indicadores oficiales canónicos y multidimensionales con sus medidas, periodicidades y relaciones tipadas en memoria y SQLite. |
| `src/statscepal/catalog/store.py` | Persistencia relacional de dimensiones, miembros y relaciones tipadas (`breakdown_of`, `measures`, `alternative_measure`) en SQLite. |
| `src/statscepal/semantic/parser.py` | Normalización léxica, detección de modismos latinoamericanos y desarmador de modificadores de contexto para desambiguar ingresos (*"guita"*, *"plata"*, *"sueldo"*). |
| `src/statscepal/semantic/engine.py` | Pipeline de 5 etapas deterministas: parsing, abstención dura, ranking canónico, compuerta dimensional y auditoría temporal. |
| `tests/benchmark/semantic_benchmark_cases_200.json` | Dataset estandarizado de las 200 preguntas (10 clusters $\times$ 20 casos) con metadatos de validación esperados. |
| `tests/test_semantic_benchmark_200.py` | Test suite automatizado de regresión que evalúa los 200 casos, mide exactitud, tasa de falsa sustitución y latencia p50. |
| `docs/specs/2026-10-15-benchmark-200-preguntas-motor-semantico.md` | Documento formal de reporte técnico con análisis de cada cluster, matrices de confusión y trazas de auditoría. |

---

### Task 1: Expand Metadata Registry & SQLite Store for 200-Question Indicators

**Files:**
- Modify: `src/statscepal/semantic/registry.py`
- Modify: `src/statscepal/catalog/store.py`
- Test: `tests/test_semantic_registry_200.py`

**Interfaces:**
- Consumes: `CatalogStore`, `IndicatorMetadata`, `DimensionMetadata`, `TypedRelationship`
- Produces: Registro completo de 25 indicadores oficiales de CEPALSTAT:
  - C1/C2 (Pobreza y Desigualdad): 3328 (Pobreza nacional/área), 3341 (Pobreza multidimensional sexo/edad/área), 3329 (Brecha de pobreza), 3330 (Índice de feminidad), 3340 (Distribución del ingreso deciles/quintiles/Gini).
  - C3/C4 (Mercado Laboral y Salarios): 127 (Desocupación por sexo), 3331 (Desempleo juvenil), 128 (Índice salario medio real), 3337 (Salario mínimo real), 3339 (Ingreso laboral medio por sexo/área), 3345 (Ingreso medio per cápita del hogar).
  - C5/C6 (Macroeconomía y Precios): 729 (PIB total), 730 (PIB per cápita), 731 (PIB trimestral), 2928 (IPC general), 2929 (IPC alimentos y bebidas), 2930 (IPC transporte y energía).
  - C7/C8 (Sector Público y Externo): 1240 (Deuda pública % PIB), 1241 (Balance primario % PIB), 1242 (Ingresos tributarios % PIB), 1243 (Cuenta corriente % PIB), 1244 (Términos de intercambio).
  - C9/C10 (Medio Ambiente y Energía): 5681 (GEI total con LULUCF), 5682 (GEI sin LULUCF), 5683 (Generación eléctrica renovable % total).

- [ ] **Step 1: Write failing test for new indicators and typed relationships**

```python
# tests/test_semantic_registry_200.py
import pytest
from statscepal.catalog.store import CatalogStore
from statscepal.semantic.registry import SemanticRegistry


def test_registry_contains_all_25_indicators(tmp_path):
    db_path = tmp_path / "test_catalog.db"
    store = CatalogStore(db_path)
    registry = SemanticRegistry(store=store)

    expected_ids = [
        3328, 3341, 3329, 3330, 3340,  # Poverty & Inequality
        127, 3331, 128, 3337, 3339, 3345,  # Labor & Wages
        729, 730, 731, 2928, 2929, 2930,  # Macro & Prices
        1240, 1241, 1242, 1243, 1244,  # Fiscal & External
        5681, 5682, 5683,  # Environment
    ]
    for ind_id in expected_ids:
        ind = registry.get_indicator(ind_id)
        assert ind is not None, f"Indicator {ind_id} missing from registry"

    # Verify typed relationships
    swaps_3328 = registry.get_target_indicators(3328, "breakdown_of")
    assert 3341 in swaps_3328

    alts_poverty = registry.get_target_indicators(3341, "alternative_measure")
    assert 3330 in alts_poverty

    swaps_salary = registry.get_target_indicators(128, "breakdown_of")
    assert 3339 in swaps_salary
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_registry_200.py`
Expected: FAIL (missing new indicators 3329, 3345, 1241, 1244, 5683, etc.)

- [ ] **Step 3: Enrich `SemanticRegistry` and `CatalogStore` with 25 official indicators**

Implement metadata registration, dimensions, and relationships in `src/statscepal/semantic/registry.py` and `src/statscepal/catalog/store.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_registry_200.py`
Expected: PASS

- [ ] **Step 5: Run existing non-integration test suite to verify zero regressions**

Run: `uv run pytest -m "not integration"`
Expected: 167+ passed.

- [ ] **Step 6: Commit changes**

```bash
git add src/statscepal/semantic/registry.py src/statscepal/catalog/store.py tests/test_semantic_registry_200.py
git commit -m "feat(semantic): register 25 official indicators and relationships for 200-question suite"
```

---

### Task 2: Build the 200-Question Empirical Benchmark Dataset (`semantic_benchmark_cases_200.json`)

**Files:**
- Create: `tests/benchmark/semantic_benchmark_cases_200.json`
- Test: `tests/test_benchmark_dataset_integrity.py`

**Interfaces:**
- Consumes: Schema de casos benchmark (`query`, `expected_indicator_id`, `expected_status`, `expected_facets`, `expected_reason`, `expected_alternatives`, `cluster`, `difficulty`)
- Produces: 200 test cases structured across 10 clusters of 20 questions with the 8-4-4-2-2 coverage matrix:
  - C1: Pobreza y Pobreza Extrema (`SE-001` - `SE-020`)
  - C2: Desigualdad y Distribución del Ingreso (`SE-021` - `SE-040`)
  - C3: Mercado Laboral y Desempleo (`SE-041` - `SE-060`)
  - C4: Salarios, Remuneraciones y Desambiguación de "Guita" (`SE-061` - `SE-080`)
  - C5: Cuentas Nacionales y PIB (`SE-081` - `SE-100`)
  - C6: Precios e Inflación Sectorial (`SE-101` - `SE-120`)
  - C7: Finanzas Públicas y Deuda (% PIB) (`SE-121` - `SE-140`)
  - C8: Sector Externo y Términos de Intercambio (`SE-141` - `SE-160`)
  - C9: Medio Ambiente y Transición Energética (`SE-161` - `SE-180`)
  - C10: Casos Adversarios, Frecuencias Inválidas y Abstención (`SE-181` - `SE-200`)

- [ ] **Step 1: Write failing test verifying dataset integrity**

```python
# tests/test_benchmark_dataset_integrity.py
import json
from pathlib import Path


def test_200_benchmark_dataset_structure():
    path = Path("tests/benchmark/semantic_benchmark_cases_200.json")
    assert path.exists(), "Benchmark dataset file does not exist"

    with open(path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) == 200, f"Expected 200 benchmark cases, got {len(cases)}"

    case_ids = [c["id"] for c in cases]
    assert len(set(case_ids)) == 200, "Duplicate test case IDs found"

    clusters = {}
    for c in cases:
        cluster = c.get("cluster")
        assert cluster, f"Case {c['id']} missing cluster"
        clusters[cluster] = clusters.get(cluster, 0) + 1

    assert len(clusters) == 10, f"Expected 10 clusters, got {len(clusters)}"
    for cl, count in clusters.items():
        assert count == 20, f"Cluster {cl} has {count} cases; expected 20"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_benchmark_dataset_integrity.py`
Expected: FAIL (file does not exist yet)

- [ ] **Step 3: Author `tests/benchmark/semantic_benchmark_cases_200.json` with all 200 cases**

Generate the complete JSON file with 200 realistic, colloquial, dimensional, and adversarial queries across Latin America.

- [ ] **Step 4: Run test to verify dataset integrity passes**

Run: `uv run pytest tests/test_benchmark_dataset_integrity.py`
Expected: PASS (200 cases, 10 clusters of 20 each)

- [ ] **Step 5: Commit changes**

```bash
git add tests/benchmark/semantic_benchmark_cases_200.json tests/test_benchmark_dataset_integrity.py
git commit -m "test(semantic): author complete 200-case empirical benchmark dataset"
```

---

### Task 3: Parser & Matcher Enhancements for Income Modifiers and Regionalisms

**Files:**
- Modify: `src/statscepal/semantic/parser.py`
- Modify: `src/statscepal/semantic/matcher.py`
- Modify: `src/statscepal/semantic/engine.py`
- Test: `tests/test_parser_income_modifiers.py`

**Interfaces:**
- Consumes: Raw natural language query
- Produces: `ParsedIntent` with context-aware root concepts:
  - *"la guita de los laburantes / trabajadores"* $\to$ `SALARIO_MEDIO_REAL` (ID 128 / 3338)
  - *"la guita mínima / el sueldo por ley / salario básico"* $\to$ `SALARIO_MINIMO_REAL` (ID 3337)
  - *"la guita de las familias / de los hogares / por cabeza"* $\to$ `INGRESO_HOGARES_PER_CAPITA` (ID 3345)
  - *"la guita en Chile en 2021"* (sin modificadores) $\to$ `is_ambiguous_measure = True`, `ambiguous_candidate = "INCOME_MEASURES"`, `ALTERNATIVE_PROPOSED` con IDs [128, 3337, 3345]
  - Regionalismos chilenos (*pega*, *lucas*, *cabros*), rioplatenses (*laburo*, *pibes*), mexicanos (*chamba*, *lana*, *chavos*), colombianos (*camello*, *plata*).

- [ ] **Step 1: Write failing test for income disambiguation and regionalisms**

```python
# tests/test_parser_income_modifiers.py
from statscepal.semantic.parser import QueryParser
from statscepal.semantic.engine import SemanticResolutionEngine


def test_income_modifier_disambiguation():
    parser = QueryParser()

    # 1. Minimum wage modifier
    intent_min = parser.parse("Cual fue la guita minima por ley en Chile en 2022")
    assert intent_min.root_concept == "SALARIO_MINIMO"

    # 2. Average real wage modifier
    intent_avg = parser.parse("La guita de los laburantes en Argentina en 2021")
    assert intent_avg.root_concept == "SALARIO_REAL"

    # 3. Household per capita modifier
    intent_hh = parser.parse("Cual es la plata de los hogares por cabeza en Colombia en 2020")
    assert intent_hh.root_concept == "INGRESO_HOGAR_PER_CAPITA"

    # 4. Purely ambiguous income query -> trigger alternatives
    engine = SemanticResolutionEngine()
    resp_ambiguous = engine.resolve("Como estuvo la guita en Chile en 2021")
    assert resp_ambiguous.status == "ALTERNATIVE_PROPOSED"
    alt_ids = [alt.indicator_id for alt in resp_ambiguous.proposed_alternatives]
    assert 3337 in alt_ids or 128 in alt_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_parser_income_modifiers.py`
Expected: FAIL

- [ ] **Step 3: Implement context modifier parsing and ambiguity rules in `parser.py` and `engine.py`**

Add syntactic modifier rules for `MINIMO`, `HOGAR`, `LABURANTES`, `DISTRIBUCION`, and the ambiguity gate when no modifier is provided.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_parser_income_modifiers.py`
Expected: PASS

- [ ] **Step 5: Run existing non-integration test suite to verify zero regressions**

Run: `uv run pytest -m "not integration"`
Expected: 168+ passed.

- [ ] **Step 6: Commit changes**

```bash
git add src/statscepal/semantic/parser.py src/statscepal/semantic/engine.py tests/test_parser_income_modifiers.py
git commit -m "feat(semantic): implement income modifier context parsing and ambiguity safeguards"
```

---

### Task 4: Automated Benchmark Execution & Stress Test (200 Cases)

**Files:**
- Create: `tests/test_semantic_benchmark_200.py`
- Modify: `tests/test_semantic_benchmark.py`

**Interfaces:**
- Consumes: `tests/benchmark/semantic_benchmark_cases_200.json`, `SemanticResolutionEngine`
- Produces: Métrica formal de Top-1 Accuracy ($\ge 98\%$), False Substitution Rate ($0.0\%$) y latencia p50 ($< 2.0\text{ ms}$) evaluada sobre los 200 casos.

- [ ] **Step 1: Write the 200-case parameterized benchmark runner**

```python
# tests/test_semantic_benchmark_200.py
import json
import time
from pathlib import Path
import pytest
from statscepal.semantic.engine import SemanticResolutionEngine


@pytest.fixture(scope="module")
def benchmark_engine():
    return SemanticResolutionEngine()


@pytest.fixture(scope="module")
def benchmark_cases_200():
    path = Path("tests/benchmark/semantic_benchmark_cases_200.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_200_cases_top1_accuracy_and_latency(benchmark_engine, benchmark_cases_200):
    correct = 0
    false_substitutions = 0
    latencies = []

    for case in benchmark_cases_200:
        query = case["query"]
        expected_status = case["expected_status"]
        expected_id = case.get("expected_indicator_id")

        t0 = time.perf_counter()
        resp = benchmark_engine.resolve(query)
        latencies.append((time.perf_counter() - t0) * 1000.0)

        # Check status
        if resp.status == expected_status:
            if expected_id is None or (resp.selected_indicator and resp.selected_indicator.indicator_id == expected_id):
                correct += 1
            elif expected_status in ["ALTERNATIVE_PROPOSED", "RESOLVED_WITH_ANCHORS"] and resp.selected_indicator and resp.selected_indicator.indicator_id == expected_id:
                correct += 1
        else:
            # Check for false substitutions (untyped swap)
            if resp.selected_indicator and expected_id and resp.selected_indicator.indicator_id != expected_id:
                if resp.status == "RESOLVED":
                    false_substitutions += 1

    accuracy = correct / len(benchmark_cases_200)
    fsr = false_substitutions / len(benchmark_cases_200)
    latencies.sort()
    p50_latency = latencies[len(latencies) // 2]

    assert accuracy >= 0.98, f"Top-1 Accuracy was {accuracy:.2%}, required >= 98.0%"
    assert fsr == 0.0, f"False Substitution Rate was {fsr:.2%}, required 0.0%"
    assert p50_latency < 2.0, f"p50 latency was {p50_latency:.3f}ms, required < 2.0ms"
```

- [ ] **Step 2: Run 200-case benchmark test**

Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`
Expected: PASS (Accuracy >= 98.0%, FSR == 0.0%, p50 < 2.0ms)

- [ ] **Step 3: Run full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: 170+ passed.

- [ ] **Step 4: Commit benchmark runner**

```bash
git add tests/test_semantic_benchmark_200.py
git commit -m "test(semantic): implement automated 200-case benchmark runner"
```

---

### Task 5: Comprehensive Benchmark Report & Traceability Documentation

**Files:**
- Create: `docs/specs/2026-10-15-benchmark-200-preguntas-motor-semantico.md`
- Create artifact: `C:\Users\camac\.gemini\antigravity-cli\brain\70e27c4c-70a0-43f4-8fd2-2eabaf6918e6\benchmark_200_preguntas.md`

**Interfaces:**
- Consumes: Resultados empíricos de los 200 casos de prueba
- Produces: Informe metodológico exhaustivo con:
  - Resumen ejecutivo y métricas globales (Accuracy, FSR, Latencia).
  - Tabla de resultados desglosada por los 10 clusters temáticos.
  - Casos de estudio detallados con trazas reales de ejecución (`execution_trace`).
  - Matriz de desambiguación de ingresos y salarios (*"guita"*, *"plata"*, *"sueldo"*).
  - Guía de verificación interactiva para usuarios y evaluadores externos.

- [ ] **Step 1: Author markdown technical report in `docs/specs/`**

Write `docs/specs/2026-10-15-benchmark-200-preguntas-motor-semantico.md` with complete statistical analysis and live logs.

- [ ] **Step 2: Generate user-facing artifact in brain directory**

Write `C:\Users\camac\.gemini\antigravity-cli\brain\70e27c4c-70a0-43f4-8fd2-2eabaf6918e6\benchmark_200_preguntas.md` with interactive overview.

- [ ] **Step 3: Verify documentation links and code symbol references**

Check all file links and markdown formatting.

- [ ] **Step 4: Commit documentation to git**

```bash
git add docs/specs/2026-10-15-benchmark-200-preguntas-motor-semantico.md
git commit -m "docs(semantic): add official 200-question empirical benchmark audit report"
```
