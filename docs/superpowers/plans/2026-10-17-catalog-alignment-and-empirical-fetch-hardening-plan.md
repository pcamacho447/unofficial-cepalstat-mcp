# Catalog Alignment & Empirical Fetch Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate synthetic indicator and member ID collisions during `--fetch`, align `VERTICAL_SLICE_INDICATORS` with real CEPALSTAT `master_indicators` IDs, improve multi-country and decade column extraction in `SemanticDataFetcher`, and add support for Latin American demonyms (gentilicios) and demographic/ethnic population queries (`4788`, `4968`, `4969`, `4992`, `4639`).

**Architecture:** We introduce an explicit `EMPIRICAL_INDICATOR_ID_MAP` in `src/statscepal/semantic/registry.py` and `SYNTHETIC_DIMENSION_MEMBER_IDS` filtering in `SemanticDataFetcher` so that offline benchmark indicator IDs remain 100% backward-compatible while `--fetch` always queries the true CEPALSTAT API indicator ID without colliding on mock member IDs (such as `79578` colliding with Chile in `2929`). We enhance `SemanticDataFetcher` to prioritize human-readable country columns (`Países_agregados regionales especiales VAR IPC`, `País__ESTANDAR`) over `iso3` while using both `iso3` and formal UN name matching (`Bolivia (Estado Plurinacional de)`) for filtering, and to parse `'Década'` columns (`Década 2010` -> `2010`). Finally, we expand `COUNTRY_LEXICON` with Latin American demonyms (`peruana`, `chileno`, `mexicano`, etc.) and register demographic/ethnic population indicators (`4788, 4968, 4969, 4992, 4639`) with multi-member breakdown support for `ETNICO_TOTAL`.

**Tech Stack:** Python 3.10+, Pydantic v2, Pandas, SQLite3, Pytest.

**Spec:** `docs/reports/resumen_avances_motor_semantico.md`

## Global Constraints

- Python 3.10+ modern typing syntax (`list[str]`, `dict[str, Any]`, `str | None`).
- All non-integration tests (295+) must pass without regression.
- False Substitution Rate must strictly equal `0.00%` across the 200-question benchmark (`tests/test_semantic_benchmark_200.py`).
- Top-1 Accuracy across the 200 benchmark test cases and 70 facet-coverage cases must strictly remain `100.0%`.
- Local resolution latency over SQLite and in-memory thesaurus must maintain `p50 < 0.5 ms`.
- Safe UTF-8 encoding and accent normalization (`_strip_accents`) for Windows console environments.
- Strict offline hermeticity: unit test suites must NEVER perform live network calls to CEPALSTAT.

---

### File Structure & Responsibilities

- `src/statscepal/semantic/registry.py`:
  - Define `EMPIRICAL_INDICATOR_ID_MAP: dict[int, int]` mapping synthetic `official_25` indicator IDs (`2928, 2930, 729, 730, 731, 2447, 3331, 3344, 128, 3337, 3339, 3340, 3345, 1241, 1242, 1243, 1244, 5683, 4406, 1318, 3333, 2949, 2954`) to their real CEPALSTAT `master_indicators` IDs (`2484, 4145, 2204, 2206, 286, 5097, 341, 340, 2287, 3390, 5698, 1246, 821, 740, 883, 3154, 460, 3097, 2288, 2050`).
  - Define `SYNTHETIC_DIMENSION_MEMBER_IDS: frozenset[int]` listing synthetic member IDs from `DEFAULT_OFFICIAL_DIMENSIONS` that must not be passed as raw `members=` integers to the live CEPALSTAT API.
  - Register demographic and ethnic population indicators (`4788, 4968, 4969, 4992, 4639`) in `VERTICAL_SLICE_INDICATORS` and `DEFAULT_OFFICIAL_DIMENSIONS`.
- `src/statscepal/semantic/fetcher.py`:
  - Map synthetic indicator IDs via `EMPIRICAL_INDICATOR_ID_MAP` before calling `_load_indicator_data`, and strip `SYNTHETIC_DIMENSION_MEMBER_IDS` from `member_ids` sent to the API.
  - Prioritize substring country columns (`"país"`, `"pais"`, `"country_name"`) ahead of `"iso3"` / `"country_code"` so `Países_agregados regionales especiales VAR IPC` is selected as `country_col` for display, while combining `country_col` (including formal UN parenthetical names like `Bolivia (Estado Plurinacional de)`) AND `iso3` column matching in Step 1 country filtering.
  - Support `"decada"` / `"década"` as a temporal column (`year_col`) and extract 4-digit years from strings like `'Década 2010'`.
