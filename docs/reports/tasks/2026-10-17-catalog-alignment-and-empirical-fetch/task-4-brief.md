# Task 4 Brief: End-to-End Certification of Multi-Country Inflation & Ethnic Population Queries

## Objective
Certify end-to-end the resolution and empirical fetch pipelines across the 3 motivating user queries, and annotate the mapped live API table ID in the CLI:
1. `"necesito los datos de la inflacion de alimentos de mexico, peru, argentina, chile, colombia y paraguay del año 2018 al 2023"` -> Resolves to `2929` (`Alimentos y bebidas`), strips synthetic member `79578` (preventing API Chile collision), matches all 6 countries, parses years 2018-2023.
2. `"necesito los datos de la inflacion de peru, argentina, chile, colombia y paraguay del año 2018 al 2023"` -> Resolves to `2928` (`IPC general`), dynamically maps to live API table `2484`, matches all 5 countries, parses years 2018-2023.
3. `"necesito datos etnicos de la poblacion peruana"` -> Resolves to `4968` (`Población Indígena y no indígena según área de residencia`), extracts country `PER` via demonym `'peruana'`, parses `'Década'` temporal column, collapses unconstrained dimension (`Area Geografica` -> `Total`), and extracts the breakdown `{"Indígena": ..., "No Indígena": ...}`.

And update `src/statscepal/cli.py` so that when `--fetch` runs, if `emp.get("empirical_indicator_id")` differs from `res.selected_candidate.indicator_id`, print:
`  CEPALSTAT API Table ID: {emp['empirical_indicator_id']}`

## Inputs & Context
- Base commit: `e539d289060ef9dec92a1b42653e8ee8ffae49a1`
- Plan reference: `docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md` (Task 4)
- Target files:
  - `tests/test_semantic_fetcher.py`
  - `src/statscepal/cli.py`

## Instructions

### 1. TDD Red Test in `tests/test_semantic_fetcher.py`
Add the following unit test to `tests/test_semantic_fetcher.py`:
```python
def test_end_to_end_ethnic_population_peru_fetch_with_decada_and_breakdown():
    """Verify 'necesito datos etnicos de la poblacion peruana' resolves to 4968 and fetches Indigenous vs No Indígena breakdown for latest decade."""
    import pandas as pd
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.fetcher import SemanticDataFetcher
    from statscepal.semantic.models import ResolutionStatus

    engine = SemanticResolutionEngine()
    res = engine.resolve("necesito datos etnicos de la poblacion peruana")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4968

    mock_df = pd.DataFrame([
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2010", "Area Geografica": "Total", "Condición Indígena": "Indígena", "value": 6383284.0, "notes_ids": "8651"},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2010", "Area Geografica": "Total", "Condición Indígena": "No Indígena", "value": 17437316.0, "notes_ids": "8651"},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2010", "Area Geografica": "Total", "Condición Indígena": "Total", "value": 23820599.0, "notes_ids": "8651"},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Década": "Década 2010", "Area Geografica": "Urbano", "Condición Indígena": "Indígena", "value": 4525633.0, "notes_ids": "8651"},
    ])

    fetcher = SemanticDataFetcher()
    fetcher._load_indicator_data = lambda ind_id, member_ids=None: mock_df

    payload = fetcher.fetch_resolved_data(res)
    assert payload["observation_exists"] is True
    series = payload.get("series", [])
    assert len(series) == 2
    by_dim = {r["dimension"]: r["value"] for r in series}
    assert by_dim == {"Indígena": 6383284.0, "No Indígena": 17437316.0}
```
Run `uv run pytest tests/test_semantic_fetcher.py -k test_end_to_end_ethnic_population_peru_fetch_with_decada_and_breakdown -v`.

### 2. Implementation in `src/statscepal/cli.py`
In `src/statscepal/cli.py`:
In the `if parsed.fetch:` block:
```python
                    emp = res.empirical_data or {}
                    if (
                        emp.get("empirical_indicator_id")
                        and res.selected_candidate
                        and emp.get("empirical_indicator_id") != res.selected_candidate.indicator_id
                    ):
                        print(f"CEPALSTAT API Table ID: {emp['empirical_indicator_id']}")
```

Also add a test in `tests/test_semantic_fetcher.py` verifying that CLI displays this annotation when `--fetch` maps an indicator.

### 3. Verification
- Run `uv run pytest tests/test_semantic_fetcher.py -v`
- Run `uv run pytest tests/test_semantic_benchmark_200.py -v`
- Run full non-integration suite: `uv run pytest -m "not integration"`

### 4. Git Commit
```bash
git add src/statscepal/cli.py tests/test_semantic_fetcher.py
git commit -m "feat(cli): display mapped CEPALSTAT API table ID and certify ethnic population fetch"
```

### 5. Report
Write `task-4-report.md` in `C:\papx\statscepal\.superpowers\sdd\2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan\task-4-report.md`.
