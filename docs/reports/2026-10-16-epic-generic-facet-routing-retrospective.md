# Informe de Retrospectiva de Arquitectura: Ingestión de Metadatos y Enrutamiento Genérico de Facetas (Épica E1–E5)

**Fecha de Certificación:** 2026-10-16  
**Repositorio:** `statscepal` (`C:\papx\statscepal`)  
**Equipo Revisor Colegiado:**
- **Winston** (Arquitecto de Sistemas & Revisor Principal)
- **Raúl** (Econometrista Macro-Estructuralista de la CEPAL)
- **Amelia** (Ingeniera de Software Senior — Implementadora)

---

## 1. Contexto y Problema Original

El motor semántico de `statscepal` fue concebido para resolver consultas en lenguaje natural hacia los indicadores oficiales de la base de datos de CEPALSTAT. Inicialmente, ante una consulta motivadora de alta relevancia social como:
> *"¿Cuál es la pobreza étnica en el Perú del 2020?"*

El motor resolvía inicialmente hacia la tasa de pobreza nacional canónica (`ID 3328`), omitiendo la dimensión étnico-racial debido a que el indicador canónico no posee dicha desagregación. Cuando se implementó el primer enrutamiento multidimensional, se introdujo código hardcodeado en `engine.py`, `parser.py` y `matcher.py`:
- `if "etnia" in facets:`
- `target_indicator_id = 3342`
- `DEFAULT_OFFICIAL_DIMENSIONS[3342]`
- Comprobaciones literales de agregados como `{"POBREZA_TOTAL", "TOTAL", "NACIONAL"}`.

Este enfoque artesanal presentaba una deuda técnica inaceptable: **no escalaba a los ~1,739 indicadores del catálogo oficial de CEPALSTAT**, generaba riesgo de dispersión metodológica y violaba el principio de genericidad arquitectónica.

Para erradicar este problema de raíz, se formuló y ejecutó la épica **`Metadata Ingestion & Generic Facet Routing` (E1–E5)**, gobernada por una política de congelamiento estricto de casos artesanales y ejecutada mediante desarrollo guiado por subagentes (SDD).

---

## 2. Evolución Arquitectónica (Las 5 Etapas)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ E1: DIMENSION HARVESTER                                                     │
│ Cosecha automatizada de metadatos oficiales de la API a SQLite.              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ E2: DECLARATIVE FACET ONTOLOGY                                              │
│ Definición declarativa de 13 facetas canónicas y auditoría de dimensiones.   │
└───────────────────┬─────────────────────────────────────┬───────────────────┘
                    │                                     │
                    ▼                                     ▼
┌──────────────────────────────────────┐   ┌──────────────────────────────────┐
│ E3: AUTOMATIC BREAKDOWN INFERENCE    │   │ E4: GENERIC STAGE 4 GATE         │
│ GraphBuilder infiere aristas de      │   │ Eliminación de literales AST,    │
│ desagregación estrictas en SQLite.   │   │ precarga en memoria SQLite.      │
└───────────────────┬──────────────────┘   └──────────────────┬───────────────┘
                    │                                         │
                    └──────────────────┬──────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ E5: MULTIDIMENSIONAL FACET-COVERAGE BENCHMARK                               │
│ Matriz de 70 casos Faceta x Familia, aislamiento léxico y FSR = 0.00%.      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### E1 · Cosechador de Metadatos de Dimensiones (`CatalogStore` & `Harvester`)
- Se crearon las tablas relacionales en SQLite `indicator_dimensions` y `dimension_members`.
- Se implementó un cosechador reanudable con rate-limiting y backoff exponencial (`statscepal catalog harvest`).
- La ejecución en integración continua (CI) opera con hermeticidad absoluta (100% offline) mediante fixtures JSON simulados en `tests/fixtures/dimensions/`.

### E2 · Ontología Declarativa de Facetas (`FacetOntology`)
- Se reemplazaron las reglas cableadas con modelos inmutables Pydantic (`FacetDefinition`, `QueryTriggerRule`, `MemberPatternRule`, `FacetOntology`).
- Se declararon las **13 facetas canónicas socioeconómicas**:
  1. `sexo` (Hombre, Mujer, Ambos sexos)
  2. `area` (Urbano, Rural, Nacional)
  3. `severidad` (Pobreza extrema, Pobreza total)
  4. `etnia` (Indígena, Afrodescendiente, No indígena, Total)
  5. `edad` (Juventud, Adultos mayores, Infancia)
  6. `quintil` (Quintil 1 a 5)
  7. `estrato` (Deciles, Quintiles, Relación Q5/Q1)
  8. `educacion` (Primaria, Secundaria, Terciaria, Universitaria, Sin instrucción)
  9. `formalidad` (Formal, Informal)
  10. `canasta` (Alimentos, Básica)
  11. `rubro` (General, Alimentos)
  12. `moneda` (Dólares constantes, Moneda nacional)
  13. `actividad` (Público, Privado, Agropecuario, Industria, Servicios)
