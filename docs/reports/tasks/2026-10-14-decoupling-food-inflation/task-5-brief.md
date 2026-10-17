# Task 5: CLI Subcommand Integration (`cli.py`)

## Objective
Extend `statscepal analyze desacople` in `src/statscepal/cli.py` to display the new Food Inflation and Purchasing Power Gap columns, and add an `--econometrics` flag to compute and print the `statsmodels` OLS regression summary table directly in the terminal.

## Files
- Modify: `src/statscepal/cli.py`
- Modify: `tests/test_cli_analyze.py`

## Specifications
1. **New Table Columns**:
   In the results DataFrame printed to stdout:
   - `País`
   - `Periodo`
   - `Δ PIB pc (%)`
   - `Δ Pob. Tot (pp)`
   - `Δ Pob. Ext (pp)`
   - `Δ Sal. Real (%)`
   - `Infl. Alim (%)`: `r.food_inflation_mean_pct`
   - `Brecha Sal/Alim (%)`: `r.food_wage_gap_pct`
   - `Δ Gini`
   - `Elasticidad`
   - `Cuadrante`
2. **`--econometrics` Flag**:
   - Add argument to `desacople_parser`:
     ```python
     desacople_parser.add_argument(
         "--econometrics",
         action="store_true",
         help="Run and display OLS multivariate regression summary",
     )
     ```
   - When present:
     - Run `summary = analyzer.run_econometric_regression(dataset)`
     - Print formatted OLS summary block:
       ```
       ======================================================================
       CEPALSTAT ECONOMETRIC REGRESSION SUMMARY (OLS)
       Dep. Variable: Δ Pobreza Total (pp) | N = {summary.n_obs} | R² = {summary.r_squared} (Adj. R² = {summary.r_squared_adj})
       F-statistic p-value: {summary.f_pvalue}
       ----------------------------------------------------------------------
       Variable              Coef.      Std.Err.   p-value    [95% Conf. Interval]
       ----------------------------------------------------------------------
       ...
       ======================================================================
       ```
3. **CSV Export**:
   - `df_table.to_csv(parsed.output, index=False)` naturally includes the new columns.

## TDD Instructions
1. Update `tests/test_cli_analyze.py`:
   - Test that default table includes `Infl. Alim (%)` and `Brecha Sal/Alim (%)`.
   - Test `--econometrics` flag triggers `run_econometric_regression` and prints regression summary block with $R^2$ and coefficients.
2. Run `uv run pytest tests/test_cli_analyze.py` to confirm failure (RED).
3. Implement in `src/statscepal/cli.py`.
4. Run `uv run pytest tests/test_cli_analyze.py` to confirm pass (GREEN).
5. Run full non-integration test suite: `uv run pytest -m "not integration"`.
6. Commit: `git add src/statscepal/cli.py tests/test_cli_analyze.py && git commit -m "feat(cli): add food inflation columns and econometrics flag to analyze desacople"`.
7. Write report to `.superpowers/sdd/2026-10-14-decoupling-food-inflation-interactive-viz/task-5-report.md`.
8. Return status contract.
