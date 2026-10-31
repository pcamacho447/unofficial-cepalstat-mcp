# Especificación de Arquitectura Pre-MCP: Saneamiento Canónico, Descubrimiento FTS5 y Resolución Semántica Híbrida a Escala (1,739 Indicadores)

- **Fecha:** 2026-10-30
- **Estado:** Aprobado para Planificación en 3 Fases
- **Paquete:** `unofficial_cepalstat_mcp` (Python >=3.10)
- **Guardarraíles Vinculantes:** `.agents/rules/semantic-resolution-guardrails.md` y `AGENTS.md`

---

## 1. Objetivo

Preparar las capas `semantic/`, `catalog/`, `bitacora/` y `client.py` antes de implementar el servidor MCP para que cualquier agente de IA resuelva consultas socioeconómicas sobre los **1,739 indicadores oficiales de CEPALSTAT** (4 temas, 23 áreas) en 1–2 llamadas deterministas, manteniendo **0.00% False Substitution Rate (FSR)**, **Zero Facet Loss**, arranque en frío instantáneo (`< 50 ms`) y latencia de resolución local **`p50 < 0.5 ms` / `p95 < 2.0 ms`**.

---

## 2. Decisiones Arquitectónicas Aprobadas

1. **Instalación Limpia Pre-Sembrada (`Cold Start` — Fase 2):**
   - El wheel incluirá un snapshot comprimido de lectura (`src/unofficial_cepalstat_mcp/data/seed_catalog.db.gz`) con los 1,739 registros de `master_indicators`, unidades/metadatos (`indicator_metadata`), dimensiones no estructurales (`indicator_dimensions`, `dimension_members`), grafo dirigido `BREAKDOWN_OF` (`indicator_relationships`), matriz empírica `temporal_availability` y recetas certificadas (`recipes`), más las recetas markdown empaquetadas.
   - En el primer acceso a `get_cache_db_path()`, si la base no existe o no está sembrada, se descomprime atómicamente (`temp -> os.replace`) en `< 50 ms` sin tráfico HTTP.

2. **Migración Integral a `indicator_id` Reales de CEPALSTAT (Fase 1):**
   - Se eliminan los IDs ficticios y las colisiones de espacio de nombres en `VERTICAL_SLICE_INDICATORS` y `test_semantic_benchmark_200.json`, migrando todo el grafo curado a IDs reales publicados en `master_indicators`.
   - `EMPIRICAL_INDICATOR_ID_MAP` queda vacío (`{}`) como alias de compatibilidad hacia atrás (identidad `ind_id -> ind_id`). Cuando distintos conceptos semánticos apuntan a rubros específicos dentro de una misma tabla multi-serie de CEPALSTAT (ej. `1246` Operaciones del gobierno, `2050` Balanza de pagos, `365` IPC por división), el motor fija un `AppliedDimensionFilter` obligatorio sobre el rubro correspondiente (`mandatory_filters`).

3. **Resolución Semántica Híbrida de 2 Niveles (Fase 3):**
   - **Nivel 1 (Grafo Canónico Curado):** Resuelve los dominios macroeconómicos, laborales, sociales, demográficos y ambientales de alta frecuencia tras validar obligatoriamente el `Specificity Guard` (`Stage 3.5`) **antes** de emitir `RESOLVED` o `ALTERNATIVE_PROPOSED`.
   - **Nivel 2 (Recuperador Determinista sobre Catálogo Completo):** Cuando Nivel 1 no identifica `root_concept` o detecta especificidad temática no cubierta, consulta un índice invertido en memoria (sincronizado con `SQLite FTS5` + expansión de `Thesaurus` + miembros dimensionales no estructurales) sobre los 1,739 indicadores:
     - Evalúa cada candidato Top-$K$ ($K=10$) contra `FacetOntology` + `DynamicMemberMatcher` (`Zero Facet Loss`) y cobertura de tokens críticos.
     - Retorna `RESOLVED` únicamente si existe un único candidato ganador inequívoco por concepto, unidad y facetas.
     - Retorna `ALTERNATIVE_PROPOSED` (con resumen estructurado `< 250 tokens`) cuando compiten múltiples series compatibles (ej. serie regional CEPAL vs serie ODS, o personas vs `%`).
     - Retorna `ABSTAINED` cuando ningún candidato cubre el fenómeno o las facetas solicitadas (**0.00% FSR**).

