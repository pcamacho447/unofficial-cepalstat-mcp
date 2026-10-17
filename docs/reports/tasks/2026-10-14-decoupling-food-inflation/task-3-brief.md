# Task 3: DecouplingAnalyzer Service with Indicator 2929 (`service.py`)

## Objective
Update `DecouplingAnalyzer` in `src/statscepal/analysis/service.py` to query CEPALSTAT food inflation (Indicator 2929) using Dimension 79565 member IDs, compute food inflation means and purchasing power wage-food gaps, and expose a convenience method to run the econometric regression.

## Files
- Modify: `src/statscepal/analysis/service.py`
- Modify: `src/statscepal/analysis/metrics.py`
- Modify: `src/statscepal/analysis/__init__.py`
- Modify: `tests/test_analysis_service.py`

## Specifications
1. **`FOOD_INFLATION_MEMBER_MAP`**:
   ```python
   FOOD_INFLATION_MEMBER_MAP = {
       "argentina": 79568,
       "chile": 79578,
       "colombia": 79579,
       "méxico": 79599,
       "mexico": 79599,
       "perú": 79604,
       "peru": 79604,
       "uruguay": 79612,
   }
   ```
2. **Indicator 2929 Extraction & Alignment**:
   - Fetch via `self.extractor.get_dataframe(2929, members=food_member_ids, decode_labels=True)`
   - Filter by country using `_normalize(c)` on the country dimension column (matching `Países_agregados regionales especiales VAR IPC` or any column containing `País`/`Pais`).
   - Filter years between `start_year` and `end_year`.
   - Calculate `food_inflation_mean_pct = round(float(sub_food["value"].mean()), 2)` if data exists, else `None`.
   - Calculate `food_wage_gap_pct = compute_food_wage_gap(sal_chg, food_inflation_mean_pct)`.
   - Populate `food_inflation_mean_pct` and `food_wage_gap_pct` in `CountryPeriodMetric`.
3. **`run_econometric_regression(dataset: DecouplingDataset | None = None) -> RegressionModelSummary`**:
   - Helper on `DecouplingAnalyzer` that delegates to `EconometricEstimator.fit_poverty_growth_model(dataset)`.

## TDD Instructions
1. Write unit tests in `tests/test_analysis_service.py` mocking indicator 2929 and verifying food inflation and wage gap attributes on records.
2. Run `uv run pytest tests/test_analysis_service.py` to confirm failure (RED).
3. Implement in `src/statscepal/analysis/service.py`.
4. Run `uv run pytest tests/test_analysis_service.py` to confirm pass (GREEN).
5. Run full non-integration test suite: `uv run pytest -m "not integration"`.
6. Commit: `git add src/statscepal/analysis/service.py src/statscepal/analysis/metrics.py src/statscepal/analysis/__init__.py tests/test_analysis_service.py && git commit -m "feat(analysis): integrate food inflation Indicator 2929 into DecouplingAnalyzer"`.
7. Write report to `.superpowers/sdd/2026-10-14-decoupling-food-inflation-interactive-viz/task-3-report.md`.
8. Return status contract.
