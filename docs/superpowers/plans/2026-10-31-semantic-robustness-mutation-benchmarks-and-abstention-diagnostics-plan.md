# Semantic Robustness, Mutation Benchmarks & Abstention Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate silent false substitutions on measure modifiers (e.g. CO2 vs all GHGs, per cápita vs totals), introduce independent hold-out & mutation testing suites, and establish an accurate, unmasked abstention hierarchy for out-of-scope geographies and frequencies.

**Architecture:** Extend Stage 3.5 Specificity Guard in `SemanticResolutionEngine` to evaluate measure units, denominators (`capita`, `tasa`, `ratio`) and specific pollutants (`co2`, `metano`), recovering matching indicators via Tier 2 (e.g. `5649` for CO2 per habitante) or failing closed. Reorder Stage 1/2 abstentions so `unsupported_facet` (including `UNSUPPORTED_COUNTRY_NON_LAC_<ISO>`) precedes `unknown_concept`, with tailored conversational hints. Enforce robustness through an independent 50-query hold-out benchmark across all 23 CEPALSTAT areas and a 4-operator mutation test suite guaranteeing that modifying a query never returns the identical aggregate with score 1.0.

**Tech Stack:** Python >=3.10, `uv`, `pytest`, `pydantic` v2, `sqlite3`, `mypy`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-10-31-semantic-robustness-and-diagnostics-spec.md`

## Global Constraints

- Import always from `unofficial_cepalstat_mcp` (never `from statscepal`).
- Always run `uv run pytest -m "not integration"`; zero live network requests in unit and benchmark suites.
- Preserve **0.00% False Substitution Rate (FSR)** across all benchmarks: 200 canonical + 40 adversarial + 100 catalog scale + 50 hold-out.
- Maintain local semantic resolution latency strictly at **`p50 < 0.5 ms` and `p95 < 2.0 ms`** (Guardrail #4).
- Never mutate `SemanticResolutionResponse` in-place.
- Pass `uv run mypy src/unofficial_cepalstat_mcp/`, `uv run ruff check .`, and `uv build` cleanly with 0 errors.

## Review Focus

1. **Specific pollutant & denominator leakage (`"emisiones de co2 per capita en mexico 2019"`):** Must not eagerly return `5681` (Gg CO2-eq all GHGs, gross total); must resolve to `5649` (*"Emisiones de dióxido de carbono (CO2) por habitante"*) or abstain fail-closed if Tier 2 is disabled.
2. **Geographic masking in non-LAC queries (`"pib de alemania 2022"`, `"tasa de paro en espana 2022"`):** Must return `UNSUPPORTED_COUNTRY_NON_LAC_<ISO>` with an explicit geography hint, not `LOW_CONCEPTUAL_RELEVANCE`.
3. **Daily / real-time financial traps (`"precio del dolar en peru hoy"`, `"tipo de cambio en tiempo real"`):** Must explain clearly that CEPALSTAT publishes statistical time series, not daily/real-time financial tickers.
4. **Mutation sensitivity:** Modifying any valid query with an unsupported breakdown, a non-LAC country, or a conflicting measure modifier must alter the outcome (change indicator, add dimension filter, propose alternatives, or abstain), never silently return the base aggregate with score 1.0.
5. **Hold-out independence:** The 50 hold-out queries must evaluate natural variations across all 23 domains without tailoring parser regexes to fit specific hold-out sentences.

---

## File Structure

- **Modify:** `src/unofficial_cepalstat_mcp/semantic/parser.py:338-375` — Update `NON_LAC_COUNTRIES` handling to set `unsupported_facet` without setting `unknown_concept=True`; preserve `co2` and `per capita` tokens in `unconsumed_tokens`.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/engine.py:38-55, 280-360, 395-440` — Reorder Stage 1/2 abstentions (`unsupported_facet` before `unknown_concept`); expand `CRITICAL_SPECIFICITY_TOKENS` with measure modifiers and pollutants; route Stage 3.5 uncovered measure tokens to Tier 2 recovery or fail-closed abstention.
- **Modify:** `tests/benchmark/catalog_scale_benchmark_cases_100.json:690-755` — Sync expected reason for non-LAC country queries to `UNSUPPORTED_COUNTRY_NON_LAC`.
- **Create:** `tests/test_semantic_abstention_diagnostics.py` — Test precision of non-LAC country, unsupported frequency, and geographic hints.
- **Create:** `tests/test_semantic_measure_modifiers.py` — Test CO2 vs GEI, per cápita vs totals, and net vs gross specificity guards.
- **Create:** `tests/benchmark/independent_holdout_benchmark_50.json` — 50 unseen queries (35 positive across 23 areas + 15 adversarial traps).
- **Create:** `tests/test_independent_holdout_benchmark_50.py` — Automated runner certifying 0.00% FSR, >=95% accuracy, and p50 < 0.5 ms.
- **Create:** `tests/test_semantic_mutations.py` — Mutation testing suite applying 4 operators to assert non-silent degradation.