---

## 3. Tabla Maestra de Saneamiento de `indicator_id` Reales (Fase 1)

| ID Anterior | Problema Detectado contra `master_indicators` | Nuevo `indicator_id` Real | Nombre Oficial en CEPALSTAT (`master_indicators`) | Filtro Obligatorio de Rubro (`mandatory_filters`) |
| :---: | :--- | :---: | :--- | :--- |
| `128` | No existe en API | **`341`** | Salario medio real anual | Ninguno |
| `3337` | Colisiona con pobreza por jefatura | **`340`** | Salario mínimo real | Ninguno |
| `3339` | Colisiona con pobreza por clima educativo | **`2287`** | Ingreso medio de la población ocupada, por sexo e inserción laboral | Ninguno |
| `3345` | Colisiona con brecha pobreza; mapeaba a ocupados (`5698`) | **`2198`** | Ingresos y gastos de los hogares a precios corrientes en moneda nacional | Rubro: Ingresos de los hogares (si aplica dimensión) |
| `3340` | Colisiona con pobreza por tipo de hogar | **`3324`** (quintiles) / **`3390`** (deciles) | Distribución del ingreso de las personas, por quintiles y área (`3324`) / hogares por deciles (`3390`) | Conmutación `3324 <-> 3390` según faceta `estrato` |
| `3331` / `3344` | No existen en API | **`5097`** | Tasa de desempleo, por sexo y edad - 19ª CIET (%) `SL_TLF_UEM_19ICLS` | `edad="JUVENTUD"` (`15 a 24`) cuando consulta es juvenil |
| `3333` | Colisiona con valor líneas de pobreza | **`2288`** | Relación del ingreso medio entre mujeres y hombres, por grupo de edad y área | Ninguno |
| `729` | No existe en API | **`2204`** | Producto interno bruto (PIB) total anual a precios constantes en dólares | Ninguno |
| `2203` | Metadato invertido (decía constantes; real es corrientes) | **`2203`** | Producto interno bruto (PIB) total anual a precios corrientes en dólares | Corregir `name`, `measure_type`, `unit` a USD corrientes |
| `2204` | Metadato invertido (decía corrientes MN; real es constantes USD) | **`2204`** | Producto interno bruto (PIB) total anual a precios constantes en dólares | Corregir `name`, `measure_type`, `unit` a USD constantes |
| `PIB_CORRIENTE` (MN) | Enrutaba a `729 -> 2204` (constantes USD) | **`2193`** | Producto interno bruto anual (PIB) por objeto del gasto a precios corrientes en moneda nacional | Rubro: Producto interno bruto (Total) |
| `730` | No existe en API | **`2206`** | Producto interno bruto (PIB) total anual por habitante a precios constantes en dólares | Ninguno |
| `731` / `2447` | No existen en API | **`286`** | Producto interno bruto trimestral por tipo del gasto a precios constantes/ términos de volumen en moneda nacional | Rubro: Producto interno bruto (Total) |
| `2928` | No existe en API | **`2484`** | Tasa de crecimiento anual del índice de precios al consumidor: diciembre a diciembre | Ninguno (`365` como `ALTERNATIVE_MEASURE` para índice nivel) |
| `2929` | Decía índice nivel; real `2929` es tasa variación alimentos | **`2929`** | Tasa de crecimiento anual del índice de precios al consumidor alimentos: diciembre a diciembre | Corregir `measure_type`/`unit` a `%` (`1684` para índice nivel) |
| `2930` | No existe; mapeaba a `4145` (IPC subyacente, opuesto a energía) | **`365`** | Indice de precios al consumidor | División/Rubro: Transporte / Vivienda y energía |
| `1241` | No existe en API | **`1246`** | Operaciones del gobierno (clasificación económica), en porcentajes del PIB | Rubro: Resultado primario (`Balance primario`) |
| `1242` | No existe en API | **`821`** | Ingresos tributarios por tipo de impuestos en porcentajes del PIB (América Latina y el Caribe) | Rubro por defecto: Total ingresos tributarios (o IVA/Renta si faceta) |
| `1243` | No existe en API | **`740`** | Saldo en cuenta corriente como porcentaje del producto interno bruto | Ninguno |
| `1244` / `2954` | `1244` no existe; `2954` colisiona con Tasa de actividad | **`883`** | Índices de la relación de precios del intercambio y poder de compra de las exportaciones | Rubro: Relación de precios del intercambio de bienes |
| `2949` | Colisiona con exportaciones CUCI Top 10 | **`2050`** | Balanza de pagos | Rubro: Balanza de bienes (FOB) |
| `4405` | Decía `% del PIB`; real `4405` es moneda nacional | **`4410`** (`% PIB`) / **`4405`** (MN) | Gasto público por función, en porcentajes del PIB (`4410`) | Función: Total gasto social / Salud / Educación |
| `4406` | No existe en API | **`460`** | Gasto público en educación | Ninguno |
| `5683` | Colisiona con alfabetización (`SE_ADT_LITR`) | **`3154`** | Proporción de energía renovable en la oferta de energía primaria | Alinear título y `unit="%"` |
| `1318` | No existe; mapeaba a `3097` (`%` agua potable) | **`4185`** | Extracción de agua, por sector | Rubro: Total extracción de agua |
| `4992` | Colisiona con `% población indígena por área` | **`28`** | Población, según área geográfica y sexo. | Ninguno (`4992` queda reservado a su significado real indígena `%`) |

