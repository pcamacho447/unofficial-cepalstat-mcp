# Task 1 Brief: Core FacetOntology Data Models & Declarative Registry

## Context
- Working Directory: `C:\papx\statscepal`
- Base Commit: `05cff68`
- Plan: `docs/superpowers/plans/2026-10-16-task-e2-declarative-facet-ontology-plan.md`

## Objectives
1. Create `src/statscepal/semantic/facet_ontology.py`:
   - Data models: `QueryTriggerRule`, `FacetDefinition`, `FacetOntology`.
   - `DEFAULT_FACET_ONTOLOGY` instance populated with standard CEPALSTAT socioeconomic and demographic facets:
     - `sexo`: IDs `{144}`, name patterns `("sexo", "genero")`, implicit aggregate `{"TOTAL", "AMBOS_SEXOS", "AMBOS"}`.
     - `area`: IDs `{326, 1364}`, name patterns `("area", "zona", "area geografica")`, implicit aggregate `{"NACIONAL"}`.
     - `severidad`: IDs `{1361, 500}`, name patterns `("pobreza", "severidad", "tipo de pobreza", "condicion de pobreza")`, implicit aggregate `{"POBREZA_TOTAL"}`.
     - `etnia`: IDs `{43039}`, name patterns `("etnia", "tipo de etnia", "autoidentificacion etnico-racial", "etnico", "etnico-racial", "raza")`, implicit aggregate `frozenset()` (requires dimension even on total).
     - `edad`: name patterns `("edad", "grupo de edad", "tramo de edad", "grupos de edad")`, implicit aggregate `frozenset()`.
     - `estrato` / `quintil`: name patterns `("quintil", "decil", "estrato")`, implicit aggregate `frozenset()`.
     - `educacion`: name patterns `("educacion", "anos de educacion", "nivel", "instruccion")`, implicit aggregate `frozenset()`.
     - `formalidad`: name patterns `("formalidad", "empleo formal", "informal")`, implicit aggregate `frozenset()`.
     - `moneda`, `actividad`, `canasta`, `rubro`.
   - Structural dimension identification:
     - `is_structural_dimension(dim_id: int, dim_name: str) -> bool`: returns True for Country (`País`, ID 208) and Time (`Años`, ID 29117, `Trimestre`, `Mes`).
     - `classify_dimension(dim_id: int, dim_name: str) -> str | None`: returns matching `facet_key`, `"__structural__"`, or `None` if unmapped.
     - `is_critical_unhandled_facet(facet_key: str, facet_value: str) -> bool`: True if facet is unknown or if `facet_value` is NOT in `facet_def.implicit_aggregate_values`.
     - `build_dimension_key_patterns()` and `build_member_value_patterns()`.
2. Follow strict TDD:
   - Create `tests/test_semantic_facet_ontology.py` with test cases:
     - `test_default_facet_ontology_covers_core_facets`
     - `test_facet_ontology_implicit_aggregate_vs_critical_breakdown`
     - `test_facet_ontology_dimension_classification`
   - Run red test: `uv run pytest tests/test_semantic_facet_ontology.py`
   - Implement `src/statscepal/semantic/facet_ontology.py`.
   - Run green test: `uv run pytest tests/test_semantic_facet_ontology.py`
   - Run full non-integration suite: `uv run pytest -m "not integration"`
3. Commit:
   `git add src/statscepal/semantic/facet_ontology.py tests/test_semantic_facet_ontology.py`
   `git commit -m "feat(semantic): implement declarative FacetOntology models and default registry"`
4. Write report to `.superpowers/sdd/2026-10-16-task-e2-declarative-facet-ontology/task-1-report.md`.
