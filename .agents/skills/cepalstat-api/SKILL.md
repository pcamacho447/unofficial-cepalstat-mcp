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

---

## 3-Step Query Workflow

CEPALSTAT indicators are multidimensional cubes (Country x Year x Breakdown). Querying data requires a three-step progression:

```
[1. Search Indicator]  -->  [2. Resolve Dimensions & Members]  -->  [3. Fetch Records / DataFrame]
```

### Step 1: Search and Discover Indicators
Find the indicator ID by keyword search across the thematic tree hierarchy.

**Using CLI:**
```bash
statscepal search "pobreza" --limit 10
statscepal search "poblacion"
```

**Using Python Client:**
```python
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

## Python SDK Reference (`statscepal`)

### `CepalStatClient`
- `client = CepalStatClient(base_url="https://api-cepalstat.cepal.org", language="es", timeout=30.0)`
- Methods: `client.get(endpoint, params=None)`
- Context manager supported: `with CepalStatClient() as client: ...`

### `ThematicTree`
- `tree = ThematicTree(client)`
- `tree.get_tree(force_refresh=False) -> list[ThematicNode]`
- `tree.search(keyword) -> list[IndicatorSearchResult]`

### `DimensionManager`
- `manager = DimensionManager(client)`
- `manager.get_dimensions(indicator_id, force_refresh=False) -> list[Dimension]`
- `manager.find_member_id(indicator_id, dimension_name_or_id, member_name) -> int | None`

### `DataExtractor`
- `extractor = DataExtractor(client, dimension_manager=None)`
- `extractor.get_metadata(indicator_id) -> dict[str, Any]`
- `extractor.get_records(indicator_id, members=None) -> list[dict[str, Any]]`
- `extractor.get_dataframe(indicator_id, members=None, decode_labels=True) -> pd.DataFrame`

---

## REST Endpoints Overview

| Endpoint | Method | Description |
|---|---|---|
| `/cepalstat/api/v1/thematic-tree` | `GET` | Thematic tree hierarchy containing areas, sub-themes, and indicator IDs |
| `/cepalstat/api/v1/indicator/{id}/metadata` | `GET` | Technical note, definition, measurement unit, calculation methodology |
| `/cepalstat/api/v1/indicator/{id}/dimensions` | `GET` | Available dimensions and member hierarchy for an indicator |
| `/cepalstat/api/v1/indicator/{id}/records` | `GET` | Observation values, source, and dimension values for the indicator |
