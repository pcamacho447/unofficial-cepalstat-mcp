# Especificación de Arquitectura v2: Motor de Resolución Semántica y Validación Estadística para CEPALSTAT MCP

> **Estado:** Documento Normativo de Arquitectura y Decisiones de Diseño  
> **Fecha:** 15 de Octubre de 2026  
> **Origen:** Incorporación formal de la Revisión Técnica de Arquitectura (Secciones 1 a 10)  
> **Ubicación:** `docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md`  
> **Autores / Panel BMAD:** Equipo Técnico de CEPALSTAT MCP (Raúl Prebisch, Winston, Amelia, Sally, Mary, John)

---

## 1. Principio Rector: De Similitud Semántica a Validación Estadística

El objetivo central del motor semántico no es adivinar qué indicador quiso decir el usuario basándose en similitud de texto o embeddings, sino **construir un motor de inferencia estadística que pueda justificar por qué seleccionó un indicador, qué filtros aplicó, qué observaciones encontró y cuándo debe abstenerse por falta de evidencia.**

### La Regla de Oro de las Tres Condiciones Independientes:
Antes de ejecutar cualquier consulta, el sistema debe comprobar de forma determinista:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TRES CONDICIONES OBLIGATORIAS                   │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Equivalencia Conceptual:    ¿El indicador mide el fenómeno pedido?  │
│                               (Incidencia ≠ Pobreza Extrema ≠ Feminidad)│
│                                                                        │
│ 2. Compatibilidad Dimensional: ¿El indicador soporta exactamente       │
│                               las dimensiones requeridas sin inventar? │
│                                                                        │
│ 3. Disponibilidad Empírica:    ¿Existe una celda con valor para ese    │
│                               país, año y combinación de miembros?     │
└────────────────────────────────────────────────────────────────────────┘
```

Si alguna de estas tres condiciones no se satisface, el motor **no debe forzar una respuesta**: debe ejecutar su **Política de Abstención Justificada**, presentando alternativas o solicitando una aclaración precisa.

---

## 2. Separación de Tres Capas Arquitectónicas (Capa Léxica vs Conceptual vs Metadatos)

Se supera el acoplamiento de diccionarios hardcodeados separando formalmente tres niveles:

```mermaid
graph TD
    subgraph CAPA 1: Léxica (Entrada y Variantes)
        L1["Sinónimos, modismos y regionalismos:<br/>'el campo', 'pibas', 'chavos', 'en negro'"]
    end
    
    subgraph CAPA 2: Conceptual (Ontología e Intención)
        C1["Conceptos abstractos normalizados:<br/>AREA_RURAL, SEXO_FEMENINO, EDAD_JUVENTUD,<br/>POBREZA_INCIDENCIA, INFORMALIDAD"]
    end
    
    subgraph CAPA 3: Específica del Indicador (Metadatos Reales)
        M1["Catálogo SQLite / API CEPALSTAT:<br/>ID 3341 -> Dim 144 (Sexo) -> Member 266 (Mujeres)<br/>ID 3341 -> Dim 326 (Área) -> Member 331 (Rural)<br/>Unidades, Notas Metodológicas, Cobertura"]
    end
    
    L1 --> C1
    C1 --> M1
