# Task 1 Brief: Expand Metadata Registry & SQLite Store for 200-Question Indicators

## Requirements
Working directory: `C:\papx\statscepal`
Base commit: `4afaa79729c8ee59fc48e22e3f3a8fb04e686e72`

You are implementing Task 1 of the 200-Question Empirical Benchmark Plan.
You must register all 25 official CEPALSTAT indicators in `SemanticRegistry` (`src/statscepal/semantic/registry.py`) and ensure they are populated into SQLite (`CatalogStore` in `src/statscepal/catalog/store.py`), including their measures, supported dimensions, members, and typed relationships.

### Indicators to Ensure Registered:
1. `3328`: "Población en situación de pobreza extrema y pobreza, por área" (INCIDENCIA_PORCENTUAL, %)
2. `3341`: "Tasa de incidencia de la pobreza según sexo y edad" (INCIDENCIA_PORCENTUAL, %)
3. `3329`: "Brecha de pobreza y pobreza extrema" (BRECHA_PORCENTUAL, %)
4. `3330`: "Índice de feminidad de la pobreza" (INDICE_FEMINIDAD, razón)
5. `3340`: "Distribución del ingreso de los hogares por quintiles y deciles" (DISTRIBUCION_INGRESO, %)
6. `127`: "Tasa de desocupación por sexo" (TASA_DESOCUPACION, %)
7. `3331`: "Tasa de desempleo juvenil de 15 a 24 años" (TASA_DESOCUPACION, %)
8. `128`: "Índice del salario medio real" (INDICE_REAL, índice 2018=100)
9. `3337`: "Salario mínimo real" (INDICE_REAL, índice 2018=100)
10. `3339`: "Ingreso laboral medio de la población ocupada por sexo y área" (MONTO_MONEDA_LOCAL, moneda local)
11. `3345`: "Ingreso medio per cápita de los hogares" (MONTO_MONEDA_LOCAL, moneda local)
12. `729`: "Producto interno bruto total anual a precios constantes" (MONTO_MONEDA_LOCAL, millones moneda nacional)
13. `730`: "Producto interno bruto per cápita a precios constantes" (USD_PER_CAPITA, USD)
14. `731`: "Producto interno bruto trimestral a precios constantes" (TASA_VARIACION_INTERANUAL, %)
15. `2928`: "Índice de precios al consumidor (IPC) general" (INDICE_PRECIOS, índice 2018=100)
16. `2929`: "Índice de precios al consumidor de alimentos y bebidas" (INDICE_PRECIOS, índice 2018=100)
17. `2930`: "Índice de precios al consumidor de transporte y energía" (INDICE_PRECIOS, índice 2018=100)
18. `1240`: "Saldo de la deuda pública del gobierno central en porcentaje del PIB" (PORCENTAJE_PIB, %)
19. `1241`: "Balance primario del gobierno central en porcentaje del PIB" (PORCENTAJE_PIB, %)
20. `1242`: "Ingresos tributarios del gobierno central en porcentaje del PIB" (PORCENTAJE_PIB, %)
21. `1243`: "Saldo en cuenta corriente de la balanza de pagos en porcentaje del PIB" (PORCENTAJE_PIB, %)
22. `1244`: "Términos de intercambio de bienes FOB/CIF" (INDICE_PRECIOS, índice 2018=100)
23. `5681`: "Emisiones totales de GEI incluyendo sector UTCUTS / con LULUCF" (VOLUMEN_EMISIONES, Mt CO2 eq)
24. `5682`: "Emisiones totales de GEI excluyendo sector UTCUTS / sin LULUCF" (VOLUMEN_EMISIONES, Mt CO2 eq)
25. `5683`: "Participación de energías renovables en la generación eléctrica" (PORCENTAJE_GENERACION, %)

### Typed Relationships to Register:
- `3328` --(breakdown_of)--> `3341`
- `3341` --(alternative_measure)--> `3330`
- `3328` --(alternative_measure)--> `3329`
- `128` --(breakdown_of)--> `3339`
- `128` --(alternative_measure)--> `3337`
- `128` --(alternative_measure)--> `3345`
- `729` --(breakdown_of)--> `730`
- `729` --(alternative_measure)--> `731`
- `2928` --(breakdown_of)--> `2929`
- `2928` --(breakdown_of)--> `2930`
- `1240` --(alternative_measure)--> `1241`
- `1240` --(alternative_measure)--> `1242`
- `5681` --(alternative_measure)--> `5682`

## TDD Instructions
1. Create `tests/test_semantic_registry_200.py` asserting all 25 indicators exist and relationships can be queried via `get_target_indicators` or `get_relationships`.
2. Run `uv run pytest tests/test_semantic_registry_200.py` and capture RED failing output.
3. Update `src/statscepal/semantic/registry.py` (and `src/statscepal/catalog/store.py` if needed).
4. Run `uv run pytest tests/test_semantic_registry_200.py` and capture GREEN passing output.
5. Run full non-integration test suite: `uv run pytest -m "not integration"` (all 166+ tests must pass).
6. Commit:
   `git add src/statscepal/semantic/registry.py src/statscepal/catalog/store.py tests/test_semantic_registry_200.py`
   `git commit -m "feat(semantic): register 25 official indicators and relationships for 200-question suite"`
7. Write your full report to:
   `.superpowers/sdd/2026-10-15-semantic-engine-200-queries-benchmark-plan/task-1-report.md`
8. Return the short contract:
   - Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
   - Commits created
   - One-line test summary
   - Concerns if any
   - Report file path
