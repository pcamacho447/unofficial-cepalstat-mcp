---
name: cepalstat-api
description: Use when querying, searching, analyzing, or retrieving socioeconomic, demographic, economic, or environmental statistics for Latin America and the Caribbean from UN CEPAL / ECLAC CEPALSTAT Open Data API.
---

# CEPALSTAT Open Data API Skill

This skill guides agents in discovering, querying, and analyzing official statistical indicators for Latin America and the Caribbean published by the United Nations Economic Commission for Latin America and the Caribbean (CEPAL / ECLAC) via the CEPALSTAT Open Data API.

## Quick Reference

- **Base URL:** `https://api-cepalstat.cepal.org`
- **Authentication:** None required (Public Open Data)
- **Supported Formats:** JSON (default), CSV, Excel, SDMX-ML
- **Supported Languages:** Spanish (`es`, default), English (`en`)
- **Dimensions Reference:** [dimensions-reference.md](references/dimensions-reference.md) for standard country and year member IDs
- **Protocol:** "Bitácora First" — always check certified recipes before making exploratory API calls to optimize token usage and eliminate bias.

---

## Query Workflow: "Bitácora First" Protocol

CEPALSTAT indicators are multidimensional cubes (Country x Year x Breakdown). To minimize API latency, maximize token optimization, and eliminate demographic or geographic bias, follow the Bitácora First query workflow:

```
[Step 0: Bitácora Lookup] ──(Recipe found)──> [Reuse Certified Member IDs & Code]
           │
      (Not found)
           ▼
[Step 1: Search Indicator] ──> [Step 2: Resolve Dimensions] ──> [Step 3: Fetch Data] ──> [Step 4: Certify Recipe]
```

---

### Step 0: Bitácora Primero (Token Optimization & Anti-Sesgo)
Before performing any exploratory queries against the CEPALSTAT API, check the local Bitácora of certified recipes:
- **Run lookup first:** `statscepal bitacora lookup "<query>" --country "<pais>"`
- **Token Optimization:** Reusing a certified recipe avoids exploratory API queries, saving thousands of LLM tokens and accelerating response times.
- **Anti-Bias / Anti-Sesgo:** Certified recipes include audit metrics (quality, geographic coverage, demographic breakdown) to eliminate hallucinated member IDs and representation bias.

**Using CLI:**
```bash
statscepal bitacora lookup "pobreza" --country "Chile"
statscepal bitacora lookup "desempleo"
statscepal bitacora list
```

**Using Python:**
```python
from statscepal.bitacora import BitacoraStore

store = BitacoraStore()
recipes = store.lookup(query="pobreza", country="Chile")
if recipes:
    recipe = recipes[0]
    print(f"Certified Recipe: {recipe.indicator_name} (ID: {recipe.indicator_id})")
    print(f"Members: {recipe.member_ids}")
    # Reuse certified code snippet directly
    print(recipe.python_code)
```

**Decision Rule:**
- **If a certified recipe exists:** Immediately reuse the certified member IDs and code snippet (avoids full API exploration and eliminates hallucination/bias risk).
- **If not found:** Execute standard API search (Steps 1-3).

---

### Step 1: Search and Discover Indicators (Master Catalog & Offline Search)
Find the indicator ID by keyword search across the master catalog or thematic tree hierarchy.

**Offline Master Indicator Catalog (~2,000 Indicators):**
The master catalog indexes ~2,000 indicators in a local SQLite database, categorized across Demográficos, Económicos, Ambientales, and Temas transversales.
- **Fast Offline Search:** `statscepal search` operates offline using the local SQLite index of ~2,000 indicators with zero network requests and sub-millisecond response times.
- **Explicit Catalog Search:** `statscepal catalog search <query>` provides dedicated catalog queries with optional thematic area filtering (`--theme`) and limit (`--limit`).
- **Catalog Statistics:** `statscepal catalog stats` displays indicator totals and distribution across thematic areas.

**Using CLI:**
```bash
# Standard search (operates offline using local SQLite index of ~2,000 indicators)
statscepal search "pobreza" --limit 10
statscepal search "poblacion"

# Dedicated master catalog search (supports optional --theme and --limit)
statscepal catalog search "desempleo"
statscepal catalog search "pib" --theme "Económicos" --limit 10

# Master catalog statistics
statscepal catalog stats
```

