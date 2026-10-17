# Task 2: Econometric Estimation Engine with `statsmodels` (`econometrics.py`)

## Objective
Implement `EconometricEstimator` in `src/statscepal/analysis/econometrics.py` utilizing `statsmodels.api.OLS` to perform multivariate regression analysis on growth, poverty, real wages, and food inflation, returning structured `RegressionModelSummary` objects.

## Files
- Create: `src/statscepal/analysis/econometrics.py`
- Modify: `src/statscepal/analysis/__init__.py`
- Create: `tests/test_analysis_econometrics.py`

## Mathematical Specification
Model specification:
$$\Delta \text{Pobreza}_{i,t} = \beta_0 + \beta_1 \cdot \text{PIB}_{i,t} + \beta_2 \cdot \Delta \text{Salario}_{i,t} + \beta_3 \cdot \text{InflAlimentos}_{i,t} + \epsilon_{i,t}$$

1. **Input**: `dataset: DecouplingDataset`.
2. **Data extraction**:
   - Construct pandas DataFrame from `dataset.records`.
   - Filter rows where `poverty_total_change_pp` is not null.
   - Independent variables:
     - `gdp_pc_growth_mean`
     - `real_min_wage_change_pct`
     - `food_inflation_mean_pct`
   - Handle missing values gracefully (drop rows with missing predictors or impute neutral 0.0 for wage/food inflation).
   - If usable rows $N < 4$, return minimal `RegressionModelSummary` with $N$ rows and default zero metrics.
3. **Estimation**:
   - Use `statsmodels.api.add_constant(X)`.
   - Fit `results = statsmodels.api.OLS(y, X_const).fit()`.
4. **Output**:
   - Return `RegressionModelSummary`:
     - `r_squared`: float
     - `r_squared_adj`: float
     - `coefficients`: dict of param names to rounded floats (4 decimals)
     - `p_values`: dict of param names to p-values (4 decimals)
     - `std_errors`: dict of param names to standard errors (4 decimals)
     - `confidence_intervals`: dict of param names to `(lower, upper)` (4 decimals)
     - `n_obs`: int
     - `f_pvalue`: float

## TDD Instructions
1. Write tests in `tests/test_analysis_econometrics.py`:
   - Test normal dataset with synthetic data: check $R^2 \ge 0$, coefficients dictionary keys, valid p-values.
   - Test small dataset ($N < 4$): verify graceful handling without crash.
   - Test missing values handling.
2. Run `uv run pytest tests/test_analysis_econometrics.py` to confirm failure (RED).
3. Implement `src/statscepal/analysis/econometrics.py`.
4. Export `EconometricEstimator` in `src/statscepal/analysis/__init__.py`.
5. Run `uv run pytest tests/test_analysis_econometrics.py` to confirm pass (GREEN).
6. Run full non-integration test suite: `uv run pytest -m "not integration"`.
7. Commit: `git add src/statscepal/analysis/econometrics.py src/statscepal/analysis/__init__.py tests/test_analysis_econometrics.py && git commit -m "feat(analysis): implement EconometricEstimator using statsmodels OLS"`.
8. Write report to `.superpowers/sdd/2026-10-14-decoupling-food-inflation-interactive-viz/task-2-report.md`.
9. Return status contract.