---

### Task 1: Accurate Abstention Hierarchy & Non-LAC Country Diagnostics (Point 4)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/parser.py:340-365`
- Modify: `src/unofficial_cepalstat_mcp/semantic/engine.py:280-335`
- Modify: `tests/benchmark/catalog_scale_benchmark_cases_100.json:690-755`
- Create: `tests/test_semantic_abstention_diagnostics.py`

**Interfaces:**
- Consumes: `ParsedIntent.unsupported_facet`, `NON_LAC_COUNTRIES` in `parser.py`
- Produces:
  - `SemanticResolutionResponse.abstention_reason == "UNSUPPORTED_COUNTRY_NON_LAC_<ISO>"`
  - `SemanticResolutionResponse.conversational_hint` with explicit mention of the out-of-scope country name and UN ECLAC regional scope.
  - Prioritized Stage 1/2 checks: `unsupported_facet` -> `unsupported_frequency` -> `period_out_of_range` -> `unknown_concept` -> `root_concept`.

- [ ] **Step 1: Write failing tests for accurate abstention diagnostics**

Create `tests/test_semantic_abstention_diagnostics.py`:
```python
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus


def test_non_lac_countries_emit_explicit_geographic_abstention_reason() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    cases = [
        ("pib de alemania 2022", "UNSUPPORTED_COUNTRY_NON_LAC_DEU", "Alemania"),
        ("tasa de paro en espana 2022", "UNSUPPORTED_COUNTRY_NON_LAC_ESP", "España"),
        ("inflacion en francia 2021", "UNSUPPORTED_COUNTRY_NON_LAC_FRA", "Francia"),
        ("pobreza extrema en estados unidos 2020", "UNSUPPORTED_COUNTRY_NON_LAC_USA", "Estados Unidos"),
        ("poblacion de japon 2022", "UNSUPPORTED_COUNTRY_NON_LAC_JPN", "Japón"),
        ("balanza comercial de italia 2020", "UNSUPPORTED_COUNTRY_NON_LAC_ITA", "Italia"),
    ]
    for query, expected_reason, expected_country_hint in cases:
        resp = engine.resolve(query)
        assert resp.status == ResolutionStatus.ABSTAINED, f"Failed for '{query}': {resp.status}"
        assert resp.abstention_reason == expected_reason, f"Failed reason for '{query}': {resp.abstention_reason}"
        assert resp.unsupported_facet == expected_reason
        assert expected_country_hint.lower() in (resp.conversational_hint or "").lower()
        assert "fuera del ambito geografico" in (resp.conversational_hint or "").lower() or "fuera del ámbito geográfico" in (resp.conversational_hint or "").lower()


def test_daily_financial_queries_emit_informative_frequency_and_domain_hint() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    resp = engine.resolve("precio del dolar en peru hoy")
    assert resp.status == ResolutionStatus.ABSTAINED
    assert resp.abstention_reason in ("UNSUPPORTED_FREQUENCY", "OUT_OF_SCOPE_DAILY_FINANCIAL")
    assert "tiempo real" in (resp.conversational_hint or "").lower() or "diaria" in (resp.conversational_hint or "").lower() or "periodicidad" in (resp.conversational_hint or "").lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_abstention_diagnostics.py -v`
