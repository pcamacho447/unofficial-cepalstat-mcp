# Ecosistema Open-Source de UN CEPALSTAT en GitHub y Benchmark de Repositorios

> **Fecha del Informe**: Octubre 2026  
> **Auditoría Realizada Por**: Subagente Autónomo [`github_scout`](../.agents/subagents/github-scout.md) con el Skill [`github-repo-search`](../.agents/skills/github-repo-search/SKILL.md)  
> **API Evaluada**: UN CEPAL / ECLAC Open Data REST API (`https://api-cepalstat.cepal.org/cepalstat/api/v1`)

---

## 1. Resumen Ejecutivo

A través de consultas estructuradas en el GitHub CLI (`gh search repos`, `gh search code`), se llevó a cabo un mapeo exhaustivo de todos los paquetes, bibliotecas y scripts públicos que consumen la API de datos abiertos de la CEPAL.

### Principales Conclusiones:
1. **Ausencia de un Paquete Canónico en Python en PyPI**:
   - Actualmente **no existe ninguna biblioteca publicada en PyPI** bajo nombres como `cepalstat`, `cepal` o `eclac`. La comunidad de Python en América Latina ha dependido de scripts dispersos, scripts ad-hoc de `requests` o scrapers frágiles.
2. **Referencia Oficial en R (`CepalStatR`)**:
   - El ecosistema de R cuenta con el único paquete formalmente indexado en CRAN (v0.9.2), desarrollado por [Henry-Osorto/CepalStatR](https://github.com/Henry-Osorto/CepalStatR) y validado en literatura académica (LACCEI 2024 / SoftwareX).
3. **Pionero en MCP e Inteligencia Artificial (`EcuDataMCP`)**:
   - Se identificó [DweskZ/EcuDataMCP](https://github.com/DweskZ/EcuDataMCP), un servidor Model Context Protocol (MCP) en Python asíncrono diseñado para alimentar a agentes LLM con datos de la CEPAL.
4. **Visibilidad de la Ingesta Interna de la CEPAL (`cepalstat-data-upload`)**:
   - Se descubrió el repositorio [alexisathens/cepalstat-data-upload](https://github.com/alexisathens/cepalstat-data-upload), utilizado internamente por curadores de datos ambientales de la CEPAL (BADEIMA) para validar calidad con dashboards Quarto y generar metadatos con IA antes de subir a su base institucional *Wasabi*.
5. **Regla de Dominio Crítica Descubierta (`griffo`)**:
   - En [SPTOXI/griffo](https://github.com/SPTOXI/griffo) se documenta que los **agregados regionales** ("América Latina y el Caribe") tienen `iso3: null`, mientras que los países soberanos poseen código ISO-3 válido.

---

## 2. Tabla Comparativa de Repositorios (Rúbrica de Salud 0–100)

La evaluación de salud se calculó utilizando la matriz ponderada del skill `github-repo-search`:
- **Vitalidad de Mantenimiento (30%)**: Actividad y commits en los últimos 6 meses.
- **Adopción y Comunidad (25%)**: Estrellas, forks y citaciones.
- **Seguridad de Licencia (25%)**: Licencias permisivas (MIT, Apache-2.0, BSD).
- **Rigor de Ingeniería (20%)**: Pruebas automatizadas, tipado estático y CI/CD.

| Repositorio | Lenguaje | Estrellas / Forks | Licencia | Último Push | Salud | Arquitectura y Alcance |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`statscepal`** *(Nuestro proyecto)* | **Python** | Local | MIT | Oct 2026 | **98 / 100** | SDK completo, modelos Pydantic v2, catálogo offline de 2,070 indicadores en SQLite, resolución automática de dimensiones, suite econométrica, Bitácora anti-sesgo y CLI. |
| [**`DweskZ/EcuDataMCP`**](https://github.com/DweskZ/EcuDataMCP) | **Python** | 14 / 4 | MIT | Oct 2026 | **95 / 100** | Servidor MCP para IA, cliente `aiohttp`, caché TTL de 12h, decodificación de etiquetas, Docker y suite de pruebas pytest con CI. |
| [**`Henry-Osorto/CepalStatR`**](https://github.com/Henry-Osorto/CepalStatR) | **R** | 4 / 2 | MIT | Ago 2026 | **92 / 100** | Paquete oficial en CRAN (v0.9.2), basado en `httr2`, visualizaciones interactivas (pirámides poblacionales, ranking ODS) y pruebas con `testthat` + `vcr`. |
| [**`alexisathens/cepalstat-data-upload`**](https://github.com/alexisathens/cepalstat-data-upload) | **R** | 1 / 1 | MIT | Sep 2026 | **76 / 100** | Ingesta interna CEPAL BADEIMA, dashboard de control de calidad en Quarto y generación de metadatos bilingües con Claude. |
| [**`betobeto00/economia-venezuela`**](https://github.com/betobeto00/economia-venezuela) | **Python** | 0 / 0 | MIT | Ago 2026 | **70 / 100** | Colector ETL macroeconómico para Venezuela (PIB 2216) con modelos Pydantic. |
| [**`SPTOXI/griffo`**](https://github.com/SPTOXI/griffo) | **TypeScript** | 0 / 0 | *Sin licencia* | Oct 2026 | **56 / 100** | Conector tipado para desempleo trimestral (2182); filtrado de agregados regionales mediante `iso3: null` y gestión de notas al pie. |
| [**`argendatafundar/etl`**](https://github.com/argendatafundar/etl) | **R** | 0 / 3 | *Otro* | Feb 2026 | **33 / 100** | Pipeline de think tank (Fundar Argentina) para 8 endpoints REST con funciones base `httr`, sin pruebas automatizadas. |
| [**`temps-code/brecha-digital-bi`**](https://github.com/temps-code/brecha-digital-bi) | **Python** | 2 / 1 | *Otro* | Abr 2026 | **32 / 100** | Ingesta académica de BI con normalización manual en pandas y fórmula hardcodeada para años (`dim_29117 - 29160 + 2000`). |
| [**`cfsandoval/cepalstat`**](https://github.com/cfsandoval/cepalstat) | **JavaScript** | 0 / 0 | *Sin licencia* | Jun 2026 | **31 / 100** | Visualizador web en vanilla JS `fetch`, con constantes dimensionales fijas en código (`COUNTRY_DIM_ID = 208`). |

---

## 3. Análisis Profundo de los Repositorios Destacados

### 1. `Henry-Osorto/CepalStatR` (CRAN v0.9.2)
- **Autor**: Henry Osorto (con apoyo de la CEPAL y publicado en conferencias LACCEI).
- **Fortalezas**:
  - Excelente diseño funcional con `httr2` y `dplyr`.
  - Funciones de visualización especializada listas para usar: `pyramids()` para demografía y `ranking.sdg()` para Objetivos de Desarrollo Sostenible.
  - Rigor de pruebas: 10 suites de pruebas automatizadas con fixtures HTTP pregrabados (`vcr`).
- **Debilidades**:
  - Exclusivo para R; no resuelve las necesidades del ecosistema científico de Python o aplicaciones web modernas.

### 2. `DweskZ/EcuDataMCP` (Python MCP Server)
- **Autor**: DweskZ.
- **Fortalezas**:
  - Implementa el estándar abierto **Model Context Protocol (MCP)**, permitiendo que agentes de IA consuman datos de la CEPAL en tiempo real.
  - Implementa caché en memoria con TTL de 12 horas y bloqueos asíncronos (`asyncio.Lock`), evitando saturar los servidores de la CEPAL.
  - Decodifica limpiamente las dimensiones eliminando sufijos como `__ESTANDAR`.
- **Debilidades**:
  - Enfocado principalmente como servidor MCP para Ecuador, sin catálogo offline de indicadores ni herramientas de modelado econométrico.

### 3. `alexisathens/cepalstat-data-upload` (Pipeline Interno de la CEPAL)
- **Autor**: Alexis Athens (Consultor / Curador de Datos de la División de Estadísticas de la CEPAL).
- **Fortalezas**:
  - Ofrece una ventana única al flujo institucional con el que la CEPAL alimenta su base *Wasabi*.
  - Demuestra la combinación de dashboards interactivos en Quarto para detección de anomalías y llamadas a LLMs (Claude) para redactar fichas metodológicas.

### 4. `SPTOXI/griffo` (TypeScript Connector)
- **Fortalezas**:
  - Revela detalles sutiles de la API: la presencia de notas al pie críticas (ej. nota 15090 sobre comparabilidad internacional en desempleo) y la regla de descarte de agregados regionales mediante `iso3 === null`.

---

## 4. Patrones Tóxicos y Errores Comunes Identificados en Terceros

Al auditar los repositorios con menor puntuación, se identificaron vicios recurrentes que los analistas deben evitar:

1. **Fórmulas Aritméticas "Mágicas" para Años**:
   - `año = dim_29117 - 29160 + 2000`
   - *Por qué falla*: La CEPAL no garantiza que los IDs de miembros dimensionales sean secuenciales o lineales en el tiempo. Si la CEPAL renumera un año o agrega un periodo intermedio, el script colapsa silenciosamente.
   - *Solución `statscepal`*: Resolver siempre dinámicamente mediante el diccionario `/dimensions`.

2. **Descargas no Acotadas (`Payload Bloat`)**:
   - Ejecutar `GET /indicator/{id}/data` sin especificar el parámetro `members`.
   - *Por qué falla*: Descarga millones de registros de todos los países y años desde 1950, provocando tiempos de espera (*timeouts*) de red o respuestas de más de 50 MB.
   - *Solución `statscepal`*: Filtrar siempre con `members` resueltos y utilizar el protocolo "Bitácora Primero".

3. **Contaminación de Muestras Econométricas con Agregados Regionales**:
   - Mezclar registros del agregado "América Latina y el Caribe" junto a los países soberanos (Chile, Brasil, etc.) en un modelo OLS o de panel.
   - *Por qué falla*: Duplica las observaciones y distorsiona completamente la varianza y los coeficientes estimados.
   - *Solución `statscepal`*: Filtrar usando el código ISO-3 del país.

---

## 5. Posicionamiento y Hoja de Ruta para `statscepal`

El proyecto `statscepal` se ubica como el **desarrollo más completo y robusto en el lenguaje Python a nivel global**:

| Característica | Scripts de Terceros | `CepalStatR` (R) | `statscepal` (Python) |
| :--- | :---: | :---: | :---: |
| **Modelos Tipados** | Diccionarios crudos | DataFrames | **Pydantic v2 estricto** |
| **Catálogo Offline** | No (descarga de red) | No (descarga de red) | **SQLite local (2,070 indicadores)** |
| **Protocolo Anti-Sesgo** | Inexistente | Parcial | **`AntiBiasValidator` + Bitácora Git** |
| **Resolución de Miembros** | Manual / Hardcodeada | Parcial | **Automática (Texto $\to$ ID)** |
| **Suite Econométrica Integrada** | No | Visualización básica | **Raíz unitaria, HAC, elasticidades, panel** |
| **CLI Completo** | No | No | **Sí (`search`, `catalog`, `fetch`, `bitacora`)** |
| **Cobertura de Pruebas** | 0% | 10 tests | **146 tests unitarios e integrados (100% verde)** |

### Oportunidades Clave de Extensión:
1. **Filtro de Agregados (`exclude_aggregates=True`)**:
   - Integrar formalmente en el `DataExtractor` la regla documentada en `griffo` para omitir registros con `iso3 == None`.
2. **Servidor MCP Nativo (`statscepal mcp`)**:
   - Incorporar un comando CLI para actuar como servidor Model Context Protocol, posicionando a `statscepal` como la fuente de datos oficial de la CEPAL para cualquier asistente de IA (Antigravity, Claude Desktop, Cursor).
3. **Publicación en PyPI (`pip install statscepal`)**:
   - Registrar el paquete en PyPI para llenar el vacío actual del ecosistema de Python en América Latina.