- `src/statscepal/semantic/facet_ontology.py`:
  - Add `ETNICO_TOTAL` to `breakdown_values` of the `etnia` facet and add a `MemberMatchRule` for `ETNICO_TOTAL` (`is_breakdown=True`) matching `("indigena", "no indigena", "afrodescendiente", "no afrodescendiente", "no indigena ni afrodescendiente")`.
- `src/statscepal/semantic/parser.py`:
  - Add Latin American demonyms (gentilicios) to `COUNTRY_LEXICON` (`peruano`, `peruana`, `chileno`, `chilena`, `mexicano`, `mexicana`, `colombiano`, `colombiana`, `argentino`, `argentina`, `brasileno`, `ecuatoriano`, `boliviano`, `uruguayo`, `paraguayo`, `venezolano`, `costarricense`, `panameno`, etc.).
  - Add `POBLACION` root concept detection when `"poblacion"`, `"habitantes"`, or `"demografia"` is queried without another primary socioeconomic root concept.
- `src/statscepal/semantic/engine.py`:
  - Add `"POBLACION": [4788, 4968, 4992, 4969, 4639]` to `CONCEPT_TO_INDICATORS` and route `POBLACION` candidates based on `etnia` and `estrato` facets (`INDIGENA` / `ETNICO_TOTAL` -> `4968`, `AFRODESCENDIENTE` -> `4969`, `estrato` + `etnia` -> `4639`, default -> `4788`).
- `tests/test_semantic_fetcher.py` & `tests/test_semantic_breakdowns.py`:
  - Add unit tests covering synthetic `member_id` stripping (`79578` on `2929`), empirical indicator ID mapping (`2928 -> 2484`), `Países_agregados regionales especiales VAR IPC` multi-country extraction, `'Década 2010'` parsing, demonym extraction (`"poblacion peruana"` -> `PER`), and ethnic population breakdown resolution (`4968`).

---

### Task 1: Empirical Indicator ID Mapping & Synthetic `member_id` Isolation

**Files:**
- Modify: `src/statscepal/semantic/registry.py:195-210`
- Modify: `src/statscepal/semantic/fetcher.py:170-210`
- Test: `tests/test_semantic_fetcher.py`

**Interfaces:**
- Produces:
  - `EMPIRICAL_INDICATOR_ID_MAP: dict[int, int]` and `SYNTHETIC_DIMENSION_MEMBER_IDS: frozenset[int]` in `src/statscepal/semantic/registry.py`.
  - `SemanticDataFetcher._resolve_empirical_indicator_id(self, response: SemanticResolutionResponse) -> int` in `src/statscepal/semantic/fetcher.py`.

- [ ] **Step 1: Write the failing tests in `tests/test_semantic_fetcher.py`**

Append the following tests to `tests/test_semantic_fetcher.py`:

```python
def test_fetcher_strips_synthetic_member_ids_to_prevent_api_country_collision():
    """Verify synthetic member_id 79578 in 2929 is NOT passed to API get_dataframe, preventing Chile-only filtering."""
    from unittest.mock import MagicMock
    import pandas as pd
    from statscepal.extractor import DataExtractor
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    res = engine.resolve(
        "necesito los datos de la inflacion de alimentos de mexico, peru, argentina, chile, colombia y paraguay del año 2018 al 2023"
    )

    mock_extractor = MagicMock(spec=DataExtractor)
    mock_extractor.get_dataframe.return_value = pd.DataFrame([
        {"iso3": "MEX", "Países_agregados regionales especiales VAR IPC": "México", "Años__ESTANDAR": 2022, "value": 14.1, "notes_ids": ""},
        {"iso3": "PER", "Países_agregados regionales especiales VAR IPC": "Perú", "Años__ESTANDAR": 2022, "value": 15.2, "notes_ids": ""},
        {"iso3": "CHL", "Países_agregados regionales especiales VAR IPC": "Chile", "Años__ESTANDAR": 2022, "value": 21.0, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher(extractor=mock_extractor)
    payload = fetcher.fetch_resolved_data(res)

    # Synthetic member_id 79578 must be stripped so members=None is passed to get_dataframe
    mock_extractor.get_dataframe.assert_called_once_with(2929, members=None)
    assert payload["observation_exists"] is True
    assert len(payload["series"]) == 3
    assert [r["country"] for r in payload["series"]] == ["México", "Perú", "Chile"]


def test_fetcher_maps_synthetic_indicator_2928_to_real_cepalstat_2484():
    """Verify synthetic indicator ID 2928 (IPC general in official_25) maps to real CEPALSTAT ID 2484 during fetch."""
    from unittest.mock import MagicMock
    import pandas as pd
    from statscepal.extractor import DataExtractor
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    res = engine.resolve(
        "necesito los datos de la inflacion de peru, argentina, chile, colombia y paraguay del año 2018 al 2023"
    )
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 2928

    mock_extractor = MagicMock(spec=DataExtractor)
    mock_extractor.get_dataframe.return_value = pd.DataFrame([
        {"iso3": "PER", "Países_agregados regionales especiales VAR IPC": "Perú", "Años__ESTANDAR": 2022, "value": 8.46, "notes_ids": ""},
        {"iso3": "CHL", "Países_agregados regionales especiales VAR IPC": "Chile", "Años__ESTANDAR": 2022, "value": 12.8, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher(extractor=mock_extractor)
    payload = fetcher.fetch_resolved_data(res)

    mock_extractor.get_dataframe.assert_called_once_with(2484, members=None)
    assert payload["observation_exists"] is True
    assert payload["empirical_indicator_id"] == 2484
    assert len(payload["series"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_fetcher.py -k "test_fetcher_strips_synthetic_member_ids or test_fetcher_maps_synthetic_indicator_2928" -v`