Expected: FAIL (`assert 'LOW_CONCEPTUAL_RELEVANCE' == 'UNSUPPORTED_COUNTRY_NON_LAC_DEU'`).

- [ ] **Step 3: Implement abstention reordering and non-LAC country diagnostic hints**

1. In `src/unofficial_cepalstat_mcp/semantic/parser.py:340-365`:
   - Keep `NON_LAC_COUNTRIES` mapping (`"alemania": "DEU"`, `"espana": "ESP"`, `"francia": "FRA"`, `"italia": "ITA"`, `"reino unido": "GBR"`, `"estados unidos": "USA"`, `"eeuu": "USA"`, `"china": "CHN"`, `"japon": "JPN"`, `"canada": "CAN"`, `"portugal": "PRT"`, `"australia": "AUS"`, `"rusia": "RUS"`, `"india": "IND"`).
   - In loop matching non-LAC countries: set `intent.unsupported_facet = f"UNSUPPORTED_COUNTRY_NON_LAC_{non_lac_code}"` and `intent.country_code = non_lac_code`, but **do not** set `intent.unknown_concept = True`.
2. In `src/unofficial_cepalstat_mcp/semantic/engine.py:284-335`:
   - Evaluate `if intent.unsupported_facet:` **before** `if intent.unknown_concept:`.
   - When `intent.unsupported_facet.startswith("UNSUPPORTED_COUNTRY_NON_LAC_")`:
     Extract the ISO code, look up country display name, and format:
     `conversational_hint = f"El país '{display_name}' ({iso}) se encuentra fuera del ámbito geográfico de la CEPAL (América Latina y el Caribe)."`
   - Evaluate `if intent.unsupported_frequency:` next, providing a clear hint that CEPALSTAT publishes statistical indicator series (annual/quarterly), not daily market or real-time ticker data.
3. In `tests/benchmark/catalog_scale_benchmark_cases_100.json:690-755`:
   - Update cases `SCALE_086` to `SCALE_092` to set `"expected_reason": "UNSUPPORTED_COUNTRY_NON_LAC"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_semantic_abstention_diagnostics.py tests/test_catalog_scale_benchmark_100.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/parser.py src/unofficial_cepalstat_mcp/semantic/engine.py tests/benchmark/catalog_scale_benchmark_cases_100.json tests/test_semantic_abstention_diagnostics.py
git commit -m "fix(semantic): prioritize unsupported geography over unknown concept with informative non-LAC hints"
```

---

### Task 2: Measure Modifier & Pollutant Specificity Guards with Tier-2 Recovery (Point 1)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/engine.py:38-65, 395-430, 715-760`
- Modify: `src/unofficial_cepalstat_mcp/semantic/parser.py:965-998`
- Create: `tests/test_semantic_measure_modifiers.py`

**Interfaces:**
- Consumes: `CRITICAL_SPECIFICITY_TOKENS`, `SemanticRegistry.search_candidates`, `CatalogStore`
- Produces:
  - Inclusion of measure tokens (`"co2"`, `"metano"`, `"capita"`, `"habitante"`, `"tasa"`, `"ratio"`, `"proporcion"`) in `CRITICAL_SPECIFICITY_TOKENS`.
  - Preservation of `"co2"` and `"capita"` in `intent.unconsumed_tokens` when coarse emissions are parsed.
  - Stage 3.5 Specificity Guard triggering Tier-2 catalog recovery: if candidate `5681` lacks `co2` or `per capita`, query Tier-2 for exact indicator (`5649` *"Emisiones de dióxido de carbono (CO2) por habitante"*); if resolved, return `5649`; if Tier-2 is disabled or no indicator matches, fail closed with `ABSTAINED` or `ALTERNATIVE_PROPOSED`.

