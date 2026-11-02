# Phase 4: Semantic Ergonomics, Typo Suggestions & Tier-2 Re-ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean tabular CLI presentation, provide informative typo suggestions ("Did you mean?") on abstentions without auto-substitution, and re-rank Tier-2 candidates to favor core headline indicators over verbose peripheral series.

**Architecture:** Purge numeric foreign keys (`notes_ids`) from CLI observation rows and prioritize textual notes. Introduce bounded Damerau-Levenshtein vocabulary suggestions in `Thesaurus` / `SemanticResolutionEngine` to append conversational hints on `LOW_CONCEPTUAL_RELEVANCE` without violating `0.00% FSR`. Add length normalization damping and low `order_num` headline boosts in `SemanticRegistry.search_candidates` to prevent verbose niche titles from dominating headline statistics.

**Tech Stack:** Python >=3.10, `uv`, `pytest`, `pydantic` v2, `sqlite3`, `mypy`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-11-02-semantic-ergonomics-and-ranking-spec.md`

## Global Constraints

- Import always from `unofficial_cepalstat_mcp` (never `from statscepal`).
- Always run `uv run pytest -m "not integration"`; zero live network requests in unit and benchmark suites.
- Preserve strictly **0.00% False Substitution Rate (FSR)**: typo suggestions must be purely conversational and never auto-resolve into a candidate.
- Maintain local semantic resolution latency at **`p50 < 0.5 ms` and `p95 < 2.0 ms`**.
- Pass `uv run mypy src/unofficial_cepalstat_mcp/`, `uv run ruff check .`, and `uv build` cleanly with 0 errors.

## Review Focus

1. **Foreign key leakage in CLI:** Purely numeric `notes_ids` (e.g. `12080`) must never appear in CLI observation tables next to measurement units.
2. **False substitution via typo auto-correction:** Typos like `"pobresa"` must remain `ABSTAINED` with `LOW_CONCEPTUAL_RELEVANCE` while adding `¿Quisiste decir 'pobreza'?` in `conversational_hint`; under no circumstances should the engine guess or auto-resolve to avoid FSR violations.
3. **Typo computational overhead:** Levenshtein checks must only execute on unconsumed tokens when query resolution has failed, never adding overhead to successful Tier-1 resolutions.
4. **Headline vs. peripheral inversion on open queries:** Open queries (e.g. `"empleo en Ecuador 2021"`) must rank primary series (e.g. `127`, `2321`, `5097`) above specialized subpopulation series (e.g. `5531`).
5. **No regression across 390 certified benchmarks:** The existing 200 canonical, 40 adversarial, 100 catalog scale, 50 hold-out benchmarks, and 8 mutation tests must pass at 100%.

---

## File Structure

- **Modify:** `src/unofficial_cepalstat_mcp/semantic/fetcher.py:1095-1115, 1235-1250` — Prioritize text notes columns (`"notes"`, `"notas"`) over numeric IDs (`"notes_ids"`, `"notes_id"`), discarding purely numeric values from `notes`.
- **Modify:** `src/unofficial_cepalstat_mcp/cli.py:830-895` — Filter out purely numeric notes strings from CLI table rendering.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/thesaurus.py:120-170, 500-560` — Add `suggest_correction(token: str, max_distance: int = 2) -> str | None` using bounded edit distance against canonical terms and synonyms.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/engine.py:345-365` — On `LOW_CONCEPTUAL_RELEVANCE` / unrecognized root concept, check unconsumed tokens for typo suggestions and append hint.
- **Modify:** `src/unofficial_cepalstat_mcp/semantic/registry.py:1710-1795` — Add document length damping and headline indicator priority (`order_num <= 20` or canonical default) in `search_candidates`.
- **Create:** `tests/test_cli_fetch_rendering.py` — Test CLI tabular output formatting and absence of raw `notes_ids`.
- **Create:** `tests/test_semantic_typo_suggestions.py` — Test typo suggestion hints without false substitution.
- **Create:** `tests/test_semantic_tier2_ranking.py` — Test that headline indicators outrank peripheral indicators on open queries.

---

### Task 1: CLI Fetch Table Hygiene & Foreign Key Suppression (Bug 7)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/fetcher.py:1095-1115, 1235-1250`
- Modify: `src/unofficial_cepalstat_mcp/cli.py:830-895`
- Create: `tests/test_cli_fetch_rendering.py`

