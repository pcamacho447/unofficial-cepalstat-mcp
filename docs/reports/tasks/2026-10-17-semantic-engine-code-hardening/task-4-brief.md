# Task 4 Brief: Dynamic conversational_hint Generation for Controlled Ambiguities in SemanticResolutionEngine Stage 3

## Mission
1. In `src/statscepal/semantic/engine.py` (Stage 3, around lines 240–265):
   - Replace the hardcoded `else:` fallback (which previously hardcoded ID 127 and 119) with dynamic conversational hint construction:
     ```python
     alt_summary = ", ".join(
         f"{a.name} (ID {a.indicator_id})" for a in alternatives
     )
     conv_hint = (
         f"Se seleccionó '{prim_meta.name}' (ID {primary_id}). "
         f"Alternativas metodológicas disponibles: {alt_summary}."
     )
     ```
   - Keep specific customized messages for `FEMININITY_INDEX`, `INCOME_MEASURES`, and `URBAN_UNEMPLOYMENT`.
2. In `tests/test_semantic_generic_gate.py`:
   - Add unit test `test_stage3_ambiguity_conversational_hint_matches_selected_and_alternative_indicators`.
   - Test queries:
     - `"cuentas fiscales en colombia 2022"` (1240, 1241)
     - `"economia de chile en 2022"` (729, 730)
     - `"inflacion sectorial en peru 2022"` (2928, 2929)
     - `"sector externo en mexico 2022"` (1243, 1244)
     - `"emisiones de gases de efecto invernadero en brasil 2021"` (5681, 5682)
   - Assert `expected_primary_id` and `expected_alt_id` are in `res.conversational_hint`, and `"127"` / `"119"` are NOT present.

## Base Commit
`7c2f146`

## Constraints
- Python 3.10+ modern typing syntax.
- All non-integration tests (294+) must pass without regression.
- False Substitution Rate must strictly equal 0.00% across the 200-question benchmark.
- Top-1 Accuracy across the 200 benchmark test cases must strictly remain 100.0%.
- Local resolution latency over SQLite and in-memory thesaurus must maintain p50 < 0.5 ms.
- Safe UTF-8 encoding for Windows console environments.
- Strict offline hermeticity: test suites must NEVER perform live network calls to CEPALSTAT.