- [ ] **Step 1: Write failing tests for measure modifier and pollutant guards**

Create `tests/test_semantic_measure_modifiers.py`:
```python
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus


def test_co2_per_capita_emissions_resolves_to_specific_indicator_not_gross_gei() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    resp = engine.resolve("emisiones de co2 per capita en mexico 2019")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    # Must resolve to 5649 (CO2 por habitante), NEVER 5681 (GEI total con LULUCF)
    assert resp.selected_candidate.indicator_id == 5649
    assert "5681" not in str(resp.selected_candidate.indicator_id)


def test_co2_per_capita_fails_closed_in_official_25_profile() -> None:
    engine = SemanticResolutionEngine(catalog_profile="official_25")
    resp = engine.resolve("emisiones de co2 per capita en mexico 2019")
    # In official_25, 5649 is not in slice, so engine must abstain rather than returning false aggregate 5681
    assert resp.status in (ResolutionStatus.ABSTAINED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    if resp.status == ResolutionStatus.ABSTAINED:
        assert resp.selected_candidate is None or resp.selected_candidate.indicator_id != 5681


def test_gross_vs_net_and_methane_specificity() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    # Methane query should not resolve to gross CO2
    resp_ch4 = engine.resolve("emisiones de metano en colombia 2020")
    if resp_ch4.status == ResolutionStatus.RESOLVED:
        assert "metano" in (resp_ch4.selected_candidate.name.lower() if resp_ch4.selected_candidate else "")
    else:
        assert resp_ch4.status == ResolutionStatus.ABSTAINED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_measure_modifiers.py -v`
Expected: FAIL (`assert 5681 == 5649`).

- [ ] **Step 3: Implement measure modifier token guard and Tier-2 recovery**

1. In `src/unofficial_cepalstat_mcp/semantic/engine.py`:
   - Add to `CRITICAL_SPECIFICITY_TOKENS`:
     `"co2"`, `"metano"`, `"capita"`, `"habitante"`, `"tasa"`, `"ratio"`, `"proporcion"`, `"brutas"`, `"netas"`.
2. In `src/unofficial_cepalstat_mcp/semantic/parser.py:965-998`:
   - When matching `EMISIONES_GEI_LULUCF` or `EMISIONES_GEI_SIN_LULUCF`, do **not** add `"co2"`, `"metano"`, or `"capita"` / `"habitante"` to `consumed_phrases` unless they are explicitly part of the matched root concept.
3. In `src/unofficial_cepalstat_mcp/semantic/engine.py:395-430` (Stage 3.5 Specificity Guard):
   - When `uncovered_critical_early` is detected:
     If `self.enable_tier2_catalog`:
       Attempt Tier-2 catalog recovery using `self.registry.search_candidates(intent.concept_tokens, facets=intent.facets, country_code=intent.country_code)`.
       Filter candidates strictly requiring coverage of the uncovered critical tokens (e.g. `co2` and `habitante` / `capita`).
       If a qualified candidate (e.g. `5649`) is found with score >= 0.85, set `canonical_id = qualified_candidate_id` and continue to Stage 4/5.
       If multiple candidates compete, return `ALTERNATIVE_PROPOSED`.
       If no qualified candidate exists, abstain with `ABSTAINED: UNSUPPORTED_SPECIFICITY`.
     If `not self.enable_tier2_catalog`:
       Abstain with `ABSTAINED: UNSUPPORTED_SPECIFICITY` rather than returning the false aggregate fallback.

- [ ] **Step 4: Run measure modifier and regression tests**