**Interfaces:**
- Consumes: `SemanticDataFetcher`, CLI formatting functions
- Produces:
  - `fetcher.py` checks `("notes", "notas", "nota")` first, and ignores purely digit strings from `notes_ids` when generating `item["notes"]`.
  - `cli.py` prints clean table columns: `Year | Value | Unit | [Anchor notes]`, omitting stray numbers.

- [ ] **Step 1: Write failing tests for CLI fetch rendering and foreign key suppression**

Create `tests/test_cli_fetch_rendering.py`:
```python
from unittest.mock import MagicMock
import pandas as pd
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.fetcher import SemanticDataFetcher
from unofficial_cepalstat_mcp.dimensions import Dimension, Member


def test_fetcher_ignores_purely_numeric_notes_ids(mocker) -> None:
    dims = [
        Dimension(id=208, name="País__ESTANDAR", members=[Member(id=210, name="Perú")]),
        Dimension(id=29117, name="Años__ESTANDAR", members=[Member(id=29190, name="2022")]),
    ]
    # Simulate API returning notes_ids as numeric 12080 without text notes
    df = pd.DataFrame([{
        "País__ESTANDAR": "Perú",
        "iso3": "PER",
        "Años__ESTANDAR": 2022,
        "value": 236311.0,
        "notes_ids": 12080,
    }])
    extractor = mocker.Mock()
    extractor.dimension_manager.get_dimensions.return_value = dims
    extractor.get_dataframe.return_value = df

    engine = SemanticResolutionEngine()
    resp = engine.resolve("pib del peru 2022")
    fetcher = SemanticDataFetcher(extractor=extractor)
    result = fetcher.fetch_resolved_data(resp)

    assert result["observation_exists"] is True
    # The note should be empty, NOT '12080'
    assert result["notes"] == ""
    for item in result["series"]:
        assert item["notes"] == ""
        assert "12080" not in str(item["notes"])


def test_cli_renders_clean_units_without_stray_numeric_ids(capsys, monkeypatch) -> None:
    from unofficial_cepalstat_mcp.cli import main
    # Mock resolve and fetch to return series with numeric notes_ids
    sample_res = {
        "observation_exists": True,
        "series": [
            {"year": 2020, "value": 202645, "unit": "Millones de USD constantes", "notes": "12080"},
            {"year": 2021, "value": 229834, "unit": "Millones de USD constantes", "notes": ""},
        ],
        "status": "RESOLVED",
    }
    # Invoke CLI logic or format function to verify stray number is not printed
    # In cli.py, test the formatted line
    from io import StringIO
    from unittest.mock import patch
    import sys

    with patch("unofficial_cepalstat_mcp.cli.SemanticDataFetcher") as MockFetcher, \
         patch("unofficial_cepalstat_mcp.cli.SemanticResolutionEngine") as MockEngine:
        mock_engine_inst = MockEngine.return_value
        mock_resp = MagicMock()
        mock_resp.status.value = "RESOLVED"
        mock_resp.selected_candidate.indicator_id = 2204
        mock_resp.selected_candidate.name = "PIB constante"
        mock_resp.selected_candidate.measure_type = "VOLUMEN_REAL"
        mock_resp.selected_candidate.unit = "Millones de USD constantes"
        mock_resp.selected_candidate.relevance_score = 1.0
        mock_resp.temporal_info = None
        mock_resp.applied_filters.country_name = "Perú"
        mock_resp.applied_filters.country_code = "PER"
        mock_resp.applied_filters.country_names = ["Perú"]
        mock_resp.applied_filters.year = 2020
        mock_resp.applied_filters.years = [2020, 2021]
        mock_resp.applied_filters.time_mode.value = "RANGE"
        mock_resp.applied_filters.facets = {}
        mock_resp.applied_filters.dimensions = []
        mock_resp.empirical_data = sample_res
        mock_engine_inst.resolve.return_value = mock_resp

        mock_fetcher_inst = MockFetcher.return_value
        mock_fetcher_inst.fetch_resolved_data.return_value = sample_res

        sys.argv = ["unofficial-cepalstat-mcp", "semantic", "resolve", "pib del peru entre 2020 y 2021", "--fetch"]
        main()
        captured = capsys.readouterr()
        # Verify 12080 is suppressed from CLI table output
        assert "12080" not in captured.out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_fetch_rendering.py -v`
