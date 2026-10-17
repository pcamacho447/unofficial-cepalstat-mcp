# Retrospective Remediation & Code Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 8 action items (`AI-1` through `AI-8`) identified in the 2026-10-17 retrospective to eliminate cross-story boundary defects, resolve member ID collisions, guarantee reachability for demographic indicators, seed dimensions for vertical-slice indicators, and modularize `SemanticDataFetcher`.

**Architecture:** 
1. **Registry & Ontology Integrity (`registry.py`, `facet_ontology.py`):** Align `DEFAULT_OFFICIAL_DIMENSIONS[3342]` with verified CEPALSTAT member IDs (`77477`, `43044`, `43043`, `43040`), seed missing dimensions for the 10 `VERTICAL_SLICE_INDICATORS` (`127, 3331, 3337, 5097, 119, 340, 365, 1684, 3344, 3333`), and refine `ETNICO_TOTAL` trigger precedence so specific ethnic groups take priority.
2. **Parser & Engine Routing Precedence (`parser.py`, `engine.py`):** Prioritize `POBLACION` when demographic and quintile terms co-occur, route `estrato + etnia` to indicator `4639` ahead of single-facet indicators in Stage 3, and prevent default `NACIONAL` area from bypassing canonical defaults.
3. **Data Fetcher Hardening & Decomposition (`fetcher.py`):** Unify column matching across Step 2 and Step 5 with accent-insensitive helpers, protect explicit user breakdowns from unconstrained dimension collapse, bridge dimension/member aliases during empirical remapping (`3340 -> 3295/3324/3390`), rescue dynamic temporal anchors per missing year, fix multi-country payload country attribution, and decompose `fetch_resolved_data` into cohesive stage helpers.
4. **CLI & Lexicon Hygiene (`cli.py`, `COUNTRY_LEXICON`):** Display dynamic `conversational_hint` whenever present (including `ALTERNATIVE_PROPOSED`), and remove redundant accented `"ñ"` keys from `COUNTRY_LEXICON`.

**Tech Stack:** Python 3.12, Pandas, SQLite, Pytest, Pydantic.