```

1. **Capa Léxica:** Normaliza texto en bruto, tokeniza, procesa diacríticos y reconoce modismos regionales latinoamericanos.
2. **Capa Conceptual:** Traduce la intención a conceptos formales (`POBREZA_INCIDENCIA`, `AREA=RURAL`, `SEXO=FEMENINO`).
3. **Capa de Metadatos del Indicador:** Descubre de manera dinámica en SQLite/API cuáles son las dimensiones y miembros reales de cada indicador candidato. **Ningún ID de dimensión o miembro se asume globalmente**.

---

## 3. Resolución de las 8 Decisiones Técnicas Críticas

En respuesta a la Sección 9 de la revisión técnica, se definen los siguientes contratos:

### Decisión 1: Contrato de Entrada y Salida del Motor Semántico

#### Entrada (`SemanticQueryRequest`):
```json
{
  "query": "¿Cuál fue la pobreza de las mujeres jóvenes rurales en Brasil en 2021?",
  "user_context": {
    "preferred_source": "armonizada_cepal",
    "allow_alternative_measures": false
  }
}
```

#### Salida (`SemanticResolutionResponse`):
```json
{
  "status": "RESOLVED",
  "resolution_type": "EXACT_MATCH | ALTERNATIVE_PROPOSED | ABSTAINED",
  "selected_candidate": {
    "indicator_id": 3341,
    "name": "Tasa de incidencia de la pobreza según sexo y edad",
    "measure_type": "INCIDENCIA_PORCENTUAL",
    "unit": "% de personas",
    "relevance_score": 0.94,
    "selection_reason": "Cumple equivalencia conceptual con 'pobreza', admite simultáneamente Sexo, Edad y Área, y posee observación empírica para Brasil 2021."
  },
  "applied_filters": {
    "country": {"code": "BRA", "member_id": 213},
    "year": {"year": 2021, "member_id": 68230},
    "dimensions": [
      {"dim_id": 144, "dim_name": "Sexo__ESTANDAR", "member_id": 266, "member_name": "Mujeres"},
      {"dim_id": 43054, "dim_name": "Grupo de edad", "member_id": 43058, "member_name": "15 a 24 años"},
      {"dim_id": 326, "dim_name": "Área geográfica", "member_id": 331, "member_name": "Rural"}
    ]
  },
  "empirical_verification": {
    "observation_exists": true,
    "value": 31.8,
    "source_survey": "PNADC (IBGE / CEPAL)",
    "timeliness_status": "OBSERVATION_EXISTING"
  },
  "justification": "Se seleccionó el indicador 3341 mediante conmutación justificada desde el canónico 3328, debido a que el 3328 no admite desagregación por sexo ni edad.",
  "alternatives": [
    {
      "indicator_id": 3330,
      "name": "Índice de feminidad de la pobreza",
      "relationship": "alternative_measure",
      "note": "Ratio de mujeres por cada 100 hombres pobres (no es un porcentaje)."
    }
  ]
}
```

---

### Decisión 2: Metadatos Mínimos para Validez de un Indicador
Un indicador del catálogo solo se considera elegible para responder a una consulta si sus metadatos locales verifican:
1. `indicator_id` (Entero positivo).
2. `name` y `description` (Texto descriptivo formal).
3. `unit` (Unidad de medida: %, miles de personas, dólares constantes, etc.).
4. `dimensions` completas con lista de `members` activos.
5. `temporal_coverage` (Años con datos reales por país).
6. `source_institution` y `methodological_notes`.

---

### Decisión 3: Relaciones Tipadas para Sustitución (`Indicator Swap`)
Se prohíbe la sustitución ciega de indicadores. El grafo de conocimiento solo permite conmutar un indicador $A$ por un indicador $B$ bajo relaciones tipadas explícitas:

| Tipo de Relación | Significado Estadístico | ¿Permite Swap Automático? | Ejemplo |
|---|---|:---:|---|
| `breakdown_of` | $B$ es la versión desagregada de $A$ bajo la misma metodología y unidad. | **SÍ** | `3341` (Pobreza por sexo/edad) es `breakdown_of` `3328` (Pobreza total). |
| `harmonized_version_of` | $B$ es la serie armonizada regional de la serie nacional $A$. | **SÍ** (para análisis regional) | `2203` (PIB USD constantes) vs. `2204` (PIB moneda nacional). |
| `alternative_measure` | $B$ mide una faceta complementaria del mismo fenómeno con distinta unidad o población. | **NO (Requiere confirmación)** | `3330` (Índice de feminidad) es `alternative_measure` de `3328`. |
| `broader_than` / `narrower_than` | Relación jerárquica de cobertura temática. | **NO** | `EMPLEO` es `broader_than` `DESOCUPACION_JUVENIL`. |
| `methodologically_incomparable` | Series que difieren en concepto, cobertura o diseño muestral. | **PROHIBIDO** | Pobreza monetaria vs. Pobreza multidimensional ODS. |

---

### Decisión 4: Criterios Formales de Abstención y Solicitud de Aclaración
El motor **debe abstenerse de seleccionar automáticamente** cuando:
1. **Falta de Equivalencia Conceptual:** Ningún candidato supera el umbral de relevancia conceptual ($S_{\text{concept}} < 0.70$).
2. **Conflicto de Medidas Estadísticas:** La consulta es ambigua entre dos medidas no intercambiables (ej. "¿pobreza femenina?" -> ¿tasa de pobreza en mujeres `3341` o índice de feminidad `3330`?) y la diferencia de score es menor a 0.05.
3. **Dimensión Requerida Inexistente:** El usuario solicita una faceta mandatoria (ej. "empleo informal por quintiles") y ningún indicador armonizado del catálogo posee esa desagregación.
4. **Ausencia Total de Observación:** El país o período solicitado no tiene ningún dato en ninguna serie candidata válida.

En caso de abstención, el payload devuelve `status: "ABSTAINED"` con la pregunta de clarificación recomendada.

---

### Decisión 5: Tratamiento de Dimensiones Inexistentes y Celdas Vacías
- Si una dimensión solicitada no existe en el catálogo para ese fenómeno, el sistema **nunca inventa el dato ni aproxima**.
- Devuelve explícitamente:
  `"unsupported_facet": "FORMALIDAD_LABORAL", "explanation": "CEPALSTAT no dispone de desagregación formal/informal para este indicador en el país solicitado."`

---

### Decisión 6: Los Cuatro Estados de Disponibilidad Temporal
Superando la clasificación teórica, el motor audita en la base de datos la celda empírica y asigna uno de 4 estados:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   LOS 4 ESTADOS DE DISPONIBILIDAD                      │
├────────────────────────────────────────────────────────────────────────┤
│ 1. OBSERVATION_EXISTING:    Existe celda con valor numérico válido.    │
│ 2. OBSERVATION_MISSING:     La serie existe pero esa celda es NULL    │
│                             (causa no documentada).                    │
│ 3. PERIOD_UNOBSERVED:       El diseño muestral no midió ese año        │
│                             (ej. CASEN en Chile en 2021).              │
│ 4. PENDING_UPDATE:          El período está en desfase normal de       │
│                             procesamiento/publicación oficial.         │
└────────────────────────────────────────────────────────────────────────┘
```