Expected: FAIL (`assert result["notes"] == ""` fails because `result["notes"] == "12080"`).

- [ ] **Step 3: Implement foreign key suppression in `fetcher.py` and `cli.py`**

1. In `src/unofficial_cepalstat_mcp/semantic/fetcher.py:1099-1104, 1237-1242`:
   - Prioritize text note columns first:
     ```python
     row_notes = ""
     for n_col in ("notes", "notas", "nota"):
         if n_col in row and not pd.isna(row[n_col]):
             val_str = str(row[n_col]).strip()
             if val_str and not val_str.isdigit():
                 row_notes = val_str
                 break
     ```
   - Ignore purely digit strings so internal database foreign keys (`notes_ids=12080`) are never surfaced as textual notes.
2. In `src/unofficial_cepalstat_mcp/cli.py:830-895`:
   - When printing `notes_val`, verify `if notes_val and not notes_val.isdigit():`.
   - If `notes_val` is purely digits, do not concatenate it to `desc_str`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli_fetch_rendering.py tests/test_semantic_fetcher.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/fetcher.py src/unofficial_cepalstat_mcp/cli.py tests/test_cli_fetch_rendering.py
git commit -m "fix(cli): suppress raw numeric foreign keys from notes in tabular fetch rendering"
```

---

### Task 2: Typo Suggestions ("Did You Mean?") without Silent Substitution (Point 5)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/thesaurus.py:120-170, 500-560`
- Modify: `src/unofficial_cepalstat_mcp/semantic/engine.py:345-365`
- Create: `tests/test_semantic_typo_suggestions.py`

**Interfaces:**
- Consumes: `Thesaurus`, `Thesaurus.synsets`
- Produces:
  - `Thesaurus.suggest_correction(self, token: str, max_distance: int = 2) -> str | None`
  - In `engine.py`, when resolution abstains with `LOW_CONCEPTUAL_RELEVANCE`:
    If any unconsumed token or query word has a suggestion $S$, append `¿Quisiste decir '{S}'?` to `conversational_hint`.
  - Resolution status remains strictly `ResolutionStatus.ABSTAINED` (`0.00% FSR`).

- [ ] **Step 1: Write failing tests for typo suggestions**

Create `tests/test_semantic_typo_suggestions.py`:
```python
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus
from unofficial_cepalstat_mcp.semantic.thesaurus import get_default_thesaurus


def test_thesaurus_suggests_close_matches() -> None:
    thesaurus = get_default_thesaurus()
    assert thesaurus.suggest_correction("pobresa") == "pobreza"
    assert thesaurus.suggest_correction("desocupasion") == "desocupacion"
    assert thesaurus.suggest_correction("inflasion") in ("inflacion", "inflación")
    assert thesaurus.suggest_correction("xyzqwk") is None


def test_engine_abstains_with_did_you_mean_hint_on_typos() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    cases = [
        ("pobresa en guatemala 2020", "pobreza"),
        ("desocupasion en peru 2021", "desocupacion"),
        ("inflasion en colombia 2022", "inflacion"),
    ]
    for query, expected_suggestion in cases:
        resp = engine.resolve(query)
        # Invariant: Must remain ABSTAINED (0.00% FSR)
        assert resp.status == ResolutionStatus.ABSTAINED
        assert resp.abstention_reason == "LOW_CONCEPTUAL_RELEVANCE"
        assert resp.selected_candidate is None
        # Must offer helpful suggestion
        assert "¿quisiste decir" in (resp.conversational_hint or "").lower()
        assert expected_suggestion in (resp.conversational_hint or "").lower()


def test_engine_does_not_suggest_for_hopeless_gibberish() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    resp = engine.resolve("blarghxyz 2022")
    assert resp.status == ResolutionStatus.ABSTAINED
    assert "¿quisiste decir" not in (resp.conversational_hint or "").lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_typo_suggestions.py -v`