Expected: FAIL (`AssertionError: Expected call: get_dataframe(2929, members=None), Actual call: get_dataframe(2929, members=[79578])`).

- [ ] **Step 3: Define `EMPIRICAL_INDICATOR_ID_MAP` and `SYNTHETIC_DIMENSION_MEMBER_IDS` in `src/statscepal/semantic/registry.py` and integrate in `src/statscepal/semantic/fetcher.py`**

In `src/statscepal/semantic/registry.py` (right after `DEFAULT_OFFICIAL_DIMENSIONS` around line 202):
```python
# Synthetic member IDs defined in DEFAULT_OFFICIAL_DIMENSIONS for offline Stage 4 matching
# that must not be sent as raw integer filters to the live CEPALSTAT API records endpoint.
SYNTHETIC_DIMENSION_MEMBER_IDS: frozenset[int] = frozenset({
    300, 301, 302,
    327, 330, 331,
    412, 413, 414, 415,
    501, 502,
    601, 602, 603, 604, 605, 610, 611, 612, 613,
    701,
    79578, 79580,
})

# Mapping from synthetic/placeholder official_25 indicator IDs to real CEPALSTAT master_indicators IDs
EMPIRICAL_INDICATOR_ID_MAP: dict[int, int] = {
    2928: 2484,  # Tasa de crecimiento anual del índice de precios al consumidor: diciembre a diciembre
    2930: 4145,  # Tasa de crecimiento anual del índice de precios al consumidor subyacente: diciembre a diciembre
    729: 2204,   # Producto interno bruto (PIB) total anual a precios constantes en dólares
    730: 2206,   # Producto interno bruto (PIB) total anual por habitante a precios constantes en dólares
    731: 286,    # Producto interno bruto trimestral por tipo del gasto a precios constantes
    2447: 286,   # Producto interno bruto trimestral
    3331: 5097,  # Tasa de desempleo, por sexo y edad - 19ª CIET (%)
    3344: 5097,  # Tasa de desocupación según sexo y edad
    128: 341,    # Salario medio real anual
    3337: 340,   # Salario mínimo real
    3339: 2287,  # Ingreso medio de la población ocupada, por sexo e inserción laboral
    3345: 5698,  # Ingreso medio de la población ocupada, por sexo, autoidentificación étnico-racial y área
    3340: 3390,  # Distribución del ingreso de los hogares, por deciles y área
    1241: 1246,  # Operaciones del gobierno (clasificación económica), en porcentajes del PIB
    1242: 821,   # Ingresos tributarios por tipo de impuestos en porcentajes del PIB
    1243: 740,   # Saldo en cuenta corriente como porcentaje del producto interno bruto
    1244: 883,   # Índices de la relación de precios del intercambio y poder de compra de las exportaciones
    5683: 3154,  # Proporción de energía renovable en la oferta de energía primaria
    4406: 460,   # Gasto público en educación
    1318: 3097,  # Porcentaje de población que utiliza fuentes mejoradas de abastecimiento de agua
    3333: 2288,  # Relación del ingreso medio entre mujeres y hombres, por grupo de edad y área
    2949: 2050,  # Balanza de pagos
    2954: 883,   # Índices de la relación de precios del intercambio
}
```