**Using Python Client:**
```python
# Offline master catalog search
from statscepal.catalog import CatalogStore

catalog = CatalogStore()
results = catalog.search("desempleo", limit=5)
for item in results:
    print(f"[{item.indicator_id}] {item.name} - Path: {item.full_path}")

# Check catalog statistics
stats = catalog.get_stats()
print(f"Total indicators: {stats.total_indicators}")

# Online thematic tree search fallback
from statscepal import CepalStatClient, ThematicTree

with CepalStatClient() as client:
    tree = ThematicTree(client)
    results = tree.search("desempleo")
    for item in results[:5]:
        print(f"[{item.indicator_id}] {item.name} - Path: {item.path}")
```

**Using Direct REST API:**
```http
GET https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree?lang=es&format=json
```

---

### Step 2: Resolve Dimensions and Member IDs
Indicators break down data by dimensions (e.g. `País__ESTANDAR`, `Años__ESTANDAR`, `Sexo`, `Área geográfica`). To filter or decode results, query the indicator's dimensions.

**Using Python Client:**
```python
from statscepal import CepalStatClient, DimensionManager

with CepalStatClient() as client:
    manager = DimensionManager(client)
    dims = manager.get_dimensions(indicator_id=4788)
    for dim in dims:
        print(f"Dimension: {dim.name} (ID: {dim.id})")
        for member in dim.members[:5]:
            print(f"   Member: {member.name} -> ID: {member.id}")

    # Or lookup member ID directly:
    chile_id = manager.find_member_id(4788, "País", "Chile")       # 224
    year_2020 = manager.find_member_id(4788, "Años", "2020")        # 29190
```

**Using Reference Table for Fast Lookup:**
Consult [dimensions-reference.md](references/dimensions-reference.md) for standard member IDs:
- **Countries (`dim_208`):** Total ALC: `208`, Argentina: `218`, Brasil: `222`, Chile: `224`, Colombia: `225`, México: `238`, etc.
- **Years (`dim_29117`):** 2018: `29188`, 2019: `29189`, 2020: `29190`, 2021: `29191`, 2022: `29192`, 2023: `29193`, 2024: `29194`.

**Using Direct REST API:**
```http
GET https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/{indicator_id}/dimensions?lang=es&format=json
```

---

### Step 3: Fetch Data and Extract Insights
Retrieve data records filtered by member IDs. Data can be exported to CSV or processed as a Pandas DataFrame with human-readable decoded dimension labels.

**Using CLI:**
```bash
# View metadata
statscepal info 4788

# Fetch table to stdout
statscepal fetch 4788 --members 224,29190

# Export table to CSV
statscepal fetch 4788 --members 224,29190 --csv output.csv
```

**Using Python Client:**
```python
from statscepal import CepalStatClient, DataExtractor

with CepalStatClient() as client:
    extractor = DataExtractor(client)

    # 1. Indicator metadata
    metadata = extractor.get_metadata(indicator_id=4788)
    print("Indicator:", metadata.get("indicator_name"))
    print("Unit:", metadata.get("unit"))

    # 2. DataFrame with automatically decoded dimension labels
    # e.g. converts dim_208=224 -> País__ESTANDAR="Chile"
    df = extractor.get_dataframe(
        indicator_id=4788,
        members=[224, 29190], # Chile, 2020
        decode_labels=True
    )
    print(df.head())
```

**Using Direct REST API:**
```http
# Metadata
GET https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/{indicator_id}/metadata?lang=es&format=json

# Records
GET https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/{indicator_id}/records?members={member_id1},{member_id2}&lang=es&format=json
```

---

### Step 4: Certify New Recipes (Save to Bitácora)
Once a new indicator query has been successfully explored and verified via Steps 1-3, certify it into the local Bitácora so future agents and workflows can reuse it directly without token overhead or bias risks:

**Using CLI:**
```bash
statscepal bitacora add <id> --country <c> --tags <t1,t2>
```
Examples:
```bash
# Certify with specific member IDs and tags
statscepal bitacora add 4788 --country "Chile" --members 224,29190 --tags "pobreza,nacional"

# Auto-audit and certify indicator
statscepal bitacora add 5011 --country "Brasil" --tags "empleo,desempleo"
```

