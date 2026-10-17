# Task 1 Brief: Generic Multi-Member Breakdowns in FacetOntology & QueryParser

Plan: `docs/superpowers/plans/2026-10-17-semantic-engine-code-hardening-plan.md`

## Requirements
1. In `src/statscepal/semantic/facet_ontology.py`:
   - In `FacetDefinition(facet_key="sexo")`:
     - Add `"SEXO_DESGLOSE": ("hombres", "mujeres")` to `member_value_patterns`.
     - Set `breakdown_values=frozenset({"SEXO_DESGLOSE"})`.
     - Prepend to `query_triggers`:
       `QueryTriggerRule(canonical_value="SEXO_DESGLOSE", phrases=("por sexo", "segun sexo", "por genero", "segun genero"))`
   - In `FacetDefinition(facet_key="area")`:
     - Add `"AREA_DESGLOSE": ("urbano", "rural")` to `member_value_patterns`.
     - Set `breakdown_values=frozenset({"AREA_DESGLOSE"})`.
     - Prepend to `query_triggers`:
       `QueryTriggerRule(canonical_value="AREA_DESGLOSE", phrases=("por area", "segun area", "por area geografica", "segun area geografica", "urbano y rural", "urbana y rural"))`
   - In `FacetDefinition(facet_key="edad")`:
     - Add `"EDAD_DESGLOSE": ("0 a 14", "15 a 24", "65")` to `member_value_patterns`.
     - Set `breakdown_values=frozenset({"EDAD_DESGLOSE"})`.
     - Prepend to `query_triggers`:
       `QueryTriggerRule(canonical_value="EDAD_DESGLOSE", phrases=("por edad", "segun edad", "por grupo de edad", "por grupos de edad", "segun grupo de edad", "segun grupos de edad"))`
   - In `FacetDefinition(facet_key="estrato")`:
     - Set `breakdown_values=frozenset({"QUINTIL", "DECIL"})`.
     - Update `member_value_patterns["DECIL"]` to `("decil", "deciles")`.

2. In `src/statscepal/semantic/parser.py`:
   - Ensure generic ontology breakdown values (`AREA_DESGLOSE`, `SEXO_DESGLOSE`, `EDAD_DESGLOSE`) extracted via `ontology.extract_facets_from_query` are retained in `facets` and not overwritten by implicit national/both defaults (`NACIONAL`, `AMBOS`).

3. In `tests/test_semantic_breakdowns.py`:
   - Add test `test_generic_breakdowns_for_sexo_area_edad_and_deciles` verifying:
     - `"pobreza por sexo en peru 2022"` swaps to 3341 (or 3342) and binds `Sexo__ESTANDAR` with `is_breakdown=True` containing `Hombres` and `Mujeres`.
     - `"pobreza por area en peru 2022"` stays on 3328 and binds `Área geográfica` with `is_breakdown=True` containing `Urbano` and `Rural`.
     - `"pobreza por edad en peru 2022"` swaps to 3341 and binds `Grupo de edad` with `is_breakdown=True` containing at least 3 age groups.
     - `"distribucion del ingreso por deciles en peru 2022"` resolves to 3340 and binds `Estrato de ingreso` with `is_breakdown=True` containing `Primer decil`, `Décimo decil`, `Deciles`.

4. Global Constraints:
   - Python 3.10+ modern typing syntax.
   - All 289+ existing non-integration tests must pass without regression.
   - Maintain 100.0% Top-1 Accuracy and 0.00% False Substitution Rate on the 200-question benchmark (`tests/test_semantic_benchmark_200.py`) and facet-coverage benchmark (`tests/test_semantic_facet_coverage.py`).
   - Resolution latency p50 < 0.5 ms.
   - Hermetic offline tests (no live network calls).

## Verification Commands
- `uv run pytest tests/test_semantic_breakdowns.py -v`
- `uv run pytest tests/test_semantic_facet_coverage.py -v`
- `uv run pytest tests/test_semantic_benchmark_200.py -v`
- `uv run pytest -m "not integration"`