**Spec:** [`docs/reports/2026-10-17-retrospective-code-hardening-and-catalog-alignment.md`](file:///C:/papx/statscepal/docs/reports/2026-10-17-retrospective-code-hardening-and-catalog-alignment.md)

## Global Constraints

- Python 3.10+ modern typing syntax (`X | Y`, `dict[K, V]`, `list[T]`, `tuple[T, ...]`).
- All 303 non-integration tests must pass with 0 regressions.
- Top-1 Accuracy across the 200-question benchmark must remain strictly at 100.0%.
- False Substitution Rate across the 200 benchmark test cases must remain strictly at 0.00%.
- Latency across in-memory SQLite and thesaurus queries must maintain $p50 < 0.5\text{ ms}$.
- Strict offline hermeticity: test suites must NEVER perform live network calls to CEPALSTAT.
- Safe UTF-8 encoding for Windows console environments.

---

## File Structure & Plan Decomposition

| File Path | Responsibility | Tasks |
|---|---|---|
| [`src/statscepal/semantic/registry.py`](file:///C:/papx/statscepal/src/statscepal/semantic/registry.py) | Indicator definitions, canonical dimensions, synthetic member sets, and empirical ID mappings. | Task 1, Task 3 |
| [`src/statscepal/semantic/fetcher.py`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py) | Empirical DataFrame extraction, column matching, unconstrained dimension filtering, multi-year anchor rescue, and payload construction. | Task 1, Task 3, Task 4, Task 5, Task 6 |
| [`src/statscepal/semantic/parser.py`](file:///C:/papx/statscepal/src/statscepal/semantic/parser.py) | Query parsing, concept tokenization, and `COUNTRY_LEXICON`. | Task 2, Task 6 |
| [`src/statscepal/semantic/engine.py`](file:///C:/papx/statscepal/src/statscepal/semantic/engine.py) | Candidate selection, population indicator routing, and dynamic conversational hints. | Task 2 |
| [`src/statscepal/semantic/facet_ontology.py`](file:///C:/papx/statscepal/src/statscepal/semantic/facet_ontology.py) | Declarative facet ontology, breakdown triggers, and value patterns. | Task 2 |
| [`src/statscepal/cli.py`](file:///C:/papx/statscepal/src/statscepal/cli.py) | CLI output formatting, table ID annotations, and conversational hint display. | Task 5 |
| [`tests/test_semantic_fetcher.py`](file:///C:/papx/statscepal/tests/test_semantic_fetcher.py) | Fetcher unit tests, column matching, breakdown preservation, empirical remapping, and country attribution. | Task 1, Task 3, Task 4, Task 5, Task 6 |
| [`tests/test_semantic_breakdowns.py`](file:///C:/papx/statscepal/tests/test_semantic_breakdowns.py) | Breakdown resolution, demographic indicator reachability (`4639`, `4992`), and facet extraction tests. | Task 2, Task 3 |
| [`tests/test_semantic_registry_200.py`](file:///C:/papx/statscepal/tests/test_semantic_registry_200.py) | Invariant tests for `DEFAULT_OFFICIAL_DIMENSIONS` consistency and `VERTICAL_SLICE_INDICATORS` coverage. | Task 1, Task 3 |
| [`tests/test_cli_semantic.py`](file:///C:/papx/statscepal/tests/test_cli_semantic.py) | CLI tests for `conversational_hint` rendering in `ALTERNATIVE_PROPOSED`. | Task 5 |

---

## Tasks

### Task 1: Member ID Collision Isolation in `3342` & Accent-Insensitive Matching in `SemanticDataFetcher` Step 5 (`AI-1` & `AI-2`)

**Files:**
- Modify: [`src/statscepal/semantic/registry.py:63-71`](file:///C:/papx/statscepal/src/statscepal/semantic/registry.py#L63-L71)
- Modify: [`src/statscepal/semantic/fetcher.py:17-20, 438-445, 690-705`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L17-L20)
- Test: [`tests/test_semantic_fetcher.py`](file:///C:/papx/statscepal/tests/test_semantic_fetcher.py)
- Test: [`tests/test_semantic_registry_200.py`](file:///C:/papx/statscepal/tests/test_semantic_registry_200.py)

**Interfaces:**
- Consumes: `SYNTHETIC_DIMENSION_MEMBER_IDS`, `DEFAULT_OFFICIAL_DIMENSIONS` in `registry.py`.
- Produces: `_match_dim_column(col_name: str, target_name: str) -> bool` helper in `fetcher.py` guaranteeing consistent accent-free and `__estandar`-free column matching across Steps 2 and 5.

- [ ] **Step 1: Write the failing tests**

```python
# In tests/test_semantic_registry_200.py:
def test_default_official_dimensions_shared_dim_id_consistency():
    """Assert that whenever a dim_id is shared across indicators, its member IDs do not conflict."""
    dim_registry: dict[int, dict[int, str]] = {}
    for ind_id, dims in DEFAULT_OFFICIAL_DIMENSIONS.items():
        for d in dims:
            dim_id = d["dim_id"]
            for m_val, m_id in d["members_by_value"].items():
                if dim_id in dim_registry and m_id in dim_registry[dim_id]:
                    existing_val = dim_registry[dim_id][m_id]
                    assert existing_val == m_val, (
                        f"Conflict in dim_id={dim_id}: member_id={m_id} mapped to '{existing_val}' "
                        f"in previous indicator, but '{m_val}' in indicator {ind_id}."
                    )
                dim_registry.setdefault(dim_id, {})[m_id] = m_val

# In tests/test_semantic_fetcher.py:
def test_fetcher_step5_breakdown_cols_matches_accented_dataframe_columns(mock_client):
    """Assert that Step 5 matches breakdown column with diacritics ('Área geográfica' vs 'Area Geografica')."""
    fetcher = SemanticDataFetcher(client=mock_client)
    res = SemanticResolutionResponse(
        query="poblacion indigena por area en peru 2020",
        status=SemanticResolutionStatus.RESOLVED,
        selected_candidate=CandidateIndicator(
            indicator_id=4968,
            name="Población indígena según área geográfica",
            confidence_score=1.0,
            conceptual_fit="EXACT",
            matched_facets={"etnia": "INDIGENA"},
        ),
        applied_filters=AppliedFilters(
            country_iso3="PER",
            country_name="Perú",
            years=[2020],
            year_mode=YearFilterMode.SINGLE,
            facets={"etnia": "INDIGENA", "area": "AREA_DESGLOSE"},
            dimensions=[
                AppliedDimensionFilter(
                    dimension_id=78153,
                    dimension_name="Area Geografica",
                    member_id=None,
                    member_name=None,
                    is_breakdown=True,
                    breakdown_members=["Urbana", "Rural"],
                )
            ],
        ),
    )
    df = pd.DataFrame([
        {"País__ESTANDAR": "Perú", "Años_disponibles": "2020", "Área geográfica": "Urbana", "valor": 500000.0},
        {"País__ESTANDAR": "Perú", "Años_disponibles": "2020", "Área geográfica": "Rural", "valor": 1200000.0},
    ])
    mock_client.get_dataframe.return_value = df
    payload = fetcher.fetch_resolved_data(res)
    assert len(payload["series"]) == 2
    assert all("member" in item for item in payload["series"]), "Step 5 failed to assign member labels due to accent mismatch"
```

- [ ] **Step 2: Run tests to verify failure**
Run: `uv run pytest tests/test_semantic_registry_200.py -k test_default_official_dimensions_shared_dim_id_consistency` and `uv run pytest tests/test_semantic_fetcher.py -k test_fetcher_step5_breakdown_cols_matches_accented_dataframe_columns`.
Verify that `test_default_official_dimensions_shared_dim_id_consistency` fails due to member `43040` (`"Total"` in `4639` vs `"Afrodescendiente"` in `3342`), and Step 5 fails to set `"member"`.

- [ ] **Step 3: Implement minimal code to fix**
1. In `src/statscepal/semantic/registry.py`: Update `DEFAULT_OFFICIAL_DIMENSIONS[3342]` on `dim_id=43039`:
```python
# In DEFAULT_OFFICIAL_DIMENSIONS[3342]:
{
    "dim_id": 43039,
    "dim_name": "Tipo de etnia",
    "members": {
        43040: "Total",
        43044: "Afrodescendiente",
        77477: "Indígena",
        43043: "No indígena ni afrodescendiente",
    },
    "members_by_value": {
        "TOTAL": 43040,
        "AFRODESCENDIENTE": 43044,
        "INDIGENA": 77477,
        "NO_INDIGENA": 43043,
    },
}
```
2. In `src/statscepal/semantic/fetcher.py`: Define `_match_dim_column(col_name: str, target_name: str) -> bool`:
```python
def _match_dim_column(col_name: str, target_name: str) -> bool:
    cl = _strip_accents(col_name).lower().strip().replace("__estandar", "")
    dl = _strip_accents(target_name).lower().strip().replace("__estandar", "")
    return cl == dl or cl.replace(" ", "") == dl.replace(" ", "")
```
Replace the raw column comparisons in Step 2 (`fetcher.py:438-445`) and Step 5 (`fetcher.py:690-701`) with calls to `_match_dim_column`.

- [ ] **Step 4: Run tests to verify pass**
Run: `uv run pytest tests/test_semantic_registry_200.py tests/test_semantic_fetcher.py -v`. All tests must pass.
Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`. Must maintain 100.0% Top-1 Accuracy and 0.00% FSR.

- [ ] **Step 5: Commit changes**
`git add src/statscepal/semantic/registry.py src/statscepal/semantic/fetcher.py tests/test_semantic_registry_200.py tests/test_semantic_fetcher.py`  
`git commit -m "fix(semantic): isolate 3342 member IDs and unify accent-insensitive column matching in fetcher"`

---

### Task 2: Concept Precedence Correction for `POBLACION` vs `DISTRIBUCION_INGRESO` & Reachability of Indicator `4639` (`AI-3`)

**Files:**
- Modify: [`src/statscepal/semantic/parser.py:736-808`](file:///C:/papx/statscepal/src/statscepal/semantic/parser.py#L736-L808)
- Modify: [`src/statscepal/semantic/facet_ontology.py:276-290, 484-486`](file:///C:/papx/statscepal/src/statscepal/semantic/facet_ontology.py#L276-L290)
- Modify: [`src/statscepal/semantic/engine.py:43-53`](file:///C:/papx/statscepal/src/statscepal/semantic/engine.py#L43-L53)
- Test: [`tests/test_semantic_breakdowns.py`](file:///C:/papx/statscepal/tests/test_semantic_breakdowns.py)

**Interfaces:**
- Consumes: `QueryParser.parse`, `FacetOntology.extract_facets_from_query`, `SemanticResolutionEngine._route_population_indicator`.
- Produces: Correct canonical routing of queries with `poblacion + quintil/estrato + etnia` to indicator `4639`, queries with `poblacion + area` to indicator `4992` (when non-default), and specific ethnic terms before `ETNICO_TOTAL`.

- [ ] **Step 1: Write the failing tests**

```python
# In tests/test_semantic_breakdowns.py:
def test_poblacion_por_quintil_y_etnia_routes_to_indicator_4639(engine):
    """Assert 'poblacion indigena por quintil en peru 2021' routes to 4639, not 3340."""
    res = engine.resolve("poblacion indigena por quintil en peru 2021")
    assert res.status == SemanticResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4639
    assert res.applied_filters.country_iso3 == "PER"

def test_poblacion_especifica_afrodescendiente_no_bloqueada_por_etnico_total(engine):
    """Assert 'poblacion del grupo etnico afrodescendiente en brasil 2020' routes to 4969."""
    res = engine.resolve("poblacion del grupo etnico afrodescendiente en brasil 2020")
    assert res.status == SemanticResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4969

def test_poblacion_por_area_urbana_rural_routes_to_indicator_4992(engine):
    """Assert 'poblacion por area urbana y rural en colombia 2022' routes to 4992."""
    res = engine.resolve("poblacion por area en colombia 2022")
    assert res.status == SemanticResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4992
```

- [ ] **Step 2: Run tests to verify failure**
Run: `uv run pytest tests/test_semantic_breakdowns.py -k "test_poblacion_por_quintil or test_poblacion_especifica or test_poblacion_por_area"`
Verify failure: `"poblacion indigena por quintil"` matches `DISTRIBUCION_INGRESO` (`3340`) and abstains on unsupported facet `"etnia"`.

- [ ] **Step 3: Implement minimal code to fix**
1. In `src/statscepal/semantic/parser.py`:
   In `QueryParser.parse`, inspect `DISTRIBUCION_INGRESO` vs `POBLACION`: if `"poblacion"` or `"habitantes"` or `"personas"` is present together with `"quintil"`, or if `"etnia"` / `"indigena"` is present with `"quintil"`, select `root_concept = "POBLACION"` and extract `estrato = "QUINTIL"`.
2. In `src/statscepal/semantic/facet_ontology.py`:
   In `FacetOntology.extract_facets_from_query`, evaluate specific member value patterns (`AFRODESCENDIENTE`, `INDIGENA`) BEFORE bare trigger words (`ETNICO_TOTAL`).
3. In `src/statscepal/semantic/engine.py`:
   In `_route_population_indicator(facets: dict[str, str]) -> int`:
```python
def _route_population_indicator(self, facets: dict[str, str]) -> int:
    has_etnia = "etnia" in facets
    has_estrato = "estrato" in facets or "quintil" in facets
    has_area = "area" in facets and self.ontology.is_critical_unhandled_facet("area", facets["area"])

    # 1. Highest specificity: Population by quintile and ethnicity -> 4639
    if has_estrato and has_etnia:
        return 4639
    # 2. Area + Ethnicity breakdowns:
    if facets.get("etnia") == "AFRODESCENDIENTE":
        return 4969
    if has_etnia:
        return 4968
    # 3. Area breakdown without ethnicity -> 4992
    if has_area:
        return 4992
    # 4. Canonical total population default -> 4788
    return 4788
```

- [ ] **Step 4: Run tests to verify pass**
Run: `uv run pytest tests/test_semantic_breakdowns.py -v`.
Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`.
Run: `uv run pytest tests/test_semantic_facet_coverage.py -v`.
Verify 100.0% accuracy across all test suites.

- [ ] **Step 5: Commit changes**
`git add src/statscepal/semantic/parser.py src/statscepal/semantic/facet_ontology.py src/statscepal/semantic/engine.py tests/test_semantic_breakdowns.py`  
`git commit -m "fix(semantic): resolve POBLACION precedence, support 4639 and 4992, and prioritize specific ethnic groups"`

---

### Task 3: Seed `DEFAULT_OFFICIAL_DIMENSIONS` for Vertical Slice Indicators & Protect Explicit Breakdowns (`AI-4`)

**Files:**
- Modify: [`src/statscepal/semantic/registry.py:42-268`](file:///C:/papx/statscepal/src/statscepal/semantic/registry.py#L42-L268)
- Modify: [`src/statscepal/semantic/fetcher.py:137-182`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L137-L182)
- Test: [`tests/test_semantic_registry_200.py`](file:///C:/papx/statscepal/tests/test_semantic_registry_200.py)
- Test: [`tests/test_semantic_fetcher.py`](file:///C:/papx/statscepal/tests/test_semantic_fetcher.py)

**Interfaces:**
- Consumes: `VERTICAL_SLICE_INDICATORS`, `DEFAULT_OFFICIAL_DIMENSIONS` in `registry.py`.
- Produces: Complete dimension definitions for indicators `127, 3331, 3337, 5097, 119, 340, 365, 1684, 3344, 3333` and safeguard in `fetcher._filter_unconstrained_dimensions` against collapsing dimensions that were explicitly requested as breakdowns in `response.applied_filters.facets`.

- [ ] **Step 1: Write the failing tests**

```python
# In tests/test_semantic_registry_200.py:
def test_vertical_slice_indicators_with_supported_facets_have_default_official_dimensions():
    """Assert all indicators in VERTICAL_SLICE_INDICATORS declaring supported_facets have dimension entries."""
    missing = []
    for ind_id, info in VERTICAL_SLICE_INDICATORS.items():
        if info.get("supported_facets"):
            if ind_id not in DEFAULT_OFFICIAL_DIMENSIONS:
                missing.append(ind_id)
    assert not missing, f"Indicators declare supported_facets but lack DEFAULT_OFFICIAL_DIMENSIONS: {missing}"

# In tests/test_semantic_fetcher.py:
def test_fetcher_does_not_collapse_dimension_when_requested_as_breakdown(mock_client):
    """Assert _filter_unconstrained_dimensions never collapses a dimension to aggregate if requested as breakdown."""
    fetcher = SemanticDataFetcher(client=mock_client)
    res = SemanticResolutionResponse(
        query="tasa de desocupacion por sexo en chile 2022",
        status=SemanticResolutionStatus.RESOLVED,
        selected_candidate=CandidateIndicator(
            indicator_id=127,
            name="Tasa de desocupación",
            confidence_score=1.0,
            conceptual_fit="EXACT",
            matched_facets={"sexo": "SEXO_DESGLOSE"},
        ),
        applied_filters=AppliedFilters(
            country_iso3="CHL",
            country_name="Chile",
            years=[2022],
            year_mode=YearFilterMode.SINGLE,
            facets={"sexo": "SEXO_DESGLOSE"},
            dimensions=[],  # Empty dimensions list because indicator lacked DEFAULT_OFFICIAL_DIMENSIONS
        ),
    )
    df = pd.DataFrame([
        {"País__ESTANDAR": "Chile", "Años_disponibles": "2022", "Sexo__ESTANDAR": "Hombres", "valor": 7.5},
        {"País__ESTANDAR": "Chile", "Años_disponibles": "2022", "Sexo__ESTANDAR": "Mujeres", "valor": 9.1},
        {"País__ESTANDAR": "Chile", "Años_disponibles": "2022", "Sexo__ESTANDAR": "Total", "valor": 8.2},
    ])
    mock_client.get_dataframe.return_value = df
    payload = fetcher.fetch_resolved_data(res)
    # The breakdown rows ('Hombres', 'Mujeres') must NOT have been filtered out to 'Total'
    series_members = [item.get("member") for item in payload["series"]]
    assert len(payload["series"]) >= 2
    assert "Hombres" in series_members or any(item.get("value") == 7.5 for item in payload["series"])
```

- [ ] **Step 2: Run tests to verify failure**
Run: `uv run pytest tests/test_semantic_registry_200.py -k test_vertical_slice_indicators_with_supported_facets_have_default_official_dimensions` and `uv run pytest tests/test_semantic_fetcher.py -k test_fetcher_does_not_collapse_dimension_when_requested_as_breakdown`.
Verify that 10 indicators fail the registry check (`[127, 3331, 3337, 5097, 119, 340, 365, 1684, 3344, 3333]`), and `fetcher` collapses `Sexo__ESTANDAR` to `Total`.

- [ ] **Step 3: Implement minimal code to fix**
1. In `src/statscepal/semantic/registry.py`: Seed `DEFAULT_OFFICIAL_DIMENSIONS` for `127, 3331, 3337, 5097, 119, 340, 365, 1684, 3344, 3333` with standard dimensions (`Sexo__ESTANDAR`, `Area Geografica`, `Grupos de edad`) and canonical aggregate members (`"Total"`, `"Ambos sexos"`, `"Nacional"`).
2. In `src/statscepal/semantic/fetcher.py`: In `_filter_unconstrained_dimensions`:
```python
# Check if this column's concept is requested as a breakdown in response.applied_filters.facets
facet_keys_in_breakdown = {
    f_k for f_k, f_v in response.applied_filters.facets.items()
    if "_DESGLOSE" in str(f_v) or f_v == "ETNICO_TOTAL"
}
# Map col_norm to facet concept:
if any(bk in col_norm for bk in facet_keys_in_breakdown):
    # User explicitly requested breakdown for this dimension -> DO NOT collapse to aggregate!
    continue
```

- [ ] **Step 4: Run tests to verify pass**
Run: `uv run pytest tests/test_semantic_registry_200.py tests/test_semantic_fetcher.py -v`.
Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`.
Verify 0 regressions and 303+ passing tests.

- [ ] **Step 5: Commit changes**
`git add src/statscepal/semantic/registry.py src/statscepal/semantic/fetcher.py tests/test_semantic_registry_200.py tests/test_semantic_fetcher.py`  
`git commit -m "feat(semantic): seed dimensions for vertical slice indicators and preserve explicit breakdown dimensions"`

---

### Task 4: Dimension & Member Alias Resolution on Empirical Remapping `3340 -> 3295 / 3324 / 3390` (`AI-5`)

**Files:**
- Modify: [`src/statscepal/semantic/fetcher.py:185-198, 431-484`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L185-L198)
- Test: [`tests/test_semantic_fetcher.py`](file:///C:/papx/statscepal/tests/test_semantic_fetcher.py)

**Interfaces:**
- Consumes: `SemanticDataFetcher._resolve_empirical_indicator_id`.
- Produces: Dimension and member alias normalization when querying income distribution by quintile (`3324`), decile (`3390`), or Q5/Q1 ratio (`3295`).

- [ ] **Step 1: Write the failing tests**

```python
# In tests/test_semantic_fetcher.py:
def test_fetcher_empirical_mapping_3340_to_3324_matches_quintil_column_and_members(mock_client):
    """Assert querying quintile on 3340 correctly remaps to 3324 and filters 'Quintil' column."""
    fetcher = SemanticDataFetcher(client=mock_client)
    res = SemanticResolutionResponse(
        query="distribucion del ingreso primer quintil en chile 2022",
        status=SemanticResolutionStatus.RESOLVED,
        selected_candidate=CandidateIndicator(
            indicator_id=3340,
            name="Distribución del ingreso por estratos",
            confidence_score=1.0,
            conceptual_fit="EXACT",
            matched_facets={"estrato": "PRIMER_QUINTIL"},
        ),
        applied_filters=AppliedFilters(
            country_iso3="CHL",
            country_name="Chile",
            years=[2022],
            year_mode=YearFilterMode.SINGLE,
            facets={"estrato": "PRIMER_QUINTIL"},
            dimensions=[
                AppliedDimensionFilter(
                    dimension_id=33401,
                    dimension_name="Estrato de ingreso",
                    member_id=33402,
                    member_name="Primer quintil",
                    is_breakdown=False,
                    breakdown_members=[],
                )
            ],
        ),
    )
    df_3324 = pd.DataFrame([
        {"País__ESTANDAR": "Chile", "Años_disponibles": "2022", "Quintil": "Quintil 1", "valor": 4.5},
        {"País__ESTANDAR": "Chile", "Años_disponibles": "2022", "Quintil": "Quintil 5", "valor": 45.2},
    ])
    mock_client.get_dataframe.return_value = df_3324
    payload = fetcher.fetch_resolved_data(res)
    assert payload["indicator_id"] == 3324
    assert len(payload["series"]) == 1
    assert payload["series"][0]["value"] == 4.5

def test_fetcher_empirical_mapping_3340_to_3390_matches_decil_column_and_members(mock_client):
    """Assert querying decile on 3340 correctly remaps to 3390 and filters 'Decil' column."""
    fetcher = SemanticDataFetcher(client=mock_client)
    res = SemanticResolutionResponse(
        query="distribucion del ingreso primer decil en uruguay 2021",
        status=SemanticResolutionStatus.RESOLVED,
        selected_candidate=CandidateIndicator(
            indicator_id=3340,
            name="Distribución del ingreso por estratos",
            confidence_score=1.0,
            conceptual_fit="EXACT",
            matched_facets={"estrato": "PRIMER_DECIL"},
        ),
        applied_filters=AppliedFilters(
            country_iso3="URY",
            country_name="Uruguay",
            years=[2021],
            year_mode=YearFilterMode.SINGLE,
            facets={"estrato": "PRIMER_DECIL"},
            dimensions=[
                AppliedDimensionFilter(
                    dimension_id=33401,
                    dimension_name="Estrato de ingreso",
                    member_id=33404,
                    member_name="Primer decil",
                    is_breakdown=False,
                    breakdown_members=[],
                )
            ],
        ),
    )
    df_3390 = pd.DataFrame([
        {"País__ESTANDAR": "Uruguay", "Años_disponibles": "2021", "Decil": "Decil 1", "valor": 1.8},
        {"País__ESTANDAR": "Uruguay", "Años_disponibles": "2021", "Decil": "Decil 10", "valor": 32.1},
    ])
    mock_client.get_dataframe.return_value = df_3390
    payload = fetcher.fetch_resolved_data(res)
    assert payload["indicator_id"] == 3390
    assert len(payload["series"]) == 1
    assert payload["series"][0]["value"] == 1.8
```

- [ ] **Step 2: Run tests to verify failure**
Run: `uv run pytest tests/test_semantic_fetcher.py -k "test_fetcher_empirical_mapping_3340_to_3324 or test_fetcher_empirical_mapping_3340_to_3390"`
Verify failure: `"Estrato de ingreso"` does not match `"Quintil"` or `"Decil"`.

- [ ] **Step 3: Implement minimal code to fix**
In `src/statscepal/semantic/fetcher.py`:
In Step 2 dimension matching, support dimension and member alias normalization:
```python
DIM_NAME_ALIASES = {
    "estrato de ingreso": ["quintil", "decil", "estrato"],
}
MEMBER_VALUE_ALIASES = {
    "primer quintil": ["quintil 1", "i", "quintil i", "1"],
    "quinto quintil": ["quintil 5", "v", "quintil v", "5"],
    "primer decil": ["decil 1", "i", "decil i", "1"],
    "decimo decil": ["decil 10", "x", "decil x", "10"],
}
```
If `dim_name` does not match directly, check `DIM_NAME_ALIASES`. When matching member values in DataFrame rows, cross-check `MEMBER_VALUE_ALIASES`.

- [ ] **Step 4: Run tests to verify pass**
Run: `uv run pytest tests/test_semantic_fetcher.py -v`.
Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`. All tests pass.

- [ ] **Step 5: Commit changes**
`git add src/statscepal/semantic/fetcher.py tests/test_semantic_fetcher.py`  
`git commit -m "feat(semantic): support dimension and member aliases for empirical income distribution indicators (3324, 3390)"`

---

### Task 5: CLI `conversational_hint` Rendering for `ALTERNATIVE_PROPOSED`, Multi-Year Dynamic Anchor Rescue, and Multi-Country Country Attribution (`AI-6`)

**Files:**
- Modify: [`src/statscepal/cli.py:639-650`](file:///C:/papx/statscepal/src/statscepal/cli.py#L639-L650)
- Modify: [`src/statscepal/semantic/fetcher.py:568-590, 787-802`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L568-L590)
- Test: [`tests/test_cli_semantic.py`](file:///C:/papx/statscepal/tests/test_cli_semantic.py)
- Test: [`tests/test_semantic_fetcher.py`](file:///C:/papx/statscepal/tests/test_semantic_fetcher.py)

**Interfaces:**
- Consumes: `SemanticResolutionResponse.conversational_hint`, `SemanticDataFetcher.fetch_resolved_data`.
- Produces: Complete CLI output with conversational hints for `ALTERNATIVE_PROPOSED`, dynamic anchor rescue across partial gaps in multi-year queries with `RESOLVED_WITH_ANCHORS`, and accurate country name pairing in multi-country root payloads.

- [ ] **Step 1: Write the failing tests**

```python
# In tests/test_cli_semantic.py:
def test_cli_semantic_resolve_displays_conversational_hint_on_alternative_proposed(runner):
    """Assert CLI outputs conversational hint when status is ALTERNATIVE_PROPOSED."""
    result = runner.invoke(app, ["semantic", "resolve", "cuentas fiscales de chile 2022"])
    assert result.exit_code == 0
    assert "Hint:" in result.output
    assert "ID 1240" in result.output

# In tests/test_semantic_fetcher.py:
def test_fetcher_multi_year_rescues_anchors_for_missing_year_in_range(mock_client):
    """Assert dynamic anchor rescue runs for unobserved years in a multi-year query."""
    fetcher = SemanticDataFetcher(client=mock_client)
    res = SemanticResolutionResponse(
        query="gini en chile del 2020 al 2022",
        status=SemanticResolutionStatus.RESOLVED,
        selected_candidate=CandidateIndicator(
            indicator_id=3289,
            name="Índice de Gini",
            confidence_score=1.0,
            conceptual_fit="EXACT",
        ),
        applied_filters=AppliedFilters(
            country_iso3="CHL",
            country_name="Chile",
            years=[2020, 2021, 2022],
            year_mode=YearFilterMode.RANGE,
        ),
    )
    # Chile has survey in 2020 and 2022, but not 2021
    df = pd.DataFrame([
        {"País__ESTANDAR": "Chile", "Años_disponibles": "2020", "valor": 0.45},
        {"País__ESTANDAR": "Chile", "Años_disponibles": "2022", "valor": 0.43},
    ])
    mock_client.get_dataframe.return_value = df
    payload = fetcher.fetch_resolved_data(res)
    assert any(item.get("is_anchor") for item in payload["series"]) or res.status == SemanticResolutionStatus.RESOLVED_WITH_ANCHORS

def test_fetcher_multi_country_payload_country_attribution(mock_client):
    """Assert payload['country'] matches the country of latest_item, not always the first country."""
    fetcher = SemanticDataFetcher(client=mock_client)
    res = SemanticResolutionResponse(
        query="pib per capita en peru y colombia 2022",
        status=SemanticResolutionStatus.RESOLVED,
        selected_candidate=CandidateIndicator(indicator_id=730, name="PIB per cápita", confidence_score=1.0, conceptual_fit="EXACT"),
        applied_filters=AppliedFilters(
            country_iso3="PER",
            country_name="Perú",
            target_countries=["PER", "COL"],
            years=[2022],
            year_mode=YearFilterMode.SINGLE,
        ),
    )
    df = pd.DataFrame([
        {"País__ESTANDAR": "Perú", "Años_disponibles": "2022", "valor": 6800.0},
        {"País__ESTANDAR": "Colombia", "Años_disponibles": "2022", "valor": 6500.0},
    ])
    mock_client.get_dataframe.return_value = df
    payload = fetcher.fetch_resolved_data(res)
    latest_item = payload["series"][-1]
    assert payload["country"] == latest_item.get("country")
```

- [ ] **Step 2: Run tests to verify failure**
Run: `uv run pytest tests/test_cli_semantic.py -k test_cli_semantic_resolve_displays_conversational_hint_on_alternative_proposed` and `uv run pytest tests/test_semantic_fetcher.py -k "test_fetcher_multi_year_rescues_anchors or test_fetcher_multi_country_payload_country_attribution"`.
Verify that CLI omits hint when `selected_candidate` is not None, and multi-country pairs `series[-1]` (Colombia) with `"Perú"`.

- [ ] **Step 3: Implement minimal code to fix**
1. In `src/statscepal/cli.py`:
   Move conversational hint display outside the `else:` branch:
```python
if res.conversational_hint:
    typer.echo(f"Hint:      {res.conversational_hint}")
```
2. In `src/statscepal/semantic/fetcher.py`:
   - In dynamic anchor rescue (`fetcher.py:568-590`), compute missing requested years `missing = [y for y in requested_years if y not in observed_requested]`. If `missing` and `avail_years`, discover adjacent anchor years, inject them with `is_anchor=True`, and set `response.status = SemanticResolutionStatus.RESOLVED_WITH_ANCHORS`.
   - In top-level payload (`fetcher.py:787-802`):
```python
payload["country"] = latest_item.get("country", response.applied_filters.country_name)
```

- [ ] **Step 4: Run tests to verify pass**
Run: `uv run pytest tests/test_cli_semantic.py tests/test_semantic_fetcher.py -v`. All pass.
Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`. All pass.

- [ ] **Step 5: Commit changes**
`git add src/statscepal/cli.py src/statscepal/semantic/fetcher.py tests/test_cli_semantic.py tests/test_semantic_fetcher.py`  
`git commit -m "fix(cli,fetcher): display conversational hints on alternatives, rescue partial multi-year anchors, and fix payload country attribution"`

---

### Task 6: Modular Decomposition of `SemanticDataFetcher.fetch_resolved_data` & Test/Lexicon Hygiene (`AI-7` & `AI-8`)

**Files:**
- Modify: [`src/statscepal/semantic/fetcher.py:200-901`](file:///C:/papx/statscepal/src/statscepal/semantic/fetcher.py#L200-L901)
- Modify: [`src/statscepal/semantic/parser.py:58-128`](file:///C:/papx/statscepal/src/statscepal/semantic/parser.py#L58-L128)
- Modify: [`tests/test_semantic_fetcher.py:273-301`](file:///C:/papx/statscepal/tests/test_semantic_fetcher.py#L273-L301)
- Test: [`tests/test_semantic_fetcher.py`](file:///C:/papx/statscepal/tests/test_semantic_fetcher.py)
- Test: [`tests/test_semantic_benchmark_200.py`](file:///C:/papx/statscepal/tests/test_semantic_benchmark_200.py)

**Interfaces:**
- Consumes: `SemanticDataFetcher`.
- Produces: Clean, decomposed helper methods inside `SemanticDataFetcher`:
  - `_prepare_empirical_fetch(response: SemanticResolutionResponse) -> tuple[int, list[int] | None]`
  - `_filter_dimensions(df: pd.DataFrame, response: SemanticResolutionResponse) -> tuple[pd.DataFrame, list[str]]`
  - `_filter_geography_and_years(df: pd.DataFrame, response: SemanticResolutionResponse) -> pd.DataFrame`
  - `_build_payload(df: pd.DataFrame, response: SemanticResolutionResponse, empirical_id: int, breakdown_cols: list[str]) -> dict[str, Any]`
  And cleanly cleaned `COUNTRY_LEXICON` without dead accented `"ñ"` keys.

- [ ] **Step 1: Write tests for distinct group years and lexicon cleanliness**

```python
# In tests/test_semantic_fetcher.py:
def test_fetcher_multi_country_without_year_filters_to_latest_year_per_country_distinct_years(mock_client):
    """Assert per-country max year filters accurately when countries have different latest years."""
    fetcher = SemanticDataFetcher(client=mock_client)
    res = SemanticResolutionResponse(
        query="pib per capita en peru y chile",
        status=SemanticResolutionStatus.RESOLVED,
        selected_candidate=CandidateIndicator(indicator_id=730, name="PIB per cápita", confidence_score=1.0, conceptual_fit="EXACT"),
        applied_filters=AppliedFilters(
            country_iso3="PER",
            country_name="Perú",
            target_countries=["PER", "CHL"],
            years=[],
            year_mode=YearFilterMode.NONE,
        ),
    )
    # Perú latest is 2021, Chile latest is 2022
    df = pd.DataFrame([
        {"País__ESTANDAR": "Perú", "Años_disponibles": "2020", "valor": 6500.0},
        {"País__ESTANDAR": "Perú", "Años_disponibles": "2021", "valor": 6800.0},
        {"País__ESTANDAR": "Chile", "Años_disponibles": "2020", "valor": 15000.0},
        {"País__ESTANDAR": "Chile", "Años_disponibles": "2022", "valor": 15500.0},
    ])
    mock_client.get_dataframe.return_value = df
    payload = fetcher.fetch_resolved_data(res)
    per_item = next(item for item in payload["series"] if item["country"] == "Perú")
    chl_item = next(item for item in payload["series"] if item["country"] == "Chile")
    assert per_item["year"] == 2021
    assert chl_item["year"] == 2022
```

- [ ] **Step 2: Run test to verify**
Run: `uv run pytest tests/test_semantic_fetcher.py -k test_fetcher_multi_country_without_year_filters_to_latest_year_per_country_distinct_years -v`.

- [ ] **Step 3: Implement refactor in `fetcher.py` and cleanup in `parser.py`**
1. In `src/statscepal/semantic/fetcher.py`:
   Decompose `fetch_resolved_data`:
   - Extract `_prepare_empirical_fetch` (50 lines).
   - Extract `_filter_dimensions` (120 lines).
   - Extract `_filter_geography_and_years` (150 lines).
   - Extract `_build_payload` (80 lines).
   Reduce `fetch_resolved_data` to a clean ~60-line orchestrator method.
2. In `src/statscepal/semantic/parser.py`:
   Remove redundant accented keys with `"ñ"` from `COUNTRY_LEXICON` (e.g. `"españa"`, `"panameño"`) since `clean = strip_accents(query)` converts `"ñ"` to `"n"` before lexicon lookup. Keep the unaccented `"espana"`, `"panameno"`.

- [ ] **Step 4: Run full test suite & benchmark verification**
Run: `uv run pytest -m "not integration"`. All 303+ tests must pass.
Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`. Must maintain 100.0% Top-1 Accuracy and 0.00% FSR.
Run: `uv run pytest tests/test_semantic_facet_coverage.py -v`. Must maintain 100.0%.

- [ ] **Step 5: Commit changes**
`git add src/statscepal/semantic/fetcher.py src/statscepal/semantic/parser.py tests/test_semantic_fetcher.py`  
`git commit -m "refactor(semantic): modularize fetch_resolved_data into stage helpers and clean up COUNTRY_LEXICON"`

---

## Final Whole-Branch Verification Protocol

Before declaring the remediation epic complete:
1. Run all non-integration tests: `uv run pytest -m "not integration"`
2. Verify 200-question benchmark: `uv run pytest tests/test_semantic_benchmark_200.py -v` (100.0% Top-1 Accuracy, 0.00% False Substitution Rate).
3. Verify 70-case facet coverage benchmark: `uv run pytest tests/test_semantic_facet_coverage.py -v` (100.0% accuracy).
4. Verify generic gate invariants: `uv run pytest tests/test_semantic_generic_gate.py -v` (5/5 passing, 0 AST regressions).
5. Test motivating user queries directly:
   - `uv run statscepal semantic resolve "necesito los datos de la inflacion de alimentos de mexico, peru, argentina, chile, colombia y paraguay del año 2018 al 2023" --explain`
   - `uv run statscepal semantic resolve "necesito los datos de la inflacion de peru, argentina, chile, colombia y paraguay del año 2018 al 2023" --explain`
   - `uv run statscepal semantic resolve "necesito datos etnicos de la poblacion peruana" --explain`
   - `uv run statscepal semantic resolve "poblacion indigena por quintil en peru 2021" --explain`
   - `uv run statscepal semantic resolve "tasa de desocupacion por sexo en chile 2022" --explain`
   - `uv run statscepal semantic resolve "cuentas fiscales de chile 2022" --explain`