The command automatically audits data quality and demographic/geographic anti-bias metrics, generates a reproducible Python code snippet, and saves the certified recipe to markdown and the SQLite lookup index.

---

## Motor de Resolución Semántica Multidimensional (CLI & API)

El paquete incorpora un motor determinístico y ultrarrápido ($p50 < 0.5\text{ ms}$) para resolver lenguaje natural a coordenadas formales de CEPALSTAT sin alucinación y con 0.00% de Tasa de Sustitución Falsa (FSR):

```bash
# Resolución de indicador canónico y filtros
statscepal semantic resolve "cual es la pobreza en el peru en 2020"

# Resolución con desglose multidimensional (etnia, género, etc.)
statscepal semantic resolve "cual es la pobreza etnica en el peru del 2020"

# Resolución con extracción de datos empíricos de la API
statscepal semantic resolve "tasa de pobreza indigena en bolivia 2021" --fetch

# Series temporales multi-anuales y ventanas relativas
statscepal semantic resolve "pobreza en chile los ultimos 4 anos" --fetch
```

### Mapeo de Indicadores Multidimensionales Clave:
- **Pobreza Agregada / Área:** `3328` (*Población en situación de pobreza extrema y pobreza, por área*)
- **Pobreza Étnica / Racial:** `3342` (*Población en situación de pobreza extrema y pobreza, por sexo, autoidentificación étnico-racial y área*)
  - Dimensión `43039` (`Tipo de etnia`): Miembros `43041` (Indígena), `43042` (Afrodescendiente), `43044` (No indígena ni afrodescendiente), `43043` (Total).

---

## Python SDK Reference (`statscepal`)

### `CepalStatClient`
- `client = CepalStatClient(base_url="https://api-cepalstat.cepal.org", language="es", timeout=30.0)`
- Methods: `client.get(endpoint, params=None)`
- Context manager supported: `with CepalStatClient() as client: ...`

### `ThematicTree`
- `tree = ThematicTree(client)`
- `tree.get_tree(force_refresh=False) -> list[ThematicNode]`
- `tree.search(keyword) -> list[IndicatorSearchResult]`

### `CatalogStore`
- `store = CatalogStore(db_path=None)`
- `store.search(query="", theme=None, limit=20) -> list[CatalogIndicator]`
- `store.get_stats() -> CatalogStats`
- `store.is_built() -> bool`
- `store.build(force=False) -> int`
- `store.export(filepath, format=None) -> Path`

### `DimensionManager`
- `manager = DimensionManager(client)`
- `manager.get_dimensions(indicator_id, force_refresh=False) -> list[Dimension]`
- `manager.find_member_id(indicator_id, dimension_name_or_id, member_name) -> int | None`

### `DataExtractor`
- `extractor = DataExtractor(client, dimension_manager=None)`
- `extractor.get_metadata(indicator_id) -> dict[str, Any]`
- `extractor.get_records(indicator_id, members=None) -> list[dict[str, Any]]`
- `extractor.get_dataframe(indicator_id, members=None, decode_labels=True) -> pd.DataFrame`

### `BitacoraStore`
- `store = BitacoraStore(recipes_dir=None, db_path=None)`
- `store.lookup(query="", country=None, tag=None) -> list[BitacoraRecipe]`
- `store.list_recipes() -> list[BitacoraRecipe]`
- `store.save_recipe(recipe: BitacoraRecipe) -> Path`
- `store.sync() -> int`

### `AntiBiasValidator`
- `quality, antibias = AntiBiasValidator.audit(df, metadata=meta)`
- Returns `QualityMetrics` and `AntiBiasReport` with bias audit checks (geographic, demographic, null rates).

---

## REST Endpoints Overview

| Endpoint | Method | Description |
|---|---|---|
| `/cepalstat/api/v1/thematic-tree` | `GET` | Thematic tree hierarchy containing areas, sub-themes, and indicator IDs |
| `/cepalstat/api/v1/indicator/{id}/metadata` | `GET` | Technical note, definition, measurement unit, calculation methodology |
| `/cepalstat/api/v1/indicator/{id}/dimensions` | `GET` | Available dimensions and member hierarchy for an indicator |
| `/cepalstat/api/v1/indicator/{id}/records` | `GET` | Observation values, source, and dimension values for the indicator |
