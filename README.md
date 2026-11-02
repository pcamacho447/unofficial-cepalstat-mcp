# unofficial-cepalstat-mcp

**Motor de Resolución Semántica, Servidor MCP y Cliente Econométrico Anti-Sesgo para UN CEPALSTAT**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Test Suite](https://img.shields.io/badge/tests-551%20passed-brightgreen.svg)]()
[![Curated Benchmarks](https://img.shields.io/badge/curated%20benchmarks-100%25%20Top--1-success.svg)](docs/reports/benchmark_200_preguntas.md)
[![False Substitution Rate](https://img.shields.io/badge/FSR-0.00%25-brightgreen.svg)](docs/reports/2026-10-18-adversarial-benchmark-specification.md)
[![Human Eval Resolution](https://img.shields.io/badge/human%20eval%20gap-54%25%20fail%20rate%20(46%25%20res)-orange.svg)](#2-la-brecha-del-lenguaje-natural-evaluación-humana-en-prueba-y-error)
[![Latency p50](https://img.shields.io/badge/latency%20p50-%3C%200.5%20ms-informational.svg)]()
[![Protocol](https://img.shields.io/badge/protocol-Model%20Context%20Protocol%20(MCP)-blueviolet.svg)](https://modelcontextprotocol.io/)
[![Source](https://img.shields.io/badge/source-CEPALSTAT%20Open%20Data-orange.svg)](https://statistics.cepal.org/portal/cepalstat/open-data.html?lang=es)

---

> [!IMPORTANT]
> **Aviso de Responsabilidad y No Oficialidad / Legal Disclaimer:**  
> **DISCLAIMER**: This project is an independent open-source tool and is **NOT an official product of, sponsored by, or affiliated with the United Nations Economic Commission for Latin America and the Caribbean (UN ECLAC / CEPAL)**. All statistical data provided through this tool is sourced from the public UN CEPALSTAT Open Data API.  
> *(Este proyecto es un desarrollo independiente de código abierto impulsado por la comunidad y no constituye una publicación oficial de la Secretaría de las Naciones Unidas ni de la Comisión Económica para América Latina y el Caribe).*

---

## 📌 ¿Por qué existe este proyecto?

Las APIs estadísticas de organismos multilaterales (como CEPALSTAT, Banco Mundial o FMI) almacenan miles de indicadores con modelos multidimensionales de alta complejidad. En CEPALSTAT coexisten **más de 1,739 indicadores**, millones de observaciones y decenas de dimensiones crudas (`dim_208=224`, `dim_48525=48528`, `dim_1361=501`).

Cuando los Modelos de Lenguaje (LLMs) o analistas intentan consultar estas APIs directamente, surgen fallas metodológicas críticas:
1. **Falsas Sustituciones Catastróficas (False Substitutions):** Un agente solicita *"valor agregado manufacturero per cápita"* y la API devuelve *"PIB total per cápita"* con score 1.0; o pide *"salario mínimo nominal"* y recibe el índice deflactado en términos reales sin advertencia.
2. **Desconexión Dimensional:** Errores al decodificar miembros de desagregación (ej. confundir *"área nacional"* con la expresión monetaria *"moneda nacional"*, o asignar códigos de género a variables agregadas).
3. **Vacíos y Discontinuidades en Encuestas de Hogares:** En América Latina, las encuestas de hogares sufren lagunas interanuales (años no observados). Consultar un año faltante conduce a alucinaciones o interpolaciones artificiales espurias.

`unofficial-cepalstat-mcp` (módulo Python `unofficial_cepalstat_mcp`) resuelve este problema mediante un **Motor de Resolución Semántica de 6 etapas**, respaldado por ontologías dimensionales, detección de polaridad económica, guardianes de especificidad no absorbida, y compatibilidad nativa con el **Model Context Protocol (MCP)** para LLMs (Claude, Cursor, Antigravity, OpenWebUI).

---

## 🏗️ Arquitectura del Sistema

### 1. Flujo End-to-End

```mermaid
flowchart TD
    UserQuery["Consulta en Lenguaje Natural<br>('desempleo juvenil urbano en argentina')"] --> Parser["1. QueryParser<br>(Entidades, Geografía, Frecuencia, Concepto)"]
    Parser --> Thesaurus["2. Thesaurus & Polarity<br>(Sinónimos LAC, Lemas, Polaridad)"]
    Thesaurus --> Gate["3. Hard Abstention Gate<br>(Detección de variables fuera de mandato)"]
    Gate --> Selection["4. Candidate Selection & Graph<br>(Travesía de relaciones ontológicas)"]
    Selection --> Specificity["5. Specificity & Frequency Guard<br>(Auditoría de tokens no absorbidos)"]
    Specificity --> Gating["6. Dimensional Gate & Member Matcher<br>(Filtro de Facetas & Vinculación de IDs)"]
    Gating --> Temporal["7. Temporal Audit & Anchor Points<br>(Detección de saltos en encuestas)"]
    Temporal --> Response["SemanticResolutionResponse<br>(RESOLVED / ALTERNATIVE_PROPOSED / ABSTAINED)"]
    Response --> Fetcher["8. SemanticDataFetcher<br>(Descarga decodificada & Mapeo empírico)"]
    Fetcher --> Data["DataFrame / Payload Limpio<br>(Valores float, Metadatos oficiales)"]
```

---

### 2. Ciclo de Vida del Servidor MCP

```mermaid
sequenceDiagram
    autonumber
    actor Client as Cliente MCP (Claude / Cursor / Agente AI)
    participant MCP as Servidor MCP (unofficial-cepalstat-mcp)
    participant Engine as SemanticResolutionEngine
    participant Fetcher as SemanticDataFetcher
    participant API as API Abierta CEPALSTAT

    Client->>MCP: Herramienta: resolve_indicator(query="salario minimo agricola en guatemala")
    MCP->>Engine: resolve("salario minimo agricola en guatemala")
    Engine-->>MCP: ALTERNATIVE_PROPOSED (ID 3337, Score: 0.65, Hint: "Salario mínimo real general")
    MCP-->>Client: Metadatos, advertencia de granularidad y score de confianza

    Client->>MCP: Herramienta: fetch_indicator_data(resolution_payload)
    MCP->>Fetcher: fetch_resolved_data(response)
    Fetcher->>API: GET /api/v1/indicator/3337/data (Parámetros oficiales decodificados)
    API-->>Fetcher: Registros tabulares crudos
    Fetcher-->>MCP: DataFrame procesado ("Guatemala", 2021, 104.2 índice)
    MCP-->>Client: JSON / Markdown estructurado anti-alucinaciones
```

---

## ⚡ Características Principales

### 1. Motor de Resolución Semántica (`SemanticResolutionEngine`)
- **Parsing de Intención Multidimensional:** Extrae automáticamente países (ISO3), períodos temporales (`SINGLE`, `RANGE`, `LIST`), periodicidad (`ANUAL`, `TRIMESTRAL`, `MENSUAL`) y facetas (`area`, `sexo`, `edad`, `quintil`, `etnia`).
- **Thesaurus Socioeconómico Latinoamericano:** Normalización de jergas y expresiones regionales (ej. *"chamba"*, *"pega"*, *"laburo"*, *"guaguas"*).
- **Detección de Polaridad y Conmutación de Facetas:** Clasifica inversiones de estado (*desempleo* vs *empleo*), complementos de facetas (*rural* vs *urbano*) y relaciones escalares.
- **Stage 3.5 Specificity Guard:** Protege contra falsas sustituciones. Si el usuario solicita un sector o especificidad ausente (*"telecomunicaciones"*, *"manufactura"*, *"gobierno general"*, *"déficit global"*, *"salario nominal"*, *"iva"*), el motor **nunca sustituye con score 1.0**:
  - Emite **`ALTERNATIVE_PROPOSED`** con score degradado ($0.65$) y advertencia conversacional si existe un indicador agregado relevante.
  - Se abstiene con **`ABSTAINED`** (`UNRESOLVED_SPECIFICITY`) si existe discrepancia categorial severa o el concepto está fuera de mandato (ej. tipos de cambio informales/blue, tasas de política monetaria o riqueza multimillonaria de Forbes).

### 2. Extractor y Fetcher Empírico (`SemanticDataFetcher`)
- **Mapeo Empírico de Producción:** Mapea automáticamente IDs de referencia al catálogo real de CEPALSTAT (ej. ID `3337` $\to$ tabla real `340`, o distribución del ingreso `3340` $\to$ `3324` por quintiles / `3390` por deciles).
- **Rescate de Puntos de Anclaje Temporal (Temporal Anchors):** Si se solicita un año intermedio ausente en encuestas de hogares, rescata los años oficiales observados inmediatamente adyacentes (*previous/next anchor*), marcando `forbid_interpolation: true` para impedir imputaciones numéricas falsas.
- **Normalización Invariante a Acentos y Mayúsculas:** Emparejamiento robusto de nombres de columnas y miembros dimensionales en Windows/Linux.

### 3. Validador Estadístico y Bitácoras Locales
- **Índice SQLite Local Ultra-Rápido (`.statscepal_cache.db`):** Búsqueda de fichas temáticas y catálogos en $< 1\text{ ms}$ con **cero llamadas a la red**, ahorrando más del 85% de tokens en contextos de LLM.
- **Control de Escala y Unidades:** Detección automática de factores de escala (*miles de personas*, *porcentaje del PIB*, *índice 2018=100*).

---

## 📊 Banco de Pruebas, Validación y Realidad Operativa

Un aspecto central de la transparencia metodológica de este proyecto es distinguir entre dos entornos de evaluación complementarios: **las suites de regresión determinista automatizadas (100% de precisión bajo especificación)** y **la evaluación empírica con usuarios humanos en prueba y error (~54% de tasa de fallo/abstención en lenguaje natural no restringido)**.

### 1. Suites de Regresión Determinista (Benchmarks Curados: 100% Top-1, 0.00% FSR)

El arnés de pruebas automatizado (`pytest`) ejecuta suites herméticas fuera de línea diseñadas para certificar invariantes matemáticos, evitar regresiones en releases y blindar el sistema contra alucinaciones estadísticas:

| Suite de Evaluación | Propósito Metodológico | Cantidad de Casos | Precisión Top-1 | Tasa de Sustitución Falsa (FSR) | Latencia Mediana ($p50$) |
|---|---|---|---|---|---|
| **Benchmark Canónico** | Dominios macroeconómicos y sociales clave (C1–C10) | 200 consultas | **100.0%** (200/200) | **0.00%** | $< 0.15\text{ ms}$ |
| **Benchmark Adversario** | Trampas de colisión léxica, polaridad y falsos amigos | 40 casos | **100.0%** (40/40) | **0.00%** | $0.74\text{ ms}$ |
| **Escala de Catálogo** | Cobertura transversal en las 23 áreas de CEPALSTAT | 100 consultas | **100.0%** (100/100) | **0.00%** | $< 0.40\text{ ms}$ |
| **Holdout Independiente** | Casos no vistos en optimización inicial | 50 consultas | **100.0%** (50/50) | **0.00%** | $< 0.30\text{ ms}$ |
| **Mutaciones Semánticas** | Pares perturbados para verificar sensibilidad | 54 pares | **100.0%** divergencia | **0.00%** | Hermético Offline |
| **Suite Completa de Regresión** | Pruebas unitarias, arquitectónicas y tipado | **551 tests** | **100.0%** pasados | **0.00%** | Hermético Offline |

> [!NOTE]
> **Sesgo de Curaduría y Adaptación Asistida (Curation Bias):**  
> El **100% de aprobación** en estas suites refleja que las preguntas fueron adaptadas e iteradas por agentes y desarrolladores para verificar que el pipeline respete las reglas ontológicas, los sinónimos y los grafos de desagregación formulados. Es una garantía de **no-regresión arquitectónica e integridad de invariantes**, no una métrica de generalización universal ante lenguaje libre arbitrario.
>
> Puedes auditar las especificaciones metodológicas en [`docs/reports/benchmark_200_preguntas.md`](docs/reports/benchmark_200_preguntas.md) y [`docs/reports/2026-10-18-adversarial-benchmark-specification.md`](docs/reports/2026-10-18-adversarial-benchmark-specification.md).

---

### 2. La Brecha del Lenguaje Natural: Evaluación Humana en Prueba y Error

En pruebas reales de usuario interactivo (*human-in-the-loop / exploratory testing*), donde analistas, economistas y usuarios formulan preguntas abiertas en lenguaje natural sin conocer la arquitectura interna del motor ni el vocabulario exacto de CEPALSTAT, el sistema presenta actualmente una **tasa de fallo o abstención aproximada del 54%** (es decir, una tasa de resolución directa inicial de **~46%**).

```mermaid
pie title Distribución Estimada en Pruebas Humanas Exploratorias
    "Resolución Directa Exitosa (46%)" : 46
    "Abstención por Sobre-especificación (24%)" : 24
    "Dispersión Léxica / Sinónimos Faltantes (15%)" : 15
    "Consultas Analíticas Compuestas (9%)" : 9
    "Incompatibilidad Dimensional Cruzada (6%)" : 6
```

---

### 3. Taxonomía Técnica de las Fallas en Consultas Humanas

El análisis de las consultas fallidas en sesiones de prueba y error revela cinco causas técnicas principales:

#### A. Dispersión Léxica y Variabilidad Regional (Lexical Drift)
* **Mecanismo:** En América Latina, la terminología socioeconómica varía marcadamente entre países e instituciones estadísticas. Un usuario peruano o argentino suele consultar por el *"PBI"* o *"producto bruto interno"* en lugar de *"PIB"* (recientemente incorporado como sinónimo regional). Otros términos comunes son *"presión tributaria"* (clasificado formalmente en CEPALSTAT como *"Ingresos tributarios del gobierno central como porcentaje del PIB"*), *"canasta básica"*, *"desocupación abierta"*, *"remuneraciones medias reales"* o *"tasa de actividad"*.
* **Impacto en el Motor:** Si una formulación no está explícitamente indexada en `DEFAULT_CANONICAL_SYNSETS` o en las expresiones regulares del `QueryParser`, los tokens no se absorben (`unconsumed_tokens`). Esto impide el enlace al concepto raíz o dispara precauciones de sobre-especificación.

#### B. Hiper-Conservadurismo del Guardián de Especificidad (Over-Abstention Bias)
* **Mecanismo:** Para garantizar de forma innegociable un **0.00% de Tasa de Sustitución Falsa (FSR)** —impidiendo que un asistente devuelva datos agregados haciéndolos pasar por el sector específico solicitado—, el motor aplica una política de *fail-closed* (`Stage 3.5 Specificity Guard`).
* **Impacto en el Motor:** Si el usuario incluye un modificador sectorial o metodológico ausente en la tabla nacional (ej. *"salario mínimo nominal"* cuando solo existe *"índice de salario mínimo real"*, o *"empleo en manufactura"* cuando solo existe *"empleo total"*), el motor emite `ABSTAINED` o `ALTERNATIVE_PROPOSED` con penalización de confianza ($0.65$). Desde la perspectiva de un usuario humano que espera una respuesta heurística o aproximada ("el mejor intento"), esta abstención metodológicamente segura suele percibirse como un fallo de resolución.

#### C. Incompatibilidad de Desagregaciones Cruzadas (Dimensional Entanglement)
* **Mecanismo:** Las tablas multidimensionales de CEPALSTAT no son cubos cartesianos completos. Una serie puede tener desagregación por `sexo`, y otra distinta por `área urbana/rural`, pero rara vez coexisten en la misma tabla ambas facetas a nivel subnacional o por quintil de ingreso.
* **Impacto en el Motor:** Consultas como *"desempleo juvenil rural femenino en Colombia"* combinan simultáneamente tres facetas (`edad`, `área`, `sexo`). Si no existe un indicador hijo en el grafo ontológico `BREAKDOWN_OF` con esa terna exacta, el motor rechaza la consulta para evitar amputar dimensiones silenciosamente.

#### D. Consultas Analíticas Compuestas vs. Series Atómicas
* **Mecanismo:** Los analistas humanos con frecuencia no buscan un indicador aislado, sino una relación econométrica o aritmética entre dos variables distintas:
  - *"Balanza comercial como porcentaje del PIB"*
  - *"Relación de deuda externa sobre reservas internacionales"*
  - *"Crecimiento del salario real descontando inflación"*
* **Impacto en el Motor:** El motor semántico opera actualmente a nivel de indicador atómico (`indicator_id`). Al no ser un motor de álgebra simbólica multi-tabla, las consultas compuestas no resuelven a menos que CEPALSTAT disponga de una serie precalculada específica.

#### E. Ambigüedad en Anclas Temporales y Filtros Implícitos
* **Mecanismo:** En lenguaje natural es habitual omitir el año asumiendo *"el dato más reciente disponible"* o emplear formulaciones cualitativas (*"en la postpandemia"*, *"última década"*, *"año actual"*).
* **Impacto en el Motor:** Si bien el parser soporta rangos y listas explícitas (`2015-2022`, `2020`), los términos temporales relativos o ausentes pueden dejar la serie sin filtro de año explícito, lo que en tablas censales o de encuestas de hogares (BADEHOG) puede disparar rescate de anclas o consultas con gran volumen de datos.

---

### 4. Hoja de Ruta Activa para Cerrar la Brecha

Para converger gradualmente la tasa de acierto en lenguaje libre hacia los niveles del benchmark curado, se están implementando las siguientes estrategias:

1. **Bucle de Aprendizaje Activo (Human-in-the-Loop Active Learning):**  
   Cada consulta fallida durante las pruebas manuales se cataloga y se incorpora progresivamente a nuevas suites de prueba, ampliando las 200 consultas canónicas hacia corpus dialectales más extensos.
2. **Expansión Sistemática de Sinónimos Multirregionales:**  
   Mapeo exhaustivo de nomenclaturas de los Institutos Nacionales de Estadística (INEGI, DANE, INDEC, INEI, INE) y Bancos Centrales de la región en la ontología de sinónimos.
3. **Resolución Híbrida Guiada por MCP (Agentic Dialogue):**  
   A través del protocolo MCP, el servidor no se abstiene de forma binaria muda, sino que retorna información de diagnóstico estructurada (`ALTERNATIVE_PROPOSED`, facetas faltantes, sugerencias de indicadores más cercanos). Esto permite que el LLM (Claude, Cursor, Antigravity) repregunte o negocie interactivamente con el usuario: *"CEPALSTAT no dispone de salario mínimo nominal para este país, pero dispone del Índice de Salario Mínimo Real (ID 3337). ¿Desea consultar esta serie?"*.
4. **Fallback Híbrido Tier-1 (Ontológico) / Tier-2 (FTS5 BM25 Catálogo Completo):**  
   Cuando una consulta no encaja en los conceptos prioritarios modelados ontológicamente, el motor activa automáticamente la búsqueda textual ponderada sobre los 1,739 indicadores del catálogo local SQLite, recuperando candidatos relevantes con baja latencia ($< 0.5\text{ ms}$).

---

## 📦 Instalación

### Desde PyPI
```bash
pip install unofficial-cepalstat-mcp
```

O ejecútalo directamente sin instalación previa con `uvx`:
```bash
uvx unofficial-cepalstat-mcp --help
```

### Para Desarrollo Local
El proyecto utiliza [`uv`](https://docs.astral.sh/uv/) como administrador de dependencias y entornos de alta velocidad en Python 3.10+.

```bash
# 1. Clonar el repositorio
git clone https://github.com/pcamacho447/unofficial-cepalstat-mcp.git
cd unofficial-cepalstat-mcp

# 2. Instalar dependencias con entorno virtual sincronizado
uv sync --extra dev
```

---

## 🐍 Uso en Python

```python
from unofficial_cepalstat_mcp import CepalStatClient, DataExtractor
from unofficial_cepalstat_mcp.semantic import SemanticDataFetcher, SemanticResolutionEngine

# 1. Resolución semántica determinista
engine = SemanticResolutionEngine()
res = engine.resolve_query("desempleo juvenil en chile 2020")
print(f"Estado: {res.status.value}")
if res.selected_candidate:
    print(f"Indicador: {res.selected_candidate.indicator_id} - {res.selected_candidate.name}")

# 2. Descarga empírica decodificada
fetcher = SemanticDataFetcher()
emp_data = fetcher.fetch_resolved_data(res)
print(f"Observaciones empíricas: {len(emp_data.get('series', []))}")
```

---

## 💻 Guía Rápida de Uso (CLI)

> [!TIP]
> Puedes invocar la CLI tanto con el comando canónico `unofficial-cepalstat-mcp` como con su alias corto `cepalstat-mcp`.

### 1. Resolución Semántica Explicada

Resuelve una consulta en lenguaje natural identificando el indicador oficial, facetas dimensionales y trazabilidad paso a paso:

```bash
uv run unofficial-cepalstat-mcp semantic resolve "desempleo juvenil urbano en argentina" --explain
```

Salida esperada:
```text
======================================================================
CEPALSTAT Semantic Resolution Engine
======================================================================
Query:     desempleo juvenil urbano en argentina
Status:    ABSTAINED
Reason:    UNSUPPORTED_FACET
Polarity:  STATE_INVERSION (Detected: 'desempleo', Expected Sign: UNSPECIFIED)
...
[Stage 4: Dimensional Gate] Canonical ID 3331 lacks facets: ['area'].
======================================================================
```

### 2. Propuesta de Alternativas con Degradación de Confianza

Cuando se solicita una especificidad que requiere advertencia (ej. salario agrícola):

```bash
uv run unofficial-cepalstat-mcp semantic resolve "salario minimo agricola en guatemala" --explain
```

Salida esperada:
```text
Status:    ALTERNATIVE_PROPOSED
Indicator: 3337 - Salario mínimo real (Measure: INDICE_REAL, Score: 0.65)
Hint:      Nota: Se propone como alternativa el indicador general 3337 ('Salario mínimo real'), pero la consulta solicitaba la especificidad: 'agricola'. Para el indicador sectorial consulte el catálogo de CEPALSTAT.
```

### 3. Descarga Empírica Decodificada

Descarga las observaciones desde CEPALSTAT con parámetros dimensionales resueltos:

```bash
uv run unofficial-cepalstat-mcp semantic resolve "pobreza extrema en chile en 2020" --fetch
```

### 4. Búsqueda Instantánea en el Catálogo Maestro

```bash
# Búsqueda instantánea en SQLite local (< 2 ms)
uv run unofficial-cepalstat-mcp search "pobreza" --limit 5

# Ver detalles oficiales del indicador 4788
uv run unofficial-cepalstat-mcp info 4788
```

---

## 🤖 Integración como Servidor MCP (Roadmap & Configuración)

El servidor MCP expone herramientas de inspección, resolución y descarga estadística para asistentes basados en LLMs:

### Herramientas MCP Planificadas:
- `cepalstat_semantic_resolve`: Resuelve consultas en lenguaje natural a indicadores de CEPALSTAT con trazabilidad y detección de alternativas.
- `cepalstat_fetch_data`: Extrae DataFrames decodificados con rescate de anclas temporales.
- `cepalstat_catalog_search`: Búsqueda instantánea en el catálogo temático de más de 1,739 indicadores.
- `cepalstat_indicator_methodology`: Consulta notas técnicas, unidades de medida y fuentes primarias de cada serie.

### Ejemplo de Configuración en Claude Desktop / Cursor / Antigravity:

Ejecución directa mediante `uvx`:
```json
{
  "mcpServers": {
    "cepalstat": {
      "command": "uvx",
      "args": [
        "unofficial-cepalstat-mcp",
        "mcp"
      ]
    }
  }
}
```

O en desarrollo local:
```json
{
  "mcpServers": {
    "cepalstat": {
      "command": "uv",
      "args": [
        "--directory",
        "/ruta/a/unofficial-cepalstat-mcp",
        "run",
        "unofficial-cepalstat-mcp",
        "mcp"
      ]
    }
  }
}
```

---

## 🧪 Ejecución de Pruebas

Para reproducir las métricas de rendimiento y verificación:

```bash
# Ejecutar la suite completa no integrada (551 tests herméticos offline)
uv run pytest -m "not integration"

# Ejecutar el benchmark canónico de 200 casos
uv run pytest tests/test_semantic_benchmark_200.py -v

# Ejecutar el benchmark adversarial de 40 casos
uv run pytest tests/test_adversarial_benchmark_40.py -v -s

# Ejecutar la batería completa de benchmarks semánticos (390 casos + 54 mutaciones)
uv run pytest tests/test_semantic_benchmark_200.py tests/test_adversarial_benchmark_40.py tests/test_catalog_scale_benchmark_100.py tests/test_independent_holdout_benchmark_50.py tests/test_semantic_mutations.py -v
```

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulte el archivo [LICENSE](LICENSE) para más detalles.  
Las series y datos de CEPALSTAT están sujetos a las políticas de datos abiertos de la [Comisión Económica para América Latina y el Caribe (CEPAL)](https://statistics.cepal.org/portal/cepalstat/open-data.html?lang=es).