In `src/statscepal/semantic/fetcher.py`:
1. Import `EMPIRICAL_INDICATOR_ID_MAP, SYNTHETIC_DIMENSION_MEMBER_IDS` from `statscepal.semantic.registry`.
2. Add method `_resolve_empirical_indicator_id(self, response: SemanticResolutionResponse) -> int`:
   ```python
   def _resolve_empirical_indicator_id(
       self, response: SemanticResolutionResponse
   ) -> int:
       """Map synthetic vertical-slice indicator IDs to verified real CEPALSTAT indicator IDs."""
       assert response.selected_candidate is not None
       ind_id = response.selected_candidate.indicator_id
       if ind_id == 3340:
           estrato = response.applied_filters.facets.get("estrato", "")
           if estrato == "RELACION_Q5_Q1":
               return 3295
           if "QUINTIL" in estrato:
               return 3324
           return 3390
       return EMPIRICAL_INDICATOR_ID_MAP.get(ind_id, ind_id)
   ```
3. In `fetch_resolved_data`:
   - Compute `empirical_id = self._resolve_empirical_indicator_id(response)`.
   - Filter out `SYNTHETIC_DIMENSION_MEMBER_IDS` when building `member_ids`:
     ```python
     raw_member_ids: list[int] = []
     for f in response.applied_filters.dimensions:
         if getattr(f, "is_breakdown", False) and getattr(f, "member_ids", None):
             raw_member_ids.extend(f.member_ids)
         elif f.member_id is not None:
             raw_member_ids.append(f.member_id)
     member_ids = [
         m for m in raw_member_ids if m not in SYNTHETIC_DIMENSION_MEMBER_IDS
     ]
     df = self._load_indicator_data(empirical_id, member_ids)
     ```
   - Include `"empirical_indicator_id": empirical_id` in `payload`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_semantic_fetcher.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/semantic/registry.py src/statscepal/semantic/fetcher.py tests/test_semantic_fetcher.py
