# Task 5 Report: CLI Subcommand Integration (`cli.py`)

## Summary
- Updated `src/statscepal/cli.py`:
  - Added `--econometrics` flag (`action="store_true"`) to `desacople_parser` subcommand (`statscepal analyze desacople`).
  - Added `Infl. Alim (%)` (`r.food_inflation_mean_pct`) and `Brecha Sal/Alim (%)` (`r.food_wage_gap_pct`) to the console table output and CSV export dictionary in `rows`.
  - Implemented formatted econometric regression summary output when `--econometrics` is passed:
    - Runs `summary = analyzer.run_econometric_regression(dataset)`
    - Prints formatted OLS summary block including:
      - Header banner: `CEPALSTAT ECONOMETRIC REGRESSION SUMMARY (OLS)`
      - Dependent variable: `Dep. Variable: Δ Pobreza Total (pp)`
      - Sample size: `N = {summary.n_obs}`
      - Goodness of fit: `R² = {summary.r_squared} (Adj. R² = {summary.r_squared_adj})`
      - Model significance: `F-statistic p-value: {summary.f_pvalue}`
      - Column headers: `Variable`, `Coef.`, `Std.Err.`, `p-value`, `[95% Conf. Interval]`
      - Parameter estimates for each variable in `summary.coefficients`.
- Updated test suite in `tests/test_cli_analyze.py`:
  - `test_cli_analyze_desacople_help`: Verified `--econometrics` is exposed in CLI help.
  - `test_cli_analyze_desacople`: Verified `Infl. Alim (%)` and `Brecha Sal/Alim (%)` appear in table output.
  - `test_cli_analyze_desacople_output_csv`: Verified `Infl. Alim (%)` and `Brecha Sal/Alim (%)` appear in generated CSV file.
  - `test_cli_analyze_desacople_econometrics`: Verified `--econometrics` invokes `analyzer.run_econometric_regression` and prints the OLS regression summary block with $R^2$, Adj. $R^2$, N, F-stat, coefficients, p-values, SEs, and confidence intervals.
  - `test_cli_analyze_desacople_without_econometrics`: Verified `run_econometric_regression` is not called and the summary block is omitted when `--econometrics` is absent.
- Followed strict TDD discipline:
  1. RED: Authored tests in `tests/test_cli_analyze.py` and captured failure output (4 failed, 6 passed: missing flag and table columns).
  2. GREEN: Implemented changes in `src/statscepal/cli.py`, confirming `tests/test_cli_analyze.py` passing (10/10 passed in 6.44s).
  3. Verified full non-integration test suite: 130 passed, 2 deselected in 28.46s.
- Cleanly committed all modified files with no stray files.

## Commit
- `e7c895eb32940da49dbcafeaf7056d7d35867e18`: `feat(cli): add food inflation columns and econometrics flag to analyze desacople`

## Test Results
- `tests/test_cli_analyze.py`: 10 passed in 6.44s
- Full non-integration suite (`pytest -m "not integration"`): 130 passed, 2 deselected in 28.46s
