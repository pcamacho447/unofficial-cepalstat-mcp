# Task 3 Brief: Latin American Demonyms in `COUNTRY_LEXICON` & Demographic/Ethnic Population Resolution (`4788`, `4968`, `4969`, `4992`, `4639`)

## Objective
Enable full conceptual and dimensional resolution of demographic and ethnic population queries (such as the user's live query: `"necesito datos etnicos de la poblacion peruana"`), by:
1. Adding Latin American demonyms (gentilicios, e.g. `peruana/o`, `chilena/o`, `mexicana/o`, etc.) to `COUNTRY_LEXICON` in `src/statscepal/semantic/parser.py`.
2. Extracting root concept `"POBLACION"` in `QueryParser.parse` when terms like `poblacion`, `habitantes`, `demografia`, `demografico` appear.
3. Enhancing the `"etnia"` `FacetDefinition` in `src/statscepal/semantic/facet_ontology.py` to recognize `"condicion indigena"`, `"condicion afrodescendiente"`, and support breakdown matching for `"ETNICO_TOTAL"`.
4. Registering demographic indicators `4788` (Población total), `4968` (Población indígena según área), `4969` (Población afrodescendiente según área), `4992` (Población según área urbana/rural), and `4639` (Población por quintil y etnia) in `src/statscepal/semantic/registry.py` with their dimensions and knowledge-graph relationships (`4788` has `BREAKDOWN_OF` to `4968, 4969, 4992, 4639`).
5. Routing `POBLACION` queries in `src/statscepal/semantic/engine.py` Stage 3 candidate selection and Stage 4 dimensional traversal based on presence of `etnia`, `area`, and `estrato` facets.

## Inputs & Context
- Base commit: `1b6c651b30ef317c5751d5570f6926d469235fa5`
- Plan reference: `docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md` (Task 3)
- Target files:
  - `src/statscepal/semantic/parser.py`
  - `src/statscepal/semantic/facet_ontology.py`
  - `src/statscepal/semantic/registry.py`
  - `src/statscepal/semantic/engine.py`
  - `tests/test_semantic_breakdowns.py`

## Instructions

### 1. TDD Red Test
Add the following two unit tests to `tests/test_semantic_breakdowns.py`:
```python
def test_ethnic_population_query_with_demonym_resolves_to_indigenous_population_breakdown():
    """Verify 'necesito datos etnicos de la poblacion peruana' extracts PER from 'peruana' and resolves to 4968 with ethnic breakdown."""
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.models import ResolutionStatus

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
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.models import ResolutionStatus

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
Run `uv run pytest tests/test_semantic_breakdowns.py -k "test_ethnic_population_query_with_demonym or test_specific_population_queries_route" -v` and confirm failure.

### 2. Implementation
1. In `src/statscepal/semantic/parser.py`:
   - Add Latin American demonyms to `COUNTRY_LEXICON`:
     - `brasileño`, `brasileno`, `brasilena`, `brasilenos`, `brasilenas` -> `BRA`
     - `colombiano`, `colombiana`, `colombianos`, `colombianas` -> `COL`
     - `chileno`, `chilena`, `chilenos`, `chilenas` -> `CHL`
     - `mexicano`, `mexicana`, `mexicanos`, `mexicanas` -> `MEX`
     - `argentino`, `argentina` (when not country), `argentinos`, `argentinas` -> `ARG`
     - `uruguayo`, `uruguaya`, `uruguayos`, `uruguayas` -> `URY`
     - `costarricense`, `costarricenses` -> `CRI`
     - `peruano`, `peruana`, `peruanos`, `peruanas` -> `PER`
     - `ecuatoriano`, `ecuatoriana`, `ecuatorianos`, `ecuatorianas` -> `ECU`
     - `boliviano`, `boliviana`, `bolivianos`, `bolivianas` -> `BOL`
     - `panameno`, `panamena`, `panamenos`, `panamenas` -> `PAN`
     - `paraguayo`, `paraguaya`, `paraguayos`, `paraguayas` -> `PRY`
     - `hondureno`, `hondurena`, `hondurenos`, `hondurenas` -> `HND`
     - `guatemalteco`, `guatemalteca`, `guatemaltecos`, `guatemaltecas` -> `GTM`
     - `salvadoreno`, `salvadorena`, `salvadorenos`, `salvadorenas` -> `SLV`
     - `nicaraguense`, `nicaraguenses` -> `NIC`
     - `dominicano`, `dominicana`, `dominicanos`, `dominicanas` -> `DOM`
     - `venezolano`, `venezolana`, `venezolanos`, `venezolanas` -> `VEN`
     - `cubano`, `cubana`, `cubanos`, `cubanas` -> `CUB`
     - `haitiano`, `haitiana`, `haitianos`, `haitianas` -> `HTI`
   - In `QueryParser.parse` Step 5, right after `elif "gini" in clean or "desigualdad" in clean:`:
     ```python
     elif any(term in clean for term in ["poblacion", "habitantes", "demografia", "demografico", "demograficos"]):
         intent.root_concept = "POBLACION"
     ```

2. In `src/statscepal/semantic/facet_ontology.py`:
   - In `FacetDefinition(facet_key="etnia"...)`:
     - Add `78149` (for 4968) and `140625` (for 4969) to `known_dimension_ids`.
     - In `dimension_name_patterns`: add `"condicion indigena"`, `"condicion afrodescendiente"`.
     - In `member_value_patterns["ETNICO_TOTAL"]`: add `("indigena", "no indigena", "afrodescendiente", "no afrodescendiente", "etnia", "etnico", "etnica")`.

3. In `src/statscepal/semantic/registry.py`:
   - Add `"POBLACION": 4788` to `OFFICIAL_25_CANONICAL_DEFAULTS` and `LEGACY_50_CANONICAL_DEFAULTS`.
   - Register dimensions for `4788, 4968, 4969, 4992, 4639` in `DEFAULT_OFFICIAL_DIMENSIONS`:
     - `4788`: Dim `88622` ("Sexo", members: Ambos sexos 88623, Hombres 88626, Mujeres 88627)
     - `4968`: Dim `48525` ("Area Geografica", members: Total 48529, Urbano 48526, Rural 48528), Dim `78149` ("Condición Indígena", members: Indígena 78150, No Indígena 78152, Total 78154)
     - `4969`: Dim `48525` ("Area Geografica", members: Total 48529, Urbano 48526, Rural 48528), Dim `140625` ("Condición Afrodescendiente", members: Afrodescendiente 140626, No Afrodescendiente 140627, Total 140629)
     - `4992`: Dim `48525` ("Area Geografica", members: Total 48529, Urbano 48526, Rural 48528)
     - `4639`: Dim `144` ("Sexo__ESTANDAR", members: Ambos sexos 146, Hombres 265, Mujeres 266), Dim `378` ("Quintil", members: Quintil 1..5, Total quintiles 379), Dim `43039` ("Tipo de etnia", members: Indígena 77477, Afrodescendiente 43044, No indígena ni afrodescendiente 43043, Total 43040)
   - Add metadata for `4788, 4968, 4969, 4992, 4639` to `VERTICAL_SLICE_INDICATORS` with concept `"POBLACION"`, measure type `CONTEO_PERSONAS` or `VOLUMEN_REAL`, unit `"personas"`, and `4788` relationships to `4968, 4969, 4992, 4639` as `RelationshipType.BREAKDOWN_OF`.

4. In `src/statscepal/semantic/engine.py`:
   - In Stage 3 candidate selection, if `intent.root_concept == "POBLACION"`:
     - If `intent.facets.get("etnia") == "AFRODESCENDIENTE"`: `canonical_id = 4969`
     - Else if `"estrato"` in intent.facets and `"etnia"` in intent.facets: `canonical_id = 4639`
     - Else if `"etnia"` in intent.facets: `canonical_id = 4968`
     - Else if `"area"` in intent.facets: `canonical_id = 4992`
     - Else: `canonical_id = 4788`

### 3. TDD Green & Regression Verification
- Run: `uv run pytest tests/test_semantic_breakdowns.py -v`
- Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`
- Run: `uv run pytest tests/test_semantic_facet_coverage.py -v`
- Run: `uv run pytest -m "not integration"`

### 4. Git Commit
```bash
git add src/statscepal/semantic/parser.py src/statscepal/semantic/facet_ontology.py src/statscepal/semantic/registry.py src/statscepal/semantic/engine.py tests/test_semantic_breakdowns.py
git commit -m "feat(semantic): support Latin American demonyms and demographic ethnic population resolution"
```

### 5. Report
Write `task-3-report.md` in `C:\papx\statscepal\.superpowers\sdd\2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan\task-3-report.md`.
