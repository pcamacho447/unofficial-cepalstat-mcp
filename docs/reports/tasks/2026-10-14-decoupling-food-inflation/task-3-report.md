# Task 3 Report: DecouplingAnalyzer Service with Indicator 2929 (`service.py`)

## Summary
- Defined `FOOD_INFLATION_MEMBER_MAP` for CEPALSTAT Indicator 2929 (Dimension 79565) covering the 6 target economies:
  - Argentina: 79568
  - Chile: 79578
  - Colombia: 79579
  - México / Mexico: 79599
  - Perú / Peru: 79604
  - Uruguay: 79612
- Implemented `compute_food_wage_gap(wage_change_pct, food_inflation_pct) -> float | None` in `src/statscepal/analysis/metrics.py` calculating $\Delta\% \text{Salario} - \text{InflAlimentos}$, rounded to 2 decimal places with safe None handling.
- Integrated Indicator 2929 querying and processing into `DecouplingAnalyzer.analyze_countries`:
  - Fetches 2929 via `self.extractor.get_dataframe(2929, members=unique_food_member_ids, decode_labels=True)`.
  - Dynamically detects the food country dimension column (`Países_agregados regionales especiales VAR IPC` or country column) and year column.
  - Normalizes country labels with `_normalize()`.
  - Calculates `food_inflation_mean_pct` over the period years.
  - Calculates `food_wage_gap_pct` via `compute_food_wage_gap`.
  - Populates both fields on each `CountryPeriodMetric`.
  - Caches the analyzed dataset in `self._last_dataset`.
- Added convenience method `DecouplingAnalyzer.run_econometric_regression(dataset=None, impute_missing=False) -> RegressionModelSummary` delegating to `EconometricEstimator.fit_poverty_growth_model`.
- Exported `compute_food_wage_gap`, `FOOD_INFLATION_MEMBER_MAP`, and `COUNTRY_MEMBER_MAP` in `src/statscepal/analysis/__init__.py`.
- Followed strict TDD discipline:
  1. RED: Authored unit tests in `tests/test_analysis_metrics.py` and `tests/test_analysis_service.py` and captured failure output (`ImportError: cannot import name 'compute_food_wage_gap'`).
  2. GREEN: Implemented logic across `metrics.py`, `service.py`, and `__init__.py`.
  3. Verified targeted test suites: 17/17 passed in 3.09s.
  4. Verified full non-integration test suite: 126 passed, 2 deselected in 17.18s.
- Cleanly committed all modified files.

## Commit
- `39d6377c65e9d04a3697f2d503ba6a4ee0478e02`: `feat(analysis): integrate food inflation Indicator 2929 into DecouplingAnalyzer`

## Test Results
- `tests/test_analysis_metrics.py` & `tests/test_analysis_service.py`: 17 passed in 3.09s
- Full non-integration suite (`pytest -m "not integration"`): 126 passed, 2 deselected in 17.18s