- Cada faceta define explícitamente sus semánticas de agregados implícitos (`implicit_aggregate_values`), eliminando la necesidad de listas hardcodeadas en el motor.
- Se introdujo el comando CLI `statscepal catalog facet-audit` para diagnosticar la cobertura de dimensiones cosechadas.

### E3 · Inferencia Automática de Aristas `BREAKDOWN_OF` (`GraphBuilder`)
- Se extendió el esquema relacional con `provenance TEXT DEFAULT 'curated'`, garantizando que las aristas curadas por expertos jamás sean sobrescritas por relaciones inferidas algorítmicamente.
- `GraphBuilder` normaliza los títulos de indicadores extrayendo su raíz conceptual canónica (`extract_name_stem`), clasifica las dimensiones usando `FacetOntology`, y deriva aristas `BREAKDOWN_OF` únicamente cuando el indicador hijo es un superconjunto estricto de facetas del indicador padre ($F_{\text{child}} \supsetneq F_{\text{parent}}$), respetando compatibilidad de unidad de medida.
- Se verificaron **0 aristas falsas** sobre el conjunto de referencia curado.

### E4 · Compuerta Dimensional Genérica en Etapa 4
- `QueryParser` delega la extracción de facetas a `FacetOntology.extract_facets_from_query()`, eliminando todo bloque condicional manual.
- `SemanticRegistry` precarga un índice optimizado en memoria (`_indicators_cache`, `_dimensions_cache`, `_relationships_cache`) que combina las semillas de respaldo con los datos de SQLite y sintetiza dinámicamente metadatos y facetas soportadas para indicadores no curados.
- **Etapa 4 de `SemanticResolutionEngine.resolve` es 100% genérica:**
  - Calcula facetas no atendidas mediante `self.registry.get_supported_facets(canonical_id)` y `self.ontology.is_critical_unhandled_facet()`.
  - Recorre aristas `RelationshipType.BREAKDOWN_OF` devueltas por el grafo en memoria.
  - Verifica vinculación de dimensiones vía `DynamicMemberMatcher`.
  - Si ninguna conmutación es válida, abstiene honestamente con `ResolutionStatus.ABSTAINED` y razón `UNSUPPORTED_FACET`.
- **Invariante AST:** La prueba `test_engine_stage4_has_zero_hardcoded_facet_or_indicator_literals` analiza el código fuente de `resolve()` y falla si `"etnia"`, `POBREZA_TOTAL`, `3342` o `DEFAULT_OFFICIAL_DIMENSIONS` son reintroducidos.

### E5 · Benchmark Sistemático de Cobertura Multidimensional
- Creación del catálogo `tests/benchmark/facet_coverage_cases.json` con **70 casos de prueba** estructurados en tres regímenes:
  1. *Desagregaciones Positivas (27 casos):* Enrutamiento hacia indicadores multidimensionales y vinculación exacta de `dim_id` y `member_name`.
  2. *Abstenciones Adversariales (27 casos):* Consultas que solicitan facetas no soportadas por una familia (ej. PIB por etnia, inflación por sexo, deuda pública rural) que deben abstenerse sin sustitución falsa.
  3. *Aislamiento Léxico (16 casos):* Aislamiento de palabras que contienen subcadenas similares a facetas (`"razón"` vs `"raza"`, `"panorama"`/`"programa"` vs `"rama"`, `"sociedad"` vs `"edad"`), y protección de conceptos compuestos (`"gasto público en educación"` -> `GASTO_EDUCACION`, ID 4406).
- Runner automatizado con reporte ASCII y comprobación estricta de **0.00% FSR**.

---

## 3. Rulings y Decisiones Clave de Diseño

1. **Semántica de Agregados Implícitos vs. Desagregaciones Críticas:**
   En las estadísticas de la CEPAL, las consultas que piden agregados nacionales (ej. *"pobreza total"*, *"tasa de desocupación nacional"*, *"ambos sexos"*) no deben gatillar conmutaciones a tablas multidimensionales complejas. Por el contrario, desagregaciones por autoidentificación étnica o quintil exigen conmutación. `FacetOntology.is_critical_unhandled_facet()` formaliza esta frontera econométrica.
2. **Cero Tolerancia a Sustituciones Falsas (FSR = 0.00%):**
   En econometría aplicada, devolver un indicador con una desagregación no solicitada o metodológicamente incompatible genera sesgo de agregación. Si no existe un indicador hijo válido que soporte la faceta, el motor debe abstenerse informativamente en lugar de adivinar o entregar una serie no comparable.