Expected: FAIL (`AttributeError: 'Thesaurus' object has no attribute 'suggest_correction'`).

- [ ] **Step 3: Implement bounded Damerau-Levenshtein suggestions in `Thesaurus` and `engine.py`**

1. In `src/unofficial_cepalstat_mcp/semantic/thesaurus.py`:
   - Implement an efficient bounded edit distance function:
     ```python
     def _edit_distance(s1: str, s2: str, max_dist: int = 2) -> int:
         if abs(len(s1) - len(s2)) > max_dist:
             return max_dist + 1
         # Standard DP with early row termination
         ...
     ```
   - In `Thesaurus`, pre-compile unique vocabulary words (length $\ge 4$) from canonical terms and synonyms.
   - Implement `suggest_correction(self, token: str, max_distance: int = 2) -> str | None`:
     Return the closest vocabulary term with distance $\le \min(\text{max\_distance}, \text{len}(token)//3)$.
2. In `src/unofficial_cepalstat_mcp/semantic/engine.py:345-365`:
   - When `not intent.root_concept` and about to return `LOW_CONCEPTUAL_RELEVANCE`:
     Inspect `intent.unconsumed_tokens` and tokens in `intent.concept_tokens`.
     If a suggestion is found:
     ```python
     conversational_hint = (
         f"No se identificó un fenómeno socioeconómico cubierto por el catálogo de CEPALSTAT. "
         f"¿Quisiste decir '{suggestion}'?"
     )
     ```
     Preserve `status = ResolutionStatus.ABSTAINED` and `abstention_reason = "LOW_CONCEPTUAL_RELEVANCE"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_semantic_typo_suggestions.py tests/test_adversarial_benchmark_40.py -v`
Expected: PASS (`0.00% FSR` preserved).

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/thesaurus.py src/unofficial_cepalstat_mcp/semantic/engine.py tests/test_semantic_typo_suggestions.py
git commit -m "feat(semantic): add bounded typo suggestion hints on abstained queries without auto-substitution"
```

---

### Task 3: Tier-2 Re-ranking: Length Damping & Headline Prioritization (Point 6)

**Files:**
- Modify: `src/unofficial_cepalstat_mcp/semantic/registry.py:1710-1795`
- Create: `tests/test_semantic_tier2_ranking.py`

**Interfaces:**
- Consumes: `SemanticRegistry.search_candidates`, `CatalogStore.get_master_indicator`, `OFFICIAL_25_CANONICAL_DEFAULTS`, `LEGACY_50_CANONICAL_DEFAULTS`
- Produces:
  - Document length normalization (BM25-style damping) on title matches.
  - Headline indicator priority: indicators with `order_num <= 20` or presence in canonical defaults receive a relevance boost ($1.3\times$).
  - Verbose specialized titles (> 90 chars with subpopulation clauses) receive length penalty when query is broad.
  - Open query `"como le fue al empleo en ecuador 2021"` ranks primary employment/unemployment indicators (`127`, `2321`, `2329`, `5097`) above `5531`.

- [ ] **Step 1: Write failing tests for Tier-2 headline re-ranking**

Create `tests/test_semantic_tier2_ranking.py`:
```python
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus


def test_open_employment_query_prioritizes_headline_over_niche_care_series() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    resp = engine.resolve("como le fue al empleo en ecuador 2021")
    # Must resolve or propose alternatives featuring core employment/unemployment, NOT niche 5531
    assert resp.status in (ResolutionStatus.RESOLVED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    top_id = resp.selected_candidate.indicator_id if resp.selected_candidate else None
    # 5531 is "Población fuera del mercado laboral con dedicación exclusiva al trabajo doméstico..."
    assert top_id != 5531, f"Peripheral niche indicator 5531 was ranked top for generic employment query: {resp.selected_candidate}"

    if resp.status == ResolutionStatus.ALTERNATIVE_PROPOSED:
        alt_ids = [alt.indicator_id for alt in resp.alternatives]
        # Core employment indicators (127, 2321, 2329, 4207, 5095, 5097) should be present
        headline_ids = {127, 2321, 2329, 3889, 4207, 5095, 5097}
        assert (top_id in headline_ids) or any(aid in headline_ids for aid in alt_ids)


def test_headline_indicators_receive_ranking_boost() -> None:
    from unofficial_cepalstat_mcp.catalog.store import CatalogStore
    from unofficial_cepalstat_mcp.semantic.registry import SemanticRegistry

    store = CatalogStore()
    registry = SemanticRegistry(store=store)
    candidates = registry.search_candidates(["desempleo"], top_k=5)
    top_ids = [c[0] for c in candidates]
    # Primary unemployment indicators must be in top 3
    assert any(h_id in top_ids[:3] for h_id in (127, 2329, 3889, 5097))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_semantic_tier2_ranking.py -v`
Expected: FAIL (`assert top_id != 5531` fails because `top_id == 5531`).

- [ ] **Step 3: Implement length damping and headline indicator prioritization in `registry.py`**

In `src/unofficial_cepalstat_mcp/semantic/registry.py:1755-1795`:
1. In `_build_in_memory_index()`:
   - Calculate and store `_title_lengths: dict[int, int]` (number of words in normalized indicator name).
   - Pre-compile `_headline_indicators: set[int]`: union of all canonical default IDs (`OFFICIAL_25_CANONICAL_DEFAULTS`, `LEGACY_50_CANONICAL_DEFAULTS`) and indicators with `order_num <= 20`.
2. In `search_candidates()`:
   - For each candidate `ind_id`:
     Apply document length normalization damping:
     $$\text{damping} = \frac{1.0}{1.0 + 0.3 \cdot \max(0, \text{word\_count} - 6) / 6.0}$$
     This prevents long compound titles (e.g. 25 words with multiple clauses) from accumulating disproportionate synonym weight on single-token or broad queries.
   - For headline indicators (`ind_id in self._headline_indicators`):
     Apply a headline boost ($1.35\times$).
   - For peripheral indicators (`order_num >= 100` and `word_count > 15`):
     Apply a peripheral discount ($0.85\times$).
3. Multiply candidate scores by the combined factor before heap selection.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_semantic_tier2_ranking.py tests/test_catalog_scale_benchmark_100.py tests/test_independent_holdout_benchmark_50.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/unofficial_cepalstat_mcp/semantic/registry.py tests/test_semantic_tier2_ranking.py
git commit -m "feat(semantic): re-rank Tier-2 candidates with length damping and headline indicator boost"
```

---

### Task 4: Full Quality Gate, Benchmarks & Documentation Sync

**Files:**
- Modify: `AGENTS.md`
- Run: Full test suite, linters, and build

**Interfaces:**
- Consumes: All 3 completed tasks
- Produces: 100% clean verification across all 554+ tests, 0 mypy errors, 0 ruff errors.

- [ ] **Step 1: Run full release verification suite**

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
- `554+ passed, 3 deselected, 0 failed`

- [ ] **Step 2: Commit any remaining doc updates**

```bash
git add AGENTS.md
git commit -m "docs(governance): record Phase 4 semantic ergonomics and re-ranking achievements"
```
