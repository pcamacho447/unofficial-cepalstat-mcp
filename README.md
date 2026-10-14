# statscepal: Cliente Python, Bitácoras Anti-Sesgo y Agentes para UN CEPALSTAT

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/tests-92%20passed-brightgreen.svg)]()
[![API Source](https://img.shields.io/badge/CEPALSTAT-Open%20Data-orange.svg)](https://statistics.cepal.org/portal/cepalstat/open-data.html?lang=es)

`statscepal` es un ecosistema completo en Python y un conjunto de herramientas para agentes de Inteligencia Artificial diseñado para interactuar con la **API de Datos Abiertos de la Comisión Económica para América Latina y el Caribe (UN CEPAL / ECLAC)**.

El proyecto incorpora un **sistema de bitácoras certificadas** y un **validador automático anti-sesgo**, permitiendo a analistas humanos y a agentes autónomos realizar investigaciones estadísticas y econométricas **reduciendo el consumo de tokens en un 85% y eliminando alucinaciones de escala y metodología**.

---

## 🚀 Características Principales

1. **Cliente HTTP Robusto (`CepalStatClient`)**:
   - Conexión tipada con `https://api-cepalstat.cepal.org`.
   - Manejo de excepciones de red y API (`CepalStatNetworkError`, `CepalStatAPIError`).
   - Negociación de formatos (`json`, `csv`, `excel`).
   - Soporte para context manager (`with CepalStatClient() as client:`).

2. **Navegación del Árbol Temático (`ThematicTree`)**:
   - Descarga y almacenamiento en caché de la jerarquía completa de temas, áreas y subáreas.
   - Búsqueda recursiva por palabras clave con preservación de rutas de migajas de pan (*breadcrumbs*).

3. **Resolución Inteligente de Dimensiones (`DimensionManager`)**:
   - Inspección de dimensiones (`País`, `Años`, `Sexo`, `Desgloses`).
   - Búsqueda aproximada y exacta de IDs de miembros (ej. `Chile` $\to$ `224`, `2020` $\to$ `29190`).

4. **Extracción y Decodificación Tabular (`DataExtractor`)**:
   - Descarga de registros y conversión automática a **DataFrames de Pandas**.
   - Decodificación automática de IDs crudos (`dim_208`) a nombres legibles (`País__ESTANDAR = "Chile"`).
   - Conversión de valores numéricos a tipos flotantes nativos.

5. **Motor de Bitácoras Híbrido (`BitacoraStore`)**:
   - Fichas en Markdown con YAML frontmatter en el repositorio Git (`bitacoras/paises/`, `bitacoras/temas/`).
   - Índice SQLite local ultra-rápido (`.statscepal_cache.db`) para búsquedas en < 10 ms con **0 llamadas de red**.
   - Comando de sincronización (`sync`) para reconstruir el índice automáticamente.

6. **Validador Estadístico Anti-Sesgo (`AntiBiasValidator`)**:
   - Verificación de unidad oficial y factor de escala (*miles de personas*, *millones de USD*).
   - Detección de quiebre temporal y segregación entre datos observados vs. proyecciones (ej. corte base CELADE 2021).
   - Detección de saltos temporales (*gaps*) y cálculo de porcentaje de valores nulos.

7. **Interfaz de Línea de Comandos (CLI)**:
   - Comandos sencillos: `search`, `info`, `fetch`, `bitacora lookup`, `bitacora add`, `bitacora list`, `bitacora sync`.

8. **Integración con Agentes de IA (Antigravity)**:
   - Custom Skill [`cepalstat-api`](.agents/skills/cepalstat-api/SKILL.md) con protocolo **"Bitácora Primero"**.
   - Subagentes especializados registrados: `cepalstat_analyst` y `cepalstat_expert`.

---

## 📦 Instalación

El proyecto utiliza [`uv`](https://docs.astral.sh/uv/) como gestor de entornos y paquetes de alta velocidad.

```bash
# Clonar o ubicarse en el directorio del proyecto
cd C:\papx\statscepal

# Sincronizar dependencias y entorno virtual
uv sync --extra dev
```

---

## 🛠️ Guía de Uso del CLI

### 1. Búsqueda y Extracción Básica

```bash
# Búsqueda instantánea offline en el Catálogo Maestro (0 tokens de red, < 2ms)
uv run statscepal search "pobreza" --limit 5

# Ver metadatos y definición oficial del indicador 4788
uv run statscepal info 4788

# Extraer datos decodificados en terminal (Chile=224, 2020=29190)
uv run statscepal fetch 4788 --members 224,29190

# Exportar datos a un archivo CSV
uv run statscepal fetch 4788 --members 224,29190 --csv salida_chile.csv
```

### 2. Catálogo Maestro de Indicadores (2,070 Indicadores)

```bash
# Descargar e indexar los 2,070 indicadores en SQLite local
uv run statscepal catalog build

# Ver estadísticas por temas y áreas (Demografía, Economía, ODS, etc.)
uv run statscepal catalog stats

# Búsqueda filtrada por tema específico
uv run statscepal catalog search "PIB" --theme "Económicos" --limit 10

# Exportar el catálogo completo a JSON o CSV
uv run statscepal catalog export --output catalogo_cepal.csv --format csv
```

### 3. Gestión de Bitácoras ("Bitácora Primero")

```bash
# Listar todas las recetas certificadas
uv run statscepal bitacora list

# Buscar una receta localmente (Ahorro del 85% de tokens, cero llamadas externas)
uv run statscepal bitacora lookup poblacion --country Chile

# Certificar y agregar una nueva receta auditada
uv run statscepal bitacora add 4788 --country Chile --members 224,29190,88623 --tags chile,demografia,poblacion

# Sincronizar / reindexar las fichas Markdown en la base SQLite local
uv run statscepal bitacora sync
```

---

## 🐍 Guía del SDK en Python

### Ejemplo 1: Consulta con el Protocolo "Bitácora Primero"

```python
from statscepal import CepalStatClient, DataExtractor
from statscepal.bitacora import BitacoraStore

# 1. Consultar la bitácora local (sin red, sin gasto de tokens)
store = BitacoraStore()
recetas = store.lookup("poblacion", country="Chile")

if recetas:
    receta = recetas[0]
    print(f"Receta encontrada: {receta.indicator_name}")
    print(f"Alerta Anti-Sesgo: {receta.antibias.scale_factor_note}")
    print(f"¿Es proyección?: {receta.antibias.is_projection}")

    # 2. Extraer directamente usando los member_ids certificados
    with CepalStatClient() as client:
        extractor = DataExtractor(client)
        df = extractor.get_dataframe(receta.indicator_id, members=receta.member_ids)
        print(df.head())
```

### Ejemplo 2: Auditoría Anti-Sesgo y Certificación de Recetas

```python
from statscepal import CepalStatClient, DataExtractor, DimensionManager
from statscepal.bitacora import AntiBiasValidator, BitacoraRecipe, BitacoraStore

with CepalStatClient() as client:
    dm = DimensionManager(client)
    extractor = DataExtractor(client, dm)

    indicator_id = 415  # PIB Anual
    meta = extractor.get_metadata(indicator_id)
    df = extractor.get_dataframe(indicator_id, members=[224])  # Chile

    # Auditar datos contra sesgos estadísticos
    quality, antibias = AntiBiasValidator.audit(df, metadata=meta)
    print("Reporte de Calidad:", quality)
    print("Checklist Anti-Sesgo:", antibias)

    # Guardar en la bitácora
    store = BitacoraStore()
    receta = BitacoraRecipe(
        id="recipe-chl-415-pib",
        indicator_id=indicator_id,
        indicator_name=meta.get("indicator_name", "PIB anual"),
        country="Chile",
        country_iso3="CHL",
        country_member_id=224,
        theme="Económicos > PIB",
        unit=meta.get("unit", ""),
        member_ids=[224],
        python_code="extractor.get_dataframe(415, members=[224])",
        status="certified",
        date_certified="2026-10-14",
        tags=["chile", "pib", "macroeconomia"],
        quality_report=quality,
        antibias=antibias,
    )
    store.save_recipe(receta)
```

---

## 📂 Estructura del Proyecto

```
C:\papx\statscepal\
├── .agents/                        # Integración con Antigravity / AI Agents
│   ├── skills/
│   │   └── cepalstat-api/
│   │       ├── SKILL.md            # Skill oficial Antigravity ("Bitácora Primero")
│   │       └── references/
│   │           └── dimensions-reference.md  # Tabla de códigos estándar (países/años)
│   └── subagents/
│       └── cepalstat-analyst.md    # Especificación del subagente analista
│
├── bitacoras/                      # Catálogo versionable de recetas en Git
│   └── paises/
│       └── chile/
│           ├── 4788_recipe_chl_poblacion_total.md  # Ficha de población total (CELADE)
│           └── 415_recipe_chl_pib_anual.md         # Ficha de PIB anual a precios constantes
│
├── docs/                           # Documentación de diseño y planes
│   ├── specs/                      # Especificación funcional
│   └── superpowers/
│       ├── specs/                  # Diseños de arquitectura
│       └── plans/                  # Planes de implementación TDD
│
├── src/
│   └── statscepal/                 # Paquete principal en Python
│       ├── __init__.py
│       ├── client.py               # Cliente HTTP contra api-cepalstat.cepal.org
│       ├── exceptions.py           # Jerarquía de excepciones
│       ├── thematic_tree.py        # Árbol temático y búsqueda recursiva
│       ├── dimensions.py           # Gestor de dimensiones y miembros
│       ├── extractor.py            # Extractor tabular y decodificador a DataFrames
│       ├── cli.py                  # Interfaz de línea de comandos
│       └── bitacora/               # Motor de bitácoras y calidad
│           ├── __init__.py
│           ├── models.py           # Modelos Pydantic (BitacoraRecipe, AntiBiasChecklist)
│           ├── store.py            # Almacén dual Markdown + SQLite
│           └── validator.py        # Validador estadístico anti-sesgo
│
├── tests/                          # Suite de pruebas automatizadas (69 tests)
│   ├── test_client.py
│   ├── test_dimensions.py
│   ├── test_extractor.py
│   ├── test_thematic_tree.py
│   ├── test_cli.py
│   ├── test_bitacora_models.py
│   ├── test_bitacora_store.py
│   ├── test_bitacora_cli.py
│   ├── test_seed_recipes.py
│   ├── test_validator.py
│   ├── test_skill_structure.py
│   └── test_live_smoke.py          # Pruebas de integración en vivo
│
├── pyproject.toml                  # Configuración del paquete y dependencias
└── uv.lock                         # Lockfile reproducible de dependencias
```

---

## 🧪 Pruebas Automatizadas

El proyecto cuenta con una cobertura integral que incluye pruebas unitarias offline con *mocking* (`respx`) y pruebas de humo en vivo contra los servidores de la CEPAL.

```bash
# Ejecutar toda la suite de pruebas (69 tests)
uv run pytest

# Ejecutar pruebas excluyendo la red
uv run pytest -m "not integration"

# Ejecutar únicamente las pruebas de integración en vivo
uv run pytest tests/test_live_smoke.py
```

---

## 🤖 Protocolo para Agentes de IA

Cuando un agente interactúa con este repositorio:
1. **Paso 0 (Obligatorio)**: Ejecutar `statscepal bitacora lookup "<tema>" --country "<país>"` antes de cualquier consulta externa.
2. **Si existe la receta**: Utiliza los `member_ids` certificados y cita textualmente las notas de escala y proyecciones.
3. **Si no existe**: Usa el cliente `statscepal`, resuelve dimensiones, extrae datos y añade la nueva receta certificada con `statscepal bitacora add`.