3. **Resiliencia de Diacríticos en Entornos Windows:**
   Mediante normalización NFKD, los nombres de miembros oficiales con tildes (`Indígena`, `Afrodescendiente`, `Décimo decil`) se emparejan sin fragilidad de codificación de consola entre UTF-8 y codepages locales de Windows.
4. **Independencia de Red:**
   Todos los tests operan 100% fuera de línea contra SQLite y lexicons en memoria. Ningún test unitario realiza llamadas HTTP en vivo a CEPALSTAT.

---

## 4. Evidencia Empírica Consolidada

### Tabla de Rendimiento y Benchmark de Facetas (70 Casos)
```text
================================================================================
                        FACET COVERAGE BENCHMARK REPORT                         
================================================================================
Facet           | Cases   | Passed  | Pass %   | False Swaps 
--------------------------------------------------------------------------------
actividad       | 5       | 5       | 100.0%   | 0           
area            | 10      | 10      | 100.0%   | 0           
canasta         | 2       | 2       | 100.0%   | 0           
edad            | 7       | 7       | 100.0%   | 0           
educacion       | 3       | 3       | 100.0%   | 0           
estrato         | 4       | 4       | 100.0%   | 0           
etnia           | 11      | 11      | 100.0%   | 0           
formalidad      | 2       | 2       | 100.0%   | 0           
moneda          | 3       | 3       | 100.0%   | 0           
quintil         | 4       | 4       | 100.0%   | 0           
rubro           | 3       | 3       | 100.0%   | 0           
severidad       | 5       | 5       | 100.0%   | 0           
sexo            | 11      | 11      | 100.0%   | 0           
--------------------------------------------------------------------------------
Total: 70 | Passed: 70 (100.00%) | FSR: 0.00% | Latency p50: 1.462 ms
================================================================================
```

### Suite Empírica de 200 Preguntas (`test_semantic_benchmark_200.py`)
- **Top-1 Accuracy:** **100.0%** (200 / 200 casos aprobados).
- **False Substitution Rate (FSR):** **0.00%** (estrictamente cero falsas sustituciones).
- **Salud de Clusters:** 10 de 10 clusters al 100% de aprobación.
- **Latencia de Resolución:** $p50 = 0.98\text{ ms}$, $p95 = 1.88\text{ ms}$.

### Suite Global de Regresión No-Integración
- **Pruebas Totales:** **278 pasadas**, 3 deseleccionadas en 45.30s.
- **Regresiones:** Cero.

---

## 5. Registro de Commits del Epic

```text
aa2108e feat(test): implement statistical evaluation runner and facet coverage certification matrix
a89eaad test(semantic): implement lexical boundary isolation and root concept protection stress suite
6c1f564 test(semantic): define systematic 13-facet multidimensional coverage test dataset
f5645af docs(plan): add task e5 multidimensional facet-coverage benchmark implementation plan
ec78705 feat(semantic): implement generic Stage 4 dimensional gate driven by FacetOntology and graph
e828a22 feat(semantic): preload SQLite dimensions and relationships into SemanticRegistry in-memory index
baf7a40 refactor(semantic): delegate query facet extraction in QueryParser to FacetOntology
e3c2acf docs(plan): add task e4 generic stage 4 dimensional gate implementation plan
2901cd8 feat(cli): add 'statscepal catalog build-graph' command and certify E3 inference
bb13bbd feat(semantic): implement GraphBuilder for automatic BREAKDOWN_OF relationship inference
e75ee56 feat(catalog): add provenance tracking and curated precedence to indicator_relationships
06cb4d4 docs(plan): add task e3 automatic breakdown inference implementation plan
7af873b feat(semantic): add harvested dimension audit engine and 'catalog facet-audit' CLI
27dada9 refactor(semantic): drive DynamicMemberMatcher from declarative FacetOntology
2997146 feat(semantic): implement declarative FacetOntology models and default registry
05cff68 docs(plan): add task e2 declarative facet ontology implementation plan
3a5d8b7 feat(catalog): implement dimension metadata harvester and CLI command
```

---

## 6. Conclusión y Veredicto Final

La Épica **`Metadata Ingestion & Generic Facet Routing` (E1–E5)** ha sido completada en su totalidad con éxito categórico. El motor de resolución semántica de `statscepal` ya no depende de rutas cableadas ni listas ad-hoc; opera como un sistema autónomo basado en ontologías declarativas, grafos relacionales y cosecha sistemática de metadatos oficiales de la CEPAL, preservando una exactitud del 100.0% y una tasa de sustitución falsa del 0.00%.

**Veredicto Final: APROBADO Y CERTIFICADO PARA PRODUCCIÓN.**