---

## 4. Contratos Transversales Entre Fases

1. **Fase 1 -> Fase 2:**
   - Al cierre de la Fase 1, toda clave en `VERTICAL_SLICE_INDICATORS` existe en `master_indicators` con su significado real, `EMPIRICAL_INDICATOR_ID_MAP == {}`, `SemanticDataFetcher` enlaza columnas vía `FacetOntology.classify_dimension(dim_id: int | None, dim_name: str)` con fallo cerrado (`observation_exists=False`) ante filtros no resueltos, y `uv run mypy src/` reporta **0 errores**.
2. **Fase 2 -> Fase 3:**
   - Al cierre de la Fase 2, `CatalogStore` expone `search(query: str = "", theme: str | None = None, area: str | None = None, limit: int = 20) -> list[CatalogIndicator]` respaldado por `indicators_fts` (`FTS5` + `BM25` + expansión `Thesaurus`), `GraphBuilder` persiste únicamente aristas dirigidas `parent -> child` (`rel_type='breakdown_of'`) respetando unidades y dimensiones opacas `__raw_dim__:<norm_name>`, `temporal_availability` reemplaza el tope estático `2023`, y `seed_catalog.db.gz` hidrata automáticamente `.statscepal_cache.db` en frío.
3. **Fase 3 -> Servidor MCP:**
   - Al cierre de la Fase 3, `SemanticResolutionEngine` resuelve de forma híbrida (Tier 1 + Tier 2) sobre los 1,739 indicadores con `p50 < 0.5 ms` y `0.00% FSR`, `SemanticDataFetcher` empuja `members=` de país y año al endpoint `/records` sin mutar `SemanticResolutionResponse`, y `AsyncCepalStatClient` provee transporte asíncrono con caché TTL y *retry* exponencial listo para conectar con `FastMCP`.