Run: `uv run pytest tests/test_semantic_measure_modifiers.py tests/test_adversarial_benchmark_40.py tests/test_semantic_benchmark_200.py -v`
Expected: PASS (`5649` resolved for CO2 per capita, 0.00% FSR, 40/40 adversarial pass).

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/engine.py src/unofficial_cepalstat_mcp/semantic/parser.py tests/test_semantic_measure_modifiers.py
git commit -m "fix(semantic): guard measure modifiers and pollutants against false substitution with Tier-2 recovery"
```

---

### Task 3: Independent Hold-Out Benchmark (50 Cases) across 23 Areas (Point 2A)

**Files:**
- Create: `tests/benchmark/independent_holdout_benchmark_50.json`
- Create: `tests/test_independent_holdout_benchmark_50.py`

**Interfaces:**
- Consumes: Full catalog profile (`catalog_profile="full_catalog"`)
- Produces:
  - 50 diverse queries crafted independently of parser internal regexes: 35 positive queries across all 23 CEPALSTAT domains (national accounts, trade, social, environment, demographics, gender, cities, infrastructure, agriculture, etc.) and 15 adversarial traps.
  - Automated test runner asserting `accuracy >= 0.95`, `false_substitution_rate == 0.0`, and `p50 < 0.5 ms`.

- [ ] **Step 1: Create the 50-case independent hold-out dataset**

Create `tests/benchmark/independent_holdout_benchmark_50.json` with 50 structured cases:
- 35 positive cases covering natural conversational phrasing:
  - Compound and relative time: `"cuánto creció el producto bruto interno de perú en los últimos 3 años"`, `"evolución de la pobreza rural en bolivia entre 2018 y 2021"`.
  - Regional variations & acronyms: `"tasa de paro juvenil en chile 2022"`, `"PBI por habitante en uruguay 2020"`, `"recaudación del IVA en colombia 2021"`, `"remesas familiares en el salvador 2022"`.
  - Sectoral and environmental: `"generación eléctrica renovable en costa rica 2020"`, `"superficie boscosa en paraguay 2020"`, `"acceso a agua potable en honduras 2021"`, `"esperanza de vida de las mujeres en cuba 2020"`, `"tasa de fecundidad en guatemala 2022"`.
  - Macro-structural: `"deuda pública externa en argentina 2022"`, `"inversión extranjera directa en brasil 2021"`, `"exportaciones de cobre en chile 2022"`.
- 15 adversarial traps:
  - Non-LAC countries: `"desempleo en reino unido 2021"`, `"inflación en canadá 2022"`, `"pib per cápita de australia 2020"`.
  - Daily financial tickers: `"precio del euro en colombia hoy"`, `"cotización del barril de petróleo wti al cierre"`.
  - Unscientific/out-of-scope concepts: `"tasa de criminalidad por signo zodiacal en lima"`, `"felicidad según el horóscopo en quito"`.
  - Measure mismatch traps: `"emisiones de dióxido de carbono por persona en perú 2019"`.

- [ ] **Step 2: Create the automated benchmark runner**

Create `tests/test_independent_holdout_benchmark_50.py`:
```python
import json
import statistics
import time
from pathlib import Path

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus


def test_independent_holdout_benchmark_50() -> None:
    path = Path(__file__).parent / "benchmark" / "independent_holdout_benchmark_50.json"
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) == 50, f"Expected exactly 50 hold-out cases, got {len(cases)}"
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")

    passed_count = 0
    false_substitutions = 0
    latencies: list[float] = []

    for item in cases:
        t0 = time.perf_counter()
        resp = engine.resolve(item["query"])
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        exp_status = item["expected_status"]
        status_ok = resp.status.value == exp_status

        # FSR Check: if ABSTAINED was expected, returning RESOLVED is a false substitution
        if exp_status == "ABSTAINED" and resp.status == ResolutionStatus.RESOLVED:
            false_substitutions += 1

        # Check forbidden indicator
        if item.get("forbidden_indicator_id") and resp.selected_candidate:
            if resp.selected_candidate.indicator_id == item["forbidden_indicator_id"]:
                false_substitutions += 1
                status_ok = False

        # Indicator match for positive queries
        ind_ok = True
        if exp_status == "RESOLVED" and item.get("expected_indicator_id"):
            actual_id = resp.selected_candidate.indicator_id if resp.selected_candidate else None
            expected_ids = item.get("allowed_indicator_ids") or [item["expected_indicator_id"]]
            ind_ok = actual_id in expected_ids

        if status_ok and ind_ok:
            passed_count += 1

    accuracy = passed_count / len(cases)
    p50_ms = statistics.median(latencies)
    fsr = false_substitutions / len(cases)

    assert fsr == 0.0, f"False Substitution Rate must be 0.00%, got {fsr:.2%} ({false_substitutions} violations)"
    assert accuracy >= 0.95, f"Hold-out accuracy must be >= 95.0%, got {accuracy:.1%} ({passed_count}/50)"
    assert p50_ms < 0.5, f"p50 latency must be < 0.5 ms, got {p50_ms:.3f} ms"
```

- [ ] **Step 3: Run the hold-out benchmark**

Run: `uv run pytest tests/test_independent_holdout_benchmark_50.py -v`
Expected: PASS (Accuracy >= 95%, FSR == 0.00%, p50 < 0.5 ms).

- [ ] **Step 4: Commit**

```bash
git add tests/benchmark/independent_holdout_benchmark_50.json tests/test_independent_holdout_benchmark_50.py
git commit -m "test(benchmark): add independent 50-query hold-out evaluation suite across 23 domains"
```

---

### Task 4: Systematic Mutation Testing Framework against Silent Degradation (Point 2B)

**Files:**
- Create: `tests/test_semantic_mutations.py`

**Interfaces:**
- Consumes: `SemanticResolutionEngine(catalog_profile="full_catalog")`
- Produces:
  - Framework executing 4 mutation operators over base canonical queries:
    1. `mutate_denominator(query)`: e.g. adds `" per cápita"` or `" como porcentaje del PIB"`.
    2. `mutate_unsupported_breakdown(query)`: e.g. adds `" por tipo de sangre"` or `" por religión"`.
    3. `mutate_geography_invalidation(query)`: replaces LAC country with non-LAC country (`ESP`, `DEU`, `FRA`, `USA`).
    4. `mutate_frequency_invalidation(query)`: adds `" en tiempo real"` or `" al minuto"`.
  - Invariant: In **100% of mutations**, the engine's response must change. It is strictly forbidden for a mutated query to silently produce the base aggregate indicator with score 1.0 and identical dimension filters.

- [ ] **Step 1: Write the mutation testing suite**

Create `tests/test_semantic_mutations.py`:
```python
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus

BASE_QUERIES = [
    "inflación anual en Chile 2022",
    "pobreza en Colombia 2021",
    "desempleo en Perú 2022",
    "PIB en México 2021",
    "exportaciones de bienes en Brasil 2022",
    "salario mínimo en Uruguay 2021",
    "gasto social en Costa Rica 2020",
    "esperanza de vida en Ecuador 2022",
]


