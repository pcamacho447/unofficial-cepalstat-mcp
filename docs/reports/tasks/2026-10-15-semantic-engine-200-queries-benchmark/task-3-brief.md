# Task 3 Brief: Parser & Matcher Enhancements for Income Modifiers and Regionalisms

## Requirements
Working directory: `C:\papx\statscepal`

You are implementing Task 3 of the 200-Question Empirical Benchmark Plan.
You must update `QueryParser` (`src/statscepal/semantic/parser.py`), `SemanticResolutionEngine` (`src/statscepal/semantic/engine.py`), and `DynamicMemberMatcher` (`src/statscepal/semantic/matcher.py`) to properly desconstruct and disambiguate complex income terminology, regionalisms, and composite indicator precedence.

### Specific Features to Implement:
1. **Income Modifier Desconstructor:**
   - Detect context modifiers around "guita", "plata", "sueldo", "salario", "ingreso":
     - If contains terms like "minima", "minimo", "por ley", "sueldo basico" -> `SALARIO_MINIMO` -> maps to Indicator `3337` ("Salario mínimo real").
     - If contains terms like "de los laburantes", "trabajadores", "asalariados", "medio", "remuneraciones" -> `SALARIO_REAL` -> maps to Indicator `128` ("Índice del salario medio real").
     - If contains terms like "de los hogares", "familias", "por cabeza", "per capita" -> `INGRESO_HOGAR_PER_CAPITA` -> maps to Indicator `3345` ("Ingreso medio per cápita de los hogares").
     - If query contains "guita", "plata", "ingreso" with NO modifiers (e.g., "Como estuvo la guita en Chile en 2021", "Cual fue el ingreso en Mexico") -> Set `is_ambiguous_measure = True`, `ambiguous_candidate = "INCOME_MEASURES"`, status `ALTERNATIVE_PROPOSED`, proposing alternatives `[3337, 3345, 128]`.
2. **Expanded Regionalisms:**
   - Chilean slang: *"pega"* (empleo/desocupación), *"lucas"* (plata/ingreso), *"cabros"* (jóvenes, edad=JUVENTUD).
   - Rioplatense slang: *"guita"* (ingreso/salario), *"laburantes"* / *"laburo"* (trabajo/asalariados), *"pibes"* / *"pibas"* (jóvenes, sexo).
   - Mexican slang: *"chamba"* (empleo), *"lana"* (ingreso), *"chavos"* / *"chavas"* (jóvenes, sexo).
   - Colombian/Andean slang: *"camello"* (empleo), *"corrientazo"* (alimentos), *"plata"* (ingreso).
3. **Composite Precedence Safeguards:**
   - Terms like "como porcentaje del PIB" or "% del PIB" for Debt (1240), Primary Balance (1241), Tax Revenues (1242), Current Account (1243) must NEVER be shadowed by generic GDP (729).
   - Terms like "emisiones sin LULUCF" or "sin UTCUTS" must map to `5682`, while general/con LULUCF maps to `5681`.

## TDD Instructions
1. Write unit tests in `tests/test_parser_income_modifiers.py` covering all modifier disambiguations, ambiguity states, regionalisms, and precedence rules.
2. Run `uv run pytest tests/test_parser_income_modifiers.py` and capture RED failing output.
3. Update `src/statscepal/semantic/parser.py`, `src/statscepal/semantic/engine.py`, and `src/statscepal/semantic/matcher.py`.
4. Run `uv run pytest tests/test_parser_income_modifiers.py` and capture GREEN passing output.
5. Run full non-integration test suite: `uv run pytest -m "not integration"`.
6. Commit:
   `git add src/statscepal/semantic/ tests/test_parser_income_modifiers.py`
   `git commit -m "feat(semantic): implement income modifier context parsing and ambiguity safeguards"`
7. Write full report to:
   `.superpowers/sdd/2026-10-15-semantic-engine-200-queries-benchmark-plan/task-3-report.md`
