# Task 6 Report: Interactive Plotly & Econometric Jupyter Notebook (`01_desacople_crecimiento_bienestar.ipynb`)

## Summary
- Upgraded `notebooks/01_desacople_crecimiento_bienestar.ipynb` and `tests/test_notebook_syntax.py` adhering strictly to TDD:
  1. **TDD RED Phase**:
     - Updated `tests/test_notebook_syntax.py` with assertions for `plotly`, `statsmodels`, `EconometricEstimator`, `FOOD_INFLATION_MEMBER_MAP`, `Infl. Alim`, `Brecha Sal/Alim`, regression calls (`run_econometric_regression` or `fit_poverty_growth_model`), and interactive trajectory lines/traces (`add_shape`, `add_annotation`, `add_trace`, `Trayectoria`).
     - Ran `uv run pytest tests/test_notebook_syntax.py` and captured RED failure (`AssertionError: Notebook missing required keyword or concept: 'plotly'`).
  2. **Notebook Implementation & Enhancement (All 5 Sections Preserved & Upgraded)**:
     - **Section 1 (Context, Methodology & Imports)**:
       - Incorporated ECLAC structuralist framework (Raúl Prebisch, Celso Furtado) explaining the food inflation wedge and real minimum wage buffer.
       - Imported `plotly.express`, `plotly.graph_objects`, `statsmodels.api`, `EconometricEstimator`, `FOOD_INFLATION_MEMBER_MAP`, `compute_food_wage_gap`, `classify_quadrant`, etc.
     - **Section 2 (Multi-Country Data Extraction with Indicator 2929)**:
       - Extracted series for Argentina, Chile, Colombia, México, Perú, and Uruguay for 2015-2019 and 2021-2023.
       - Integrated food inflation series (Indicator 2929, Dimension 79565) harmonized via `FOOD_INFLATION_MEMBER_MAP`.
     - **Section 3 (Comparative Metrics Table)**:
       - Enhanced `df_metrics` DataFrame and `df_pivot` comparison table with `Infl. Alim (%)` and `Brecha Sal/Alim (%)`.
     - **Section 4 (Interactive Plotly Quadrant & Trajectory Visualization)**:
       - Built 2x2 socioeconomic quadrant scatter with `plotly.express.scatter` and `plotly.graph_objects`:
         - X-axis: `Δ PIB pc (%)`, Y-axis: `Δ Pob. Tot (pp)`
         - Interactive tooltips with country, period, GDP delta, poverty delta, wage delta, food inflation, wage-food gap, and quadrant.
         - Color-coded quadrants (Virtuoso, Excluyente, Resiliencia, Doble Vulnerabilidad).
         - Bubble size scaled by absolute magnitude of `Brecha Sal/Alim (%)`.
         - Shaded background quadrant rectangles (`fig.add_shape`) and dashed zero-lines (`fig.add_hline`, `fig.add_vline`).
         - Trajectory lines and directional arrow annotations (`fig.add_trace`, `fig.add_annotation`) connecting P1 (2015-2019) to P2 (2021-2023) for each country.
       - Added comparative bar chart panels contrasting real minimum wage variation with food-wage gaps.
     - **Section 5 (Econometric OLS Estimation & Structuralist Diagnostics)**:
       - Executed `analyzer.run_econometric_regression(dataset, impute_missing=False)` yielding $R^2 = 0.8204$, Adj $R^2 = 0.7306$, and F-pvalue $= 0.0118$.
       - Formatted and printed an OLS estimation summary table with coefficients, SEs, p-values, and 95% confidence intervals.
       - Authored deep analytical discussion from the perspective of Raúl (ECLAC macro-structuralist econometrician) explaining:
         - The non-significance of headline GDP per capita ($\beta_1 = -0.3190, p = 0.1716$) once controlling for wages and food inflation, demonstrating social decoupling.
         - The critical institutional transmission role of the real minimum wage ($\beta_2 = -0.1329, p = 0.0078^{***}$).
         - The regressive impact of the food inflation wedge ($\beta_3 = +0.0242, p = 0.0777^{*}$).
       - Added executive diagnostic reporting cell.
  3. **TDD GREEN Phase & Non-Integration Suite**:
     - Verified all code cells are syntactically valid Python parsable with `ast.parse`.
     - Verified notebook conforms to `nbformat: 4`.
     - `uv run pytest tests/test_notebook_syntax.py` passed cleanly (1 passed in 0.07s).
     - Full non-integration suite: 130 passed, 2 deselected in 24.46s.

## Commit
- `a82278b19f07bcb4e686e36348697692e052d217`: `feat(notebooks): upgrade 01_desacople with statsmodels OLS and interactive Plotly visualization`

## Test Results
- `tests/test_notebook_syntax.py`: 1 passed in 0.07s
- Full non-integration suite (`pytest -m "not integration"`): 130 passed, 2 deselected in 24.46s