def test_mutations_never_return_silent_identical_aggregate() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")

    for base_query in BASE_QUERIES:
        base_resp = engine.resolve(base_query)
        assert base_resp.status == ResolutionStatus.RESOLVED
        base_id = base_resp.selected_candidate.indicator_id if base_resp.selected_candidate else None
        base_filters = base_resp.applied_filters.dimensions if base_resp.applied_filters else []

        # Operator 1: Unsupported Breakdown Mutation
        mut_breakdown = f"{base_query} por tipo de sangre"
        resp_b = engine.resolve(mut_breakdown)
        assert resp_b.status == ResolutionStatus.ABSTAINED, f"Must abstain on bogus breakdown: '{mut_breakdown}'"

        # Operator 2: Geography Invalidation Mutation
        # Replace country with España or Alemania
        mut_geo = base_query.replace("Chile", "España").replace("Colombia", "Alemania").replace("Perú", "Francia").replace("México", "Italia").replace("Brasil", "Japón").replace("Uruguay", "Canadá").replace("Costa Rica", "Reino Unido").replace("Ecuador", "Estados Unidos")
        resp_g = engine.resolve(mut_geo)
        assert resp_g.status == ResolutionStatus.ABSTAINED, f"Must abstain on non-LAC geography: '{mut_geo}'"
        assert "UNSUPPORTED_COUNTRY_NON_LAC" in (resp_g.abstention_reason or "")

        # Operator 3: Real-Time Frequency Invalidation Mutation
        mut_freq = f"{base_query} en tiempo real"
        resp_f = engine.resolve(mut_freq)
        assert resp_f.status == ResolutionStatus.ABSTAINED, f"Must abstain on real-time request: '{mut_freq}'"

        # Operator 4: Denominator / Unit Mutation
        # When query is modified with "per cápita", it must NOT return the identical total indicator without adapting
        if "PIB" in base_query or "gasto social" in base_query:
            mut_pc = f"{base_query} per cápita"
            resp_pc = engine.resolve(mut_pc)
            if resp_pc.status == ResolutionStatus.RESOLVED and resp_pc.selected_candidate:
                # Must adapt indicator (e.g. 2206 instead of 2204) or add dimension
                new_id = resp_pc.selected_candidate.indicator_id
                assert new_id != base_id or resp_pc.applied_filters.dimensions != base_filters, (
                    f"Query '{mut_pc}' silently returned identical aggregate indicator {base_id}!"
                )
```

- [ ] **Step 2: Run mutation tests to verify they pass**

Run: `uv run pytest tests/test_semantic_mutations.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_semantic_mutations.py
git commit -m "test(semantic): add mutation testing suite preventing silent degradation across 4 operators"
```

---

### Task 5: Full Release Verification & Documentation Sync

**Files:**
- Modify: `AGENTS.md`
- Modify: `.agents/rules/semantic-resolution-guardrails.md`

**Interfaces:**
- Consumes: All updated tests, engines, benchmarks, and mutation suites
- Produces: Clean CI gate certification and updated agent instructions documenting the hold-out benchmark, mutation invariants, and non-LAC country diagnostic rules.

- [ ] **Step 1: Update documentation and guardrails**

1. In `.agents/rules/semantic-resolution-guardrails.md`:
   - Document Invariant 12: *Preservación de Modificadores de Medida y Denominadores:* Prohibido responder a una consulta con especificador de medida (e.g. `per cápita`, `tasa`, `CO2` vs `GEI`, `bruto` vs `neto`) con el indicador agregado correspondiente si no cuenta con dicha dimensión o unidad.
   - Document Invariant 13: *Diagnósticos de Abstención Geográfica No Enmascarada:* Consultas sobre países fuera de América Latina y el Caribe deben abstenerse explícitamente con `UNSUPPORTED_COUNTRY_NON_LAC_<ISO>` y advertencia geográfica, sin enmascararse como `LOW_CONCEPTUAL_RELEVANCE`.
2. In `AGENTS.md`:
   - Update verification commands to include `test_independent_holdout_benchmark_50.py` and `test_semantic_mutations.py` (390 total benchmark queries certified: 200 canonical + 40 adversarial + 100 catalog scale + 50 hold-out).

- [ ] **Step 2: Run full quality and release gate verification**

Run:
```bash
uv run ruff check .
uv run mypy src/unofficial_cepalstat_mcp/
uv build
uv run pytest -m "not integration" -q
```
Expected:
- `All checks passed!`
- `Success: no issues found in 34 source files`
- `Successfully built dist/...`
- `543+ passed, 3 deselected, 0 failed`

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md .agents/rules/semantic-resolution-guardrails.md
git commit -m "docs(governance): record measure modifier guardrails, mutation invariants and holdout benchmark in AGENTS.md"
```
