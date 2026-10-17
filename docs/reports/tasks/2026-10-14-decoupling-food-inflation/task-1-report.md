# Task 1 Report: Dependencies & Data Models

## Summary
- Added `statsmodels>=0.14.0` and `plotly>=5.20.0` into `pyproject.toml` dependencies.
- Synced dependencies using `uv sync --extra dev` (updating `uv.lock`).
- Extended `CountryPeriodMetric` model in `src/statscepal/analysis/models.py` with:
  - `food_inflation_mean_pct: float | None = None`
  - `food_wage_gap_pct: float | None = None`
- Implemented `RegressionModelSummary` model in `src/statscepal/analysis/models.py` with regression diagnostics (`r_squared`, `r_squared_adj`, `coefficients`, `p_values`, `std_errors`, `confidence_intervals`, `n_obs`, `f_pvalue`).
- Exported `RegressionModelSummary` from `src/statscepal/analysis/__init__.py`.
- Followed TDD:
  1. RED: Authored unit tests in `tests/test_analysis_models.py` and captured collection failure (`ImportError: cannot import name 'RegressionModelSummary' from 'statscepal.analysis'`).
  2. Implemented dependencies and models.
  3. GREEN: Verified `test_analysis_models.py` (5/5 passed).
  4. Verified entire non-integration test suite (116 passed, 2 deselected).
- Committed changes cleanly under `feat(analysis): add statsmodels dependency and econometric regression data models`.

## Commit
- `7148988f01e0ae4e84658e142831e89e5c1d7e40`: `feat(analysis): add statsmodels dependency and econometric regression data models`

## Test Results
- `tests/test_analysis_models.py`: 5 passed in 2.05s
- Full suite (`pytest -m "not integration"`): 116 passed, 2 deselected in 12.91s