git commit -m "feat(semantic): map synthetic indicator IDs to real CEPALSTAT IDs and strip synthetic member IDs"
```

---

### Task 2: Robust Country Column Priority, UN Formal Country Name Matching & Decade Period Parsing in `SemanticDataFetcher`

**Files:**
- Modify: `src/statscepal/semantic/fetcher.py:21-66,225-275,390-415`
- Test: `tests/test_semantic_fetcher.py`

**Interfaces:**
- Consumes: `SemanticDataFetcher.fetch_resolved_data` in `src/statscepal/semantic/fetcher.py`.
- Produces:
  - Prioritized human-readable country column detection (`"país"`, `"pais"`, `"country_name"` before `"iso3"` / `"country_code"`), combined `country_col` (including formal UN parenthetical names like `"Bolivia (Estado Plurinacional de)"`) + `iso3` filtering in Step 1.
  - `_extract_numeric_years(series: pd.Series) -> pd.Series` supporting both integer years (`2020`) and decade strings (`"Década 2010"` -> `2010`), plus `"decada"` / `"década"` in `_STRUCTURAL_AND_META_COLS` and `year_col` discovery.

- [ ] **Step 1: Write the failing tests in `tests/test_semantic_fetcher.py`**

Append the following tests to `tests/test_semantic_fetcher.py`:

```python
def test_fetcher_matches_un_formal_country_names_and_displays_human_country_column():
    """Verify fetcher matches Bolivia (Estado Plurinacional de) via iso3/prefix and displays human country name over iso3."""
    import pandas as pd
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    res = engine.resolve("inflacion de alimentos en bolivia y chile del 2021 al 2022")

    mock_df = pd.DataFrame([
        {"iso3": "BOL", "Países_agregados regionales especiales VAR IPC": "Bolivia (Estado Plurinacional de)", "Años__ESTANDAR": 2021, "value": 0.9, "notes_ids": ""},
        {"iso3": "BOL", "Países_agregados regionales especiales VAR IPC": "Bolivia (Estado Plurinacional de)", "Años__ESTANDAR": 2022, "value": 4.2, "notes_ids": ""},
        {"iso3": "CHL", "Países_agregados regionales especiales VAR IPC": "Chile", "Años__ESTANDAR": 2021, "value": 5.7, "notes_ids": ""},
        {"iso3": "CHL", "Países_agregados regionales especiales VAR IPC": "Chile", "Años__ESTANDAR": 2022, "value": 21.0, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher()
    fetcher._load_indicator_data = lambda ind_id, member_ids=None: mock_df

    payload = fetcher.fetch_resolved_data(res)
    assert payload["observation_exists"] is True
    series = payload["series"]
    assert len(series) == 4
    countries = {r["country"] for r in series}
    assert "Bolivia (Estado Plurinacional de)" in countries
    assert "Chile" in countries


def test_fetcher_parses_decada_column_as_temporal_dimension():
    """Verify fetcher recognizes 'Década' column (e.g. 'Década 2010', 'Década 2020') as year_col and extracts numeric year."""
    import pandas as pd
    from statscepal.semantic.fetcher import SemanticDataFetcher
    from statscepal.semantic.models import (
        AppliedFilters,
        ResolutionStatus,
        SelectedCandidate,
        SemanticResolutionResponse,
    )

    res = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="poblacion indigena en peru",
        selected_candidate=SelectedCandidate(
            indicator_id=4968,
            name="Población Indígena y no indígena según área de residencia",
            unit="personas",
        ),
        applied_filters=AppliedFilters(
            country_code="PER",
            country_name="Perú",
        ),
    )

    mock_df = pd.DataFrame([
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2010", "Area Geografica": "Total", "Condición Indígena": "Total", "value": 23820599.0, "notes_ids": ""},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2020", "Area Geografica": "Total", "Condición Indígena": "Total", "value": 26500000.0, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher()
    fetcher._load_indicator_data = lambda ind_id, member_ids=None: mock_df

    payload = fetcher.fetch_resolved_data(res)
    assert payload["observation_exists"] is True
    assert payload["year"] == 2020
    assert payload["value"] == 26500000.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_fetcher.py -k "test_fetcher_matches_un_formal_country_names or test_fetcher_parses_decada_column" -v`
Expected: FAIL (`country` is `'BOL'`/`'CHL'` instead of human names, and `payload["year"] == 0` instead of `2020`).

- [ ] **Step 3: Implement country column priority, dual `iso3`/prefix matching, and `Década` parsing in `src/statscepal/semantic/fetcher.py`**

In `src/statscepal/semantic/fetcher.py`:
1. Add `"decada"`, `"década"`, `"países_agregados regionales especiales var ipc"`, `"paises_agregados regionales especiales var ipc"`, `"total quintiles"`, `"total deciles"` to `_STRUCTURAL_AND_META_COLS` and `_AGGREGATE_MEMBER_PRIORITY`.
2. Add static/helper method `_extract_numeric_years(series: pd.Series) -> pd.Series`:
   ```python
   def _extract_numeric_years(series: pd.Series) -> pd.Series:
       """Convert a year or decade Series (e.g., 2020 or 'Década 2010') into numeric years."""
       num = pd.to_numeric(series, errors="coerce")
       if num.notna().any():
           return num
       extracted = series.astype(str).str.extract(r"(1\d{3}|20\d{2})", expand=False)
       return pd.to_numeric(extracted, errors="coerce")
   ```
3. In Step 1 (`Filter by country if specified`), check substring `"país"` / `"pais"` / `"country"` BEFORE falling back to `"iso3"` / `"country_code"`:
   ```python
   if country_col is None:
       for col in filtered_df.columns:
           cl = col.lower()
           if ("pais" in cl or "país" in cl or "country" in cl) and cl not in ("country_code",):
               country_col = col
               break

   if country_col is None:
       for candidate in ("iso3", "country_code"):
           for col in filtered_df.columns:
               if col.lower() == candidate:
                   country_col = col
                   break
           if country_col is not None:
               break
   ```
   And when building `mask` for country filtering, match against `country_col` (including prefix match `col_norm.str.startswith(norm_target_name + " (")`) AND also check any `iso3` / `country_code` column present in `filtered_df`:
   ```python
   mask = pd.Series(False, index=filtered_df.index)
   if country_col is not None:
       col_str = filtered_df[country_col].astype(str).str.strip()
       if target_country_names:
           col_norm = col_str.map(_strip_accents)
           for t_name in target_country_names:
               norm_target_name = _strip_accents(t_name)
               mask |= (col_norm == norm_target_name) | col_norm.str.startswith(norm_target_name + " (")
       if target_country_codes:
           col_upper = col_str.str.upper()
           for t_code in target_country_codes:
               mask |= (col_upper == t_code.strip().upper())
   for iso_cand in ("iso3", "country_code"):
       if iso_cand in filtered_df.columns and target_country_codes:
           iso_upper = filtered_df[iso_cand].astype(str).str.strip().str.upper()
           for t_code in target_country_codes:
               mask |= (iso_upper == t_code.strip().upper())
   if country_col is not None or any(c in filtered_df.columns for c in ("iso3", "country_code")):
       filtered_df = filtered_df[mask]
   ```
4. In Step 3 (`Identify year column`), include `"decada"` in the keyword tuple `("year", "anio", "ano", "anios", "anos", "period", "periodo", "decada")` and use `_extract_numeric_years` whenever converting `filtered_df[year_col]` or extracting `row_year`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_semantic_fetcher.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/semantic/fetcher.py tests/test_semantic_fetcher.py
git commit -m "feat(semantic): prioritize human country columns, match UN formal names, and parse decade columns"
```

---

### Task 3: Latin American Demonyms in `COUNTRY_LEXICON` & Demographic/Ethnic Population Resolution (`4788`, `4968`, `4969`, `4992`, `4639`)

**Files:**
- Modify: `src/statscepal/semantic/parser.py:27-88,710-720`
- Modify: `src/statscepal/semantic/facet_ontology.py:55-120,260-310`
- Modify: `src/statscepal/semantic/registry.py:195-210,635-655`
- Modify: `src/statscepal/semantic/engine.py:45-100,190-240`
- Test: `tests/test_semantic_breakdowns.py`

**Interfaces:**
- Produces:
  - Demonym recognition in `COUNTRY_LEXICON` (`peruano/a`, `chileno/a`, `mexicano/a`, `colombiano/a`, `argentino/a`, `brasileno/a`, `ecuatoriano/a`, `boliviano/a`, `uruguayo/a`, `paraguayo/a`, `venezolano/a`, `costarricense`, `panameno/a`, `guatemalteco/a`, `hondureno/a`, `salvadoreno/a`, `nicaraguense`, `dominicano/a`, `cubano/a`, `haitiano/a`).
  - `POBLACION` root concept and indicators `4788`, `4968`, `4992`, `4969`, `4639` with `ETNICO_TOTAL` breakdown support.

- [ ] **Step 1: Write the failing tests in `tests/test_semantic_breakdowns.py`**

Append the following tests to `tests/test_semantic_breakdowns.py`:

```python
def test_ethnic_population_query_with_demonym_resolves_to_indigenous_population_breakdown():
    """Verify 'necesito datos etnicos de la poblacion peruana' extracts PER from 'peruana' and resolves to 4968 with ethnic breakdown."""
    engine = SemanticResolutionEngine()

    res = engine.resolve("necesito datos etnicos de la poblacion peruana")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.applied_filters.country_code == "PER"
    assert res.applied_filters.country_name == "Perú"
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4968
    assert res.applied_filters.facets.get("etnia") == "ETNICO_TOTAL"
    etnia_dims = [
        d for d in res.applied_filters.dimensions
        if "indígena" in d.dim_name.lower() or "etnia" in d.dim_name.lower()
    ]
    assert len(etnia_dims) == 1
    assert etnia_dims[0].is_breakdown is True
    assert "Indígena" in etnia_dims[0].member_names


def test_specific_population_queries_route_to_total_indigenous_and_afrodescendant_indicators():
    """Verify total, indigenous, and afrodescendant population queries resolve to 4788, 4968, and 4969."""
    engine = SemanticResolutionEngine()

    res_tot = engine.resolve("poblacion total de chile en 2022")
    assert res_tot.status == ResolutionStatus.RESOLVED
    assert res_tot.selected_candidate is not None
    assert res_tot.selected_candidate.indicator_id == 4788
    assert res_tot.applied_filters.country_code == "CHL"

    res_ind = engine.resolve("poblacion indigena en bolivia")
    assert res_ind.status == ResolutionStatus.RESOLVED
    assert res_ind.selected_candidate is not None
    assert res_ind.selected_candidate.indicator_id == 4968
    assert res_ind.applied_filters.country_code == "BOL"

    res_afro = engine.resolve("poblacion afrodescendiente en brasil")
    assert res_afro.status == ResolutionStatus.RESOLVED
    assert res_afro.selected_candidate is not None
    assert res_afro.selected_candidate.indicator_id == 4969
    assert res_afro.applied_filters.country_code == "BRA"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_breakdowns.py -k "test_ethnic_population_query_with_demonym or test_specific_population_queries_route" -v`
Expected: FAIL (`res.status == ResolutionStatus.ABSTAINED`).

- [ ] **Step 3: Implement demonyms, `POBLACION` indicators, and `ETNICO_TOTAL` breakdown**

1. In `src/statscepal/semantic/parser.py`:
   - Add Latin American demonyms to `COUNTRY_LEXICON`:
     ```python
     "brasileño": "BRA", "brasileno": "BRA", "brasilena": "BRA", "brasilenos": "BRA", "brasilenas": "BRA",
     "colombiano": "COL", "colombiana": "COL", "colombianos": "COL", "colombianas": "COL",
     "chileno": "CHL", "chilena": "CHL", "chilenos": "CHL", "chilenas": "CHL",
     "mexicano": "MEX", "mexicana": "MEX", "mexicanos": "MEX", "mexicanas": "MEX",
     "argentino": "ARG", "argentinos": "ARG", "argentinas": "ARG",
     "uruguayo": "URY", "uruguaya": "URY", "uruguayos": "URY", "uruguayas": "URY",
     "costarricense": "CRI", "costarricenses": "CRI",
     "peruano": "PER", "peruana": "PER", "peruanos": "PER", "peruanas": "PER",
     "ecuatoriano": "ECU", "ecuatoriana": "ECU", "ecuatorianos": "ECU", "ecuatorianas": "ECU",
     "boliviano": "BOL", "boliviana": "BOL", "bolivianos": "BOL", "bolivianas": "BOL",
     "panameno": "PAN", "panamena": "PAN", "panamenos": "PAN", "panamenas": "PAN",
     "paraguayo": "PRY", "paraguaya": "PRY", "paraguayos": "PRY", "paraguayas": "PRY",
     "hondureno": "HND", "hondurena": "HND", "hondurenos": "HND", "hondurenas": "HND",
     "guatemalteco": "GTM", "guatemalteca": "GTM", "guatemaltecos": "GTM", "guatemaltecas": "GTM",
     "salvadoreno": "SLV", "salvadorena": "SLV", "salvadorenos": "SLV", "salvadorenas": "SLV",
     "nicaraguense": "NIC", "nicaraguenses": "NIC",
     "dominicano": "DOM", "dominicana": "DOM", "dominicanos": "DOM", "dominicanas": "DOM",
     "venezolano": "VEN", "venezolana": "VEN", "venezolanos": "VEN", "venezolanas": "VEN",
     "cubano": "CUB", "cubana": "CUB", "cubanos": "CUB", "cubanas": "CUB",
     "haitiano": "HTI", "haitiana": "HTI", "haitianos": "HTI", "haitianas": "HTI",
     ```
   - At the end of Step 5 in `QueryParser.parse` (right after `elif "gini" in clean or "desigualdad" in clean:`):
     ```python
     elif any(term in clean for term in ["poblacion", "habitantes", "demografia", "demografico", "demograficos"]):
         intent.root_concept = "POBLACION"
     ```
2. In `src/statscepal/semantic/facet_ontology.py`:
   - In the `"etnia"` `FacetDefinition`:
     - Add `"condicion indigena"` and `"condicion afrodescendiente"` to `dimension_name_Keywords`.
     - Set `breakdown_values=frozenset({"ETNICO_TOTAL"})`.
     - Add `MemberMatchRule` for `ETNICO_TOTAL`:
       ```python
       MemberMatchRule(
           canonical_value="ETNICO_TOTAL",
           exact_matches=(
               "indigena",
               "no indigena",
               "afrodescendiente",
               "no afrodescendiente",
               "no indigena ni afrodescendiente",
           ),
           is_breakdown=True,
       ),
       ```
3. In `src/statscepal/semantic/registry.py`:
   - Add `4788`, `4968`, `4969`, `4992`, and `4639` to `DEFAULT_OFFICIAL_DIMENSIONS`:
     ```python
     4788: [
         Dimension(
             id=88622,
             name="Sexo",
             members=[Member(id=88623, name="Ambos sexos"), Member(id=88626, name="Hombres"), Member(id=88627, name="Mujeres")],
         ),
     ],
     4968: [
         Dimension(
             id=48525,
             name="Area Geografica",
             members=[Member(id=48529, name="Total"), Member(id=48526, name="Urbano"), Member(id=48528, name="Rural")],
         ),
         Dimension(
             id=78149,
             name="Condición Indígena",
             members=[Member(id=78150, name="Indígena"), Member(id=78152, name="No Indígena"), Member(id=78154, name="Total")],
         ),
     ],
     4969: [
         Dimension(
             id=48525,
             name="Area Geografica",
             members=[Member(id=48529, name="Total"), Member(id=48526, name="Urbano"), Member(id=48528, name="Rural")],
         ),
         Dimension(
             id=140625,
             name="Condición Afrodescendiente",
             members=[Member(id=140626, name="Afrodescendiente"), Member(id=140627, name="No Afrodescendiente"), Member(id=140629, name="Total")],
         ),
     ],
     4992: [
         Dimension(
             id=48525,
             name="Area Geografica",
             members=[Member(id=48529, name="Total"), Member(id=48526, name="Urbano"), Member(id=48528, name="Rural")],
         ),
     ],
     4639: [
         Dimension(
             id=144,
             name="Sexo__ESTANDAR",
             members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
         ),
         Dimension(
             id=378,
             name="Quintil",
             members=[
                 Member(id=380, name="Quintil 1"),
                 Member(id=382, name="Quintil 2"),
                 Member(id=383, name="Quintil 3"),
                 Member(id=384, name="Quintil 4"),
                 Member(id=381, name="Quintil 5"),
                 Member(id=379, name="Total quintiles"),
             ],
         ),
         Dimension(
             id=43039,
             name="Tipo de etnia",
             members=[
                 Member(id=77477, name="Indígena"),
                 Member(id=43044, name="Afrodescendiente"),
                 Member(id=43043, name="No indígena ni afrodescendiente"),
                 Member(id=43040, name="Total"),
             ],
         ),
     ],
     ```
   - Add `4788, 4968, 4969, 4992, 4639` to `VERTICAL_SLICE_INDICATORS` with relationships linking `4788` (`BREAKDOWN_OF`) to `4968, 4969, 4639`.
4. In `src/statscepal/semantic/engine.py`:
   - Add `"POBLACION": [4788, 4968, 4969, 4639, 4992]` to `CONCEPT_TO_INDICATORS`.
   - In Stage 3 candidate selection for `intent.root_concept == "POBLACION"`:
     - If `intent.facets.get("etnia") == "AFRODESCENDIENTE"`: `primary_id = 4969`
     - Else if `"estrato"` in `intent.facets` and `"etnia"` in `intent.facets`: `primary_id = 4639`
     - Else if `"etnia"` in `intent.facets`: `primary_id = 4968`
     - Else: `primary_id = 4788`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_semantic_breakdowns.py tests/test_semantic_benchmark_200.py tests/test_semantic_facet_coverage.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/semantic/parser.py src/statscepal/semantic/facet_ontology.py src/statscepal/semantic/registry.py src/statscepal/semantic/engine.py tests/test_semantic_breakdowns.py
git commit -m "feat(semantic): support Latin American demonyms and demographic ethnic population resolution"
```

---

### Task 4: End-to-End Certification of Multi-Country Inflation & Ethnic Population Queries

**Files:**
- Modify: `tests/test_semantic_fetcher.py`
- Modify: `src/statscepal/cli.py` (display `empirical_indicator_id` note if mapped)

**Interfaces:**
- Consumes: `SemanticResolutionEngine.resolve` and `SemanticDataFetcher.fetch_resolved_data`.
- Produces: End-to-end hermetic certification of all 3 user diagnostic queries and CLI empirical ID annotation.

- [ ] **Step 1: Write the failing test in `tests/test_semantic_fetcher.py`**

Append the following test to `tests/test_semantic_fetcher.py`:

```python
def test_end_to_end_ethnic_population_peru_fetch_with_decada_and_breakdown():
    """Verify 'necesito datos etnicos de la poblacion peruana' resolves to 4968 and fetches Indigenous vs No Indígena breakdown for latest decade."""
    import pandas as pd
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    res = engine.resolve("necesito datos etnicos de la poblacion peruana")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4968

    mock_df = pd.DataFrame([
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2010", "Area Geografica": "Total", "Condición Indígena": "Indígena", "value": 6383284.0, "notes_ids": "8651"},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2010", "Area Geografica": "Total", "Condición Indígena": "No Indígena", "value": 17437316.0, "notes_ids": "8651"},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2010", "Area Geografica": "Total", "Condición Indígena": "Total", "value": 23820599.0, "notes_ids": "8651"},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2010", "Area Geografica": "Urbano", "Condición Indígena": "Indígena", "value": 4525633.0, "notes_ids": "8651"},
    ])

    fetcher = SemanticDataFetcher()
    fetcher._load_indicator_data = lambda ind_id, member_ids=None: mock_df

    payload = fetcher.fetch_resolved_data(res)
    assert payload["observation_exists"] is True
    series = payload.get("series", [])
    assert len(series) == 2
    by_dim = {r["dimension"]: r["value"] for r in series}
    assert by_dim == {"Indígena": 6383284.0, "No Indígena": 17437316.0}
```

- [ ] **Step 2: Run test to verify behavior**

Run: `uv run pytest tests/test_semantic_fetcher.py -k test_end_to_end_ethnic_population_peru_fetch_with_decada_and_breakdown -v`

- [ ] **Step 3: Display mapped `empirical_indicator_id` in CLI output (`src/statscepal/cli.py`)**

In `src/statscepal/cli.py`, when `--fetch` displays `Empirical Series` or `Empirical Observation`, if `emp.get("empirical_indicator_id")` differs from `res.selected_candidate.indicator_id`, print:
`  CEPALSTAT API Table ID: {emp['empirical_indicator_id']}` so the user always sees the exact live CEPALSTAT API table ID fetched.

- [ ] **Step 4: Run full test suite to verify 100% pass rate**

Run: `uv run pytest -m "not integration" -v`
Expected: All 300+ tests PASS, 100.0% accuracy on the 200-question and 70-case benchmarks, `0.00%` False Substitution Rate.

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/cli.py tests/test_semantic_fetcher.py
git commit -m "feat(cli): display mapped CEPALSTAT API table ID and certify ethnic population fetch"
```