**Política estricta:** Para los estados 2, 3 y 4, **se prohíbe interpolar o autocompletar**. Los puntos ancla (*Nearest-Neighbor Anchors*) se reportan exclusivamente como contexto histórico, nunca como sustituto del dato intermedio.

---

### Decisión 7: Procedimiento de Ingesta y Versionado de Metadatos
- Se utiliza SQLite local (`.statscepal_cache.db`) con tablas relacionales normalizadas:
  - `master_indicators`: Registro de 2,143 indicadores.
  - `indicator_dimensions`: Dimensiones nativas descubiertas por indicador.
  - `dimension_members`: Miembros con sus IDs oficiales.
  - `indicator_relationships`: Grafo de relaciones tipadas (`breakdown_of`, `alternative_measure`, etc.).
  - `data_availability_matrix`: Matriz de celdas existentes por País $\times$ Año $\times$ Indicador.
- Versionado con marca de tiempo UTC y hash de control para detectar cambios en la API oficial.

---

### Decisión 8: Benchmark de Validación Inicial (El Test-Bed)
Antes de ampliar ontologías en abstracto, se establece una suite de **30 casos de prueba empíricos** con ground truth estricto.

#### Métricas de Evaluación Obligatorias:
1. **Top-1 Resolution Accuracy:** % de consultas donde el indicador elegido es el correcto según estándar econométrico.
2. **Recall@3:** % de consultas donde el indicador correcto está entre los top-3.
3. **False Substitution Rate (Tasa de Falsos Swaps):** Casos donde se conmutó un indicador indebidamente. Meta: **0.0%**.
4. **Facet & Member Precision:** % de miembros de dimensión mapeados con exactitud.
5. **Temporal Status Accuracy:** % de acierto en los 4 estados temporales.
6. **Justified Abstention Rate:** % de casos ambiguos o imposibles donde el motor se abstuvo correctamente.
7. **Latencia p50 / p95:** Medición separada de la resolución local en SQLite (meta: $< 2$ ms) y de la llamada HTTP a la API externa.

---

## 4. Pipeline Operativo en 5 Etapas

```
[Consulta del Usuario]
       │
       ▼
┌────────────────────────────────────────┐
│ Etapa 1: Interpretación Semántica (LLM)│ -> Extrae Conceptos, Facetas, Geo, Tiempo
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Etapa 2: Recuperación Híbrida          │ -> Búsqueda FTS5 en SQLite + Synonyms
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Etapa 3: Filtro Duro de Restricciones  │ -> Equivalencia Conceptual
│          (Código Python Determinista)  │    Compatibilidad Dimensional
└──────────────────┬─────────────────────┘    Disponibilidad Empírica
                   │
                   ▼
┌────────────────────────────────────────┐
│ Etapa 4: Scoring y Política Abstención │ -> Ranking explicable de válidos
│                                        │    ¿Empate o < umbral? -> Abstención
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Etapa 5: Consulta API y Auditoría      │ -> Ejecución con IDs verificados
│                                        │    Auditoría temporal y procedencia
└────────────────────────────────────────┘
```

---

## 5. Hoja de Ruta de Implementación: El Corte Vertical Funcional

Siguiendo la recomendación de la revisión técnica, no expandiremos las 25 ontologías en el aire. La implementación procederá en **tres fases estrictamente verificables**:

### Fase A: El Benchmark y el Schema de Metadatos
1. Diseñar el archivo del benchmark con 30 casos reales: `tests/benchmark/semantic_resolution_cases.json`.
2. Crear las tablas de metadatos relacionales en SQLite para dimensions, members y relaciones tipadas.
3. Construir el test runner automatizado que calcula las métricas de precisión, abstención y latencia.

### Fase B: El Corte Vertical Funcional (Dominio Pobreza y Empleo)
1. Ingestar y relacionar los indicadores de Pobreza (`3328`, `3341`, `3330`, `3337`, `4322`) y Mercado Laboral (`127`, `119`, `5097`, `340`).
2. Implementar las 5 etapas del pipeline en código Python (`src/statscepal/semantic/`).
3. Ejecutar el benchmark sobre este corte vertical y verificar que todas las restricciones duras se cumplan sin alucinaciones.

### Fase C: Expansión Progresiva Basada en Errores
1. Analizar los errores detectados por el benchmark.
2. Calibrar empíricamente los pesos del relevance score.
3. Expandir la ontología hacia los dominios Macroeconómico y Ambiental con la garantía de que el pipeline es estadísticamente inviolable.
