# Task 2 Brief: Build the 200-Question Empirical Benchmark Dataset

## Requirements
Working directory: `C:\papx\statscepal`

You are implementing Task 2 of the 200-Question Empirical Benchmark Plan.
You must construct the comprehensive empirical benchmark dataset in `tests/benchmark/semantic_benchmark_cases_200.json` consisting of exactly **200 test cases** across **10 clusters** (20 cases per cluster), adhering strictly to the **8-4-4-2-2 coverage matrix**:
- 8 Canonical direct queries (diverse Latin American countries: Chile, Brasil, México, Colombia, Argentina, Perú, Uruguay, etc.).
- 4 Regionalisms / Slang (chilenismos, lunfardo rioplatense, mexicanismos, modismos andinos).
- 4 Dimensional Breakdowns & Indicator Swaps (`breakdown_of` via dynamic SQLite metadata).
- 2 Controlled Ambiguities (`ALTERNATIVE_PROPOSED`, never guessing).
- 2 Hard Abstentions or Survey Gaps (`ABSTAINED` or `RESOLVED_WITH_ANCHORS`).

### The 10 Clusters:
1. `C1_POBREZA` (Cases `SE-001` - `SE-020`): Pobreza total, extrema, brecha de pobreza (3329), severidad, modismos (*"miseria"*, *"indigencia"*).
2. `C2_DESIGUALDAD` (Cases `SE-021` - `SE-040`): Gini (3340), Palma, quintiles de ingreso (Q5/Q1), decil más rico, transferencias sociales.
3. `C3_MERCADO_LABORAL` (Cases `SE-041` - `SE-060`): Desocupación por sexo (127), desempleo juvenil (3331), informalidad laboral (*"chamba en negro"*), tasa de participación.
4. `C4_SALARIOS_E_INGRESOS` (Cases `SE-061` - `SE-080`): Desambiguación contextual de *"guita"*, *"plata"*, *"sueldo"*: Salario medio real (128), Salario mínimo real (3337), Ingreso laboral medio por sexo (3339), Ingreso per cápita del hogar (3345).
5. `C5_CUENTAS_NACIONALES` (Cases `SE-081` - `SE-100`): PIB total constante (729), PIB per cápita (730), PIB trimestral (731), consumo de los hogares, inversión bruta.
6. `C6_PRECIOS_E_INFLACION` (Cases `SE-101` - `SE-120`): IPC general (2928), IPC alimentos y bebidas (2929), IPC transporte y energía (2930), tasas de variación interanual (*"carestía de la comida"*).
7. `C7_FINANZAS_PUBLICAS` (Cases `SE-121` - `SE-140`): Deuda pública (% PIB, 1240), balance primario (% PIB, 1241), ingresos tributarios (% PIB, 1242), precedencia sobre PIB.
8. `C8_SECTOR_EXTERNO` (Cases `SE-141` - `SE-160`): Balanza en cuenta corriente (% PIB, 1243), términos de intercambio FOB/CIF (1244), balanza comercial.
9. `C9_MEDIO_AMBIENTE` (Cases `SE-161` - `SE-180`): Emisiones totales con LULUCF (5681), emisiones netas sin LULUCF (5682), energías renovables en matriz eléctrica (5683).
10. `C10_ADVERSARIOS_Y_ABSTENCIONES` (Cases `SE-181` - `SE-200`): Periodicidades inválidas (diaria), vacíos muestrales CASEN 2021, facetas imposibles (*"astronautas"*, *"personas más inteligentes"*), años futuros o fuera de rango (< 1950, > 2030).

### Schema for each case:
```json
{
  "id": "SE-001",
  "cluster": "C1_POBREZA",
  "difficulty": "CANONICAL",
  "query": "Tasa de pobreza en Brasil en 2021",
  "expected_status": "RESOLVED",
  "expected_indicator_id": 3328,
  "expected_facets": {"severidad": "POBREZA_TOTAL", "area": "NACIONAL"},
  "expected_reason": null,
  "expected_alternatives": []
}
```

## TDD Instructions
1. Write `tests/test_benchmark_dataset_integrity.py` asserting exactly 200 cases, exactly 10 clusters of 20 cases each, unique IDs, valid schemas, and non-empty queries.
2. Run `uv run pytest tests/test_benchmark_dataset_integrity.py` and capture RED failing output.
3. Generate `tests/benchmark/semantic_benchmark_cases_200.json`.
4. Run `uv run pytest tests/test_benchmark_dataset_integrity.py` and capture GREEN passing output.
5. Commit:
   `git add tests/benchmark/semantic_benchmark_cases_200.json tests/test_benchmark_dataset_integrity.py`
   `git commit -m "test(semantic): author complete 200-case empirical benchmark dataset"`
6. Write full report to:
   `.superpowers/sdd/2026-10-15-semantic-engine-200-queries-benchmark-plan/task-2-report.md`
