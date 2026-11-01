# Semantic Robustness, Mutation Benchmarks & Abstention Diagnostics Specification

**Date:** 2026-10-31  
**Status:** Approved  
**Scope:** `src/unofficial_cepalstat_mcp/semantic/`, `tests/`  

---

## 1. Context & Motivation

Following the completion of Phases 1, 2, and 3 of the Semantic Scaling plan, probe queries with unseen natural language variations revealed three critical edge cases that jeopardize the engine's core promise of **0.00% False Substitution Rate (FSR)** and clear agentic communication:

1. **Silent False Substitutions on Measure Modifiers & Sub-pollutants:**
   A query like `"emisiones de co2 per capita en mexico 2019"` resolves with score 1.0 to indicator `5681` (*"Emisiones totales de GEI incluyendo sector UTCUTS / con LULUCF"*), which is in Gigagrams of CO2 equivalent for all greenhouse gases, completely ignoring both the specific gas (`co2`) and the denominator (`per cápita`). CEPALSTAT actually contains indicator `5649` (*"Emisiones de dióxido de carbono (CO2) por habitante"*), but Tier 1 eagerly matched `5681` because neither `co2` nor `capita` was classified as a `CRITICAL_SPECIFICITY_TOKEN`.

2. **Benchmark Circularity & Lack of Mutation Robustness:**
   Existing benchmark suites (200 canonical, 40 adversarial, 100 catalog-scale) were tuned iteratively alongside the engine rules. While they verify that known queries pass, they lack:
   - An independent, blind **hold-out benchmark** of 50 queries covering natural phrasing variations across all 23 domains.
   - **Mutation tests**: systematically altering valid queries with unexpected modifiers (e.g., adding `"per cápita"`, `"por signo zodiacal"`, changing country to a non-LAC country, or requesting real-time frequency). Under mutation, the engine must adapt (re-route, filter), propose alternatives, or abstain—*never* return the identical aggregate indicator with score 1.0.

3. **Masked & Misleading Abstention Diagnostics:**
   Queries for non-LAC countries (e.g. `"pib de alemania 2022"`, `"tasa de paro en espana 2022"`) currently return `LOW_CONCEPTUAL_RELEVANCE` with the hint *"No se identificó un fenómeno socioeconómico cubierto por el catálogo de CEPALSTAT"*. This is actively misleading: the economic phenomenon (PIB, desempleo) is standard in CEPALSTAT, but the geography (Germany, Spain) is outside UN ECLAC's mandate. The root cause is that `QueryParser` sets `unknown_concept = True` alongside `unsupported_facet = "UNSUPPORTED_COUNTRY_NON_LAC_..."`, and `engine.py` evaluates `unknown_concept` before `unsupported_facet`.

---

## 2. Requirements & Invariants

### 2.1. Measure Modifier & Sub-pollutant Guardrail (Point 1)
- **Token Classification:** Extend `CRITICAL_SPECIFICITY_TOKENS` in `engine.py` to include:
  - Measure units & denominators: `"capita"`, `"habitante"`, `"tasa"`, `"ratio"`, `"proporcion"`, `"porcentaje"` (when not acting as relative denominator).
  - Gas & pollutant specifications: `"co2"`, `"metano"`, `"oxido"`, `"nitroso"`, `"fluorados"`.
  - Net vs gross accounting: `"brutas"`, `"netas"`.
- **Parser Specificity:**
  - `QueryParser` must not collapse queries mentioning `"co2"` or `"per capita"` / `"por habitante"` into coarse `EMISIONES_GEI_LULUCF` without preserving these tokens in `unconsumed_tokens`.
  - When `intent.root_concept == "EMISIONES_GEI_LULUCF"`, if `co2` or `per capita` is present in unconsumed tokens, Stage 3.5 Specificity Guard must reject `5681`.
- **Tier-2 Recovery or Safe Abstention:**
  - When Stage 3.5 flags uncovered critical tokens, instead of immediately abstaining if `enable_tier2_catalog` is enabled, the engine must consult Tier-2. If Tier-2 finds an indicator covering those tokens (e.g. `5649` for CO2 per habitante), it routes to that indicator. If none exists, it abstains with `UNSUPPORTED_SPECIFICITY_<TOKEN>` or proposes `ALTERNATIVE_PROPOSED`.

### 2.2. Independent Hold-Out & Mutation Benchmarking (Point 2)
- **Independent Hold-Out Suite (50 Cases):**
  - Stored in `tests/benchmark/independent_holdout_benchmark_50.json`.
  - Contains 35 positive queries across varied domains using diverse phrasing (e.g., regionalisms, compound sentences, relative windows, multi-country comparisons) and 15 adversarial traps (non-LAC countries, daily financial variables, unsupported breakdowns).
  - Target: `>= 95%` accuracy, `0.00% FSR`, `p50 < 0.5 ms`.
- **Mutation Testing Framework:**
  - Implemented in `tests/test_semantic_mutations.py`.
  - Applies 4 systematic mutation operators to base queries:
    1. *Denominator Mutation:* Append `"per cápita"` or `"en porcentaje del PIB"`.
    2. *Unsupported Breakdown Mutation:* Append `"por tipo de sangre"` or `"por religión"`.
    3. *Geography Invalidation:* Replace LAC country with non-LAC country (`ESP`, `DEU`, `FRA`, `USA`, `JPN`).
    4. *Frequency Invalidation:* Append `"en tiempo real"` or `"al minuto"`.
  - Invariant: In 100% of mutations, `mutated_response != base_response` (status changes, candidate changes, applied filters change, or engine abstains).

### 2.3. Accurate Abstention Hierarchy & Clear Diagnostics (Point 4)
- **Execution Order in `SemanticResolutionEngine`:**
  1. `intent.unsupported_facet` (including `UNSUPPORTED_COUNTRY_NON_LAC_<ISO>` and `UNSUPPORTED_GEOGRAPHY_<NAME>`) evaluated **FIRST**.
  2. `intent.unsupported_frequency` evaluated **SECOND**.
  3. `intent.period_out_of_range` evaluated **THIRD**.
  4. `intent.unknown_concept` evaluated **FOURTH**.
  5. `not intent.root_concept` (Tier-2 fallback or `LOW_CONCEPTUAL_RELEVANCE`) evaluated **FIFTH**.
- **Diagnostic Hint Clarity:**
  - `UNSUPPORTED_COUNTRY_NON_LAC_<ISO>`:
    *Reason:* `UNSUPPORTED_COUNTRY_NON_LAC_<ISO>`
    *Hint:* `"El país '{name}' ({iso}) se encuentra fuera del ámbito geográfico de la CEPAL (América Latina y el Caribe)."`
  - `NON_LAC_COUNTRIES` in `parser.py`: Do NOT set `intent.unknown_concept = True` when a non-LAC country is recognized. Set only `intent.unsupported_facet = f"UNSUPPORTED_COUNTRY_NON_LAC_{code}"` and populate `intent.country_code = code` (or `intent.unsupported_country = code`).
  - Add standard non-LAC countries: `"alemania"`, `"espana"`, `"francia"`, `"italia"`, `"reino unido"`, `"estados unidos"`, `"eeuu"`, `"china"`, `"japon"`, `"canada"`, `"rusia"`, `"brasil"` (is LAC!), `"portugal"`, `"australia"`, `"india"`.
  - Distinguish daily/real-time financial queries (`"precio del dolar"`, `"tipo de cambio hoy"`, `"tasa de cambio en tiempo real"`): hint explicitly states CEPALSTAT publishes statistical macro indicators, not real-time FX/financial tickers.
