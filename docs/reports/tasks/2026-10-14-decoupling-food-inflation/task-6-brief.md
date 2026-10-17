# Task 6: Interactive Plotly & Econometric Jupyter Notebook (`01_desacople_crecimiento_bienestar.ipynb`)

## Objective
Upgrade `notebooks/01_desacople_crecimiento_bienestar.ipynb` to incorporate food inflation metrics, interactive Plotly visualizations with detailed hover data and trajectory lines, and an econometric OLS estimation cell with formal $R^2$ and p-value statistical diagnostics.

## Files
- Modify: `notebooks/01_desacople_crecimiento_bienestar.ipynb`
- Modify: `tests/test_notebook_syntax.py`

## Requirements
1. **Interactive Visualization (`plotly.express`)**:
   - 2x2 Socioeconomic Quadrant Scatter Plot using `plotly.express.scatter`:
     - X-axis: `Δ PIB pc (%)`
     - Y-axis: `Δ Pob. Tot (pp)`
     - Hover data: `País`, `Periodo`, `Δ PIB pc (%)`, `Δ Pob. Tot (pp)`, `Δ Sal. Real (%)`, `Infl. Alim (%)`, `Brecha Sal/Alim (%)`, `Cuadrante`.
     - Color: `Cuadrante`
     - Size: Absolute value of `Brecha Sal/Alim (%)` or `Δ Sal. Real (%)`
     - Quadrant background shapes (shaded or labeled rectangles) and dashed zero-lines.
   - Trajectory arrows/lines connecting P1 (2015-2019) to P2 (2021-2023) for each country showing direction of shift.
2. **Econometric OLS Summary Cell**:
   - Import `EconometricEstimator` / use `analyzer.run_econometric_regression(dataset)`.
   - Display formatted regression summary with $R^2$, Adj. $R^2$, F-pvalue, coefficients, and p-values table.
   - Textual interpretation grounded in Raúl's ECLAC macro-structuralist principles.
3. **Valid Notebook Syntax**:
   - `nbformat: 4`, Python 3 kernel.
   - Tested by `tests/test_notebook_syntax.py` with `ast.parse` for every code cell and assertions for `plotly` and `statsmodels`.

## TDD Instructions
1. Update `tests/test_notebook_syntax.py` to assert presence of `plotly`, `statsmodels`, and econometric regression in notebook cells.
2. Run `uv run pytest tests/test_notebook_syntax.py` to confirm failure (RED).
3. Generate the enhanced `notebooks/01_desacople_crecimiento_bienestar.ipynb`.
4. Run `uv run pytest tests/test_notebook_syntax.py` to confirm pass (GREEN).
5. Run full non-integration test suite: `uv run pytest -m "not integration"`.
6. Commit: `git add notebooks/01_desacople_crecimiento_bienestar.ipynb tests/test_notebook_syntax.py && git commit -m "feat(notebooks): upgrade 01_desacople with statsmodels OLS and interactive Plotly visualization"`.
7. Write report to `.superpowers/sdd/2026-10-14-decoupling-food-inflation-interactive-viz/task-6-report.md`.
8. Return status contract.
