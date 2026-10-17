# Task 2 Brief: Robust Country Column Priority, UN Formal Country Name Matching & Decade Period Parsing in `SemanticDataFetcher`

## Objective
Harden `SemanticDataFetcher` in `src/statscepal/semantic/fetcher.py` so that:
1. Country columns with human-readable names (such as `'Países_agregados regionales especiales VAR IPC'` in IPC indicators 2929/2484) are prioritized over code columns (`iso3`).
2. Country name filtering robustly matches UN formal country names that contain parenthetical qualifiers, such as `'Bolivia (Estado Plurinacional de)'` when querying for `'Bolivia'`, and cross-checks the country's `iso3` code against any `iso3`/`country_code` column in the DataFrame.
3. Demographic and census indicators that record time periods in a `'Década'` column (e.g., `'Década 2010'`, `'Década 2020'` in indicators 4968, 4969, 4992) are detected as temporal dimensions, and their numeric years are extracted via regex `(1\d{3}|20\d{2})`.
4. Add `'decada'`, `'década'`, `'total quintiles'`, `'total deciles'`, etc., to `_STRUCTURAL_AND_META_COLS` and `_AGGREGATE_MEMBER_PRIORITY` to prevent unconstrained dimension collapses from misidentifying decade or aggregate columns.

## Inputs & Context
- Base commit: `591da039b2b545f4ce7f10b7ee0420b721e42f61`
- Plan reference: `docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md` (Task 2)
- Target files:
  - `src/statscepal/semantic/fetcher.py`
  - `tests/test_semantic_fetcher.py`

## Instructions

### 1. TDD Red Test
Add the following two unit tests to `tests/test_semantic_fetcher.py`:
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
Run `uv run pytest tests/test_semantic_fetcher.py -k "test_fetcher_matches_un_formal_country_names or test_fetcher_parses_decada_column" -v` and confirm failure.

### 2. Implementation in `src/statscepal/semantic/fetcher.py`
1. Update `_STRUCTURAL_AND_META_COLS`: add `"decada"`, `"década"`, `"países_agregados regionales especiales var ipc"`, `"paises_agregados regionales especiales var ipc"`.
2. Update `_AGGREGATE_MEMBER_PRIORITY`: add `"total quintiles"`, `"total deciles"`.
3. Add helper method:
```python
def _extract_numeric_years(series: pd.Series) -> pd.Series:
    """Convert a year or decade Series (e.g., 2020 or 'Década 2010') into numeric years."""
    num = pd.to_numeric(series, errors="coerce")
    if num.notna().any():
        return num
    extracted = series.astype(str).str.extract(r"(1\d{3}|20\d{2})", expand=False)
    return pd.to_numeric(extracted, errors="coerce")
```
4. In `fetch_resolved_data`:
   - Prioritize human-readable country columns before code columns.
   - Robustly match target country names (including `startswith(norm_target_name + " (")`) and cross-check `iso3`/`country_code` columns against target codes.
   - Recognize `"decada"` in temporal column identification: `("year", "anio", "ano", "anios", "anos", "period", "periodo", "decada")`.
   - Use `_extract_numeric_years` when converting `year_col` to numbers.

### 3. TDD Green & Regression Verification
- Run: `uv run pytest tests/test_semantic_fetcher.py -v`
- Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`
- Run: `uv run pytest -m "not integration"`

### 4. Git Commit
```bash
git add src/statscepal/semantic/fetcher.py tests/test_semantic_fetcher.py
git commit -m "feat(semantic): prioritize human country columns, match UN formal names, and parse decade columns"
```

### 5. Report
Write `task-2-report.md` in `C:\papx\statscepal\.superpowers\sdd\2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan\task-2-report.md`.
