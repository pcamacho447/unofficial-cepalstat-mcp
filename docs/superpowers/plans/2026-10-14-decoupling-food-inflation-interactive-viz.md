# Growth-Wellbeing Econometric Engine & Interactive Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade econometric analysis suite using `statsmodels` for formal regression modeling of growth-poverty-wage-inflation elasticities across Latin America, create a specialized BMAD/Superpowers agent & skill (`cepal-econometrician` / `cepalstat-econometrics`), integrate CEPALSTAT food inflation (Indicator 2929), and upgrade the Jupyter notebook (`01_desacople_crecimiento_bienestar.ipynb`) with interactive Plotly visualizations and econometric summary tables.

**Architecture:** 
1. **Econometric Core (`statsmodels`):** Implement `EconometricEstimator` in `src/statscepal/analysis/econometrics.py` to fit OLS regression models ($\Delta \text{Pobreza} = \alpha + \beta_1 \Delta \text{PIB} + \beta_2 \Delta \text{SalarioReal} + \beta_3 \text{InflAlimentos} + \epsilon$), estimating robust elasticities, p-values, standard errors, and $R^2$.
2. **Food Inflation & Purchasing Power:** Integrate Indicator 2929 into `DecouplingAnalyzer` using Dimension 79565 member IDs; compute `food_inflation_mean_pct` and `food_wage_gap_pct`.
3. **Agent & Skill Layer:** Create BMAD Agent `bmad-agent-econometrician` ("Raúl", 📈) and Superpowers Skill `cepalstat-econometrics` with domain guidelines for structuralist econometric interpretation.
4. **Interactive Notebook & CLI:** Interactive Plotly scatter plot with tooltips, trajectories, and OLS regression summary display in `notebooks/01_desacople_crecimiento_bienestar.ipynb`; expanded CLI output.

**Tech Stack:** Python 3.10+, `pydantic>=2.7.0`, `pandas>=2.2.0`, `statsmodels>=0.14.0`, `plotly>=5.20.0`, `pytest>=8.0.0`, CEPALSTAT Open Data API.

**Spec:** [docs/superpowers/specs/2026-10-14-desacople-social-notebooks-design.md](file:///C:/papx/statscepal/docs/superpowers/specs/2026-10-14-desacople-social-notebooks-design.md).

## Global Constraints
- Modern Python 3.10+ typing syntax (`float | None`).
- TDD mandatory for all mathematical/statistical logic.
- All 113 existing unit/regression tests must remain green.
- Plotly charts must render standalone in JupyterLab 4 / VS Code without requiring npm/node dependencies.
- Windows console UTF-8 safe encoding safeguards.

---

### Task 1: Dependencies & Data Models (`pyproject.toml`, `models.py`)

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/statscepal/analysis/models.py`
- Modify: `tests/test_analysis_models.py`

**Interfaces:**
- `CountryPeriodMetric` fields:
  - `food_inflation_mean_pct: float | None = None`
  - `food_wage_gap_pct: float | None = None`
- New Model: `RegressionModelSummary`:
  - `r_squared: float`
  - `p_values: dict[str, float]`
  - `coefficients: dict[str, float]`
  - `confidence_intervals: dict[str, tuple[float, float]]`
  - `n_obs: int`
  - `f_pvalue: float`

- [ ] **Step 1: Write failing test in `tests/test_analysis_models.py`**
Test `CountryPeriodMetric` with food inflation and `RegressionModelSummary` creation.

- [ ] **Step 2: Run test to confirm failure (RED)**
Run: `uv run pytest tests/test_analysis_models.py`

- [ ] **Step 3: Update `pyproject.toml` and `models.py`**
- Add `"statsmodels>=0.14.0"` and `"plotly>=5.20.0"` to dependencies in `pyproject.toml`.
- Add `RegressionModelSummary` and update `CountryPeriodMetric` in `src/statscepal/analysis/models.py`.
- Run: `uv sync --extra dev`.

- [ ] **Step 4: Run test to confirm pass (GREEN)**
Run: `uv run pytest tests/test_analysis_models.py`

- [ ] **Step 5: Commit**
```bash
git add pyproject.toml src/statscepal/analysis/models.py tests/test_analysis_models.py
git commit -m "feat(analysis): add statsmodels dependency and econometric regression data models"
```

---

### Task 2: Econometric Estimation Engine with `statsmodels` (`econometrics.py`)

**Files:**
- Create: `src/statscepal/analysis/econometrics.py`
- Modify: `src/statscepal/analysis/__init__.py`
- Create: `tests/test_analysis_econometrics.py`

**Interfaces:**
- Produces: `EconometricEstimator`:
  - `fit_poverty_growth_model(dataset: DecouplingDataset) -> RegressionModelSummary`:
    Fits OLS: $\Delta \text{Pobreza} = \beta_0 + \beta_1 \Delta \text{PIB} + \beta_2 \Delta \text{SalarioReal} + \beta_3 \text{InflAlimentos} + \epsilon$.
    Returns `RegressionModelSummary` with $R^2$, coefficients, p-values, and 95% confidence intervals.
  - Handles sparse data gracefully (returns informative summary or raises domain error if $N < 4$).

- [ ] **Step 1: Write failing test in `tests/test_analysis_econometrics.py`**
Mock a `DecouplingDataset` with 12 observation rows, verify OLS fitting, $R^2 \in [0, 1]$, and valid coefficients.

- [ ] **Step 2: Run test to confirm failure (RED)**
Run: `uv run pytest tests/test_analysis_econometrics.py`

- [ ] **Step 3: Implement `src/statscepal/analysis/econometrics.py` using `statsmodels.api.OLS`**
Export `EconometricEstimator` in `src/statscepal/analysis/__init__.py`.

- [ ] **Step 4: Run test to confirm pass (GREEN)**
Run: `uv run pytest tests/test_analysis_econometrics.py`

- [ ] **Step 5: Commit**
```bash
git add src/statscepal/analysis/econometrics.py src/statscepal/analysis/__init__.py tests/test_analysis_econometrics.py
git commit -m "feat(analysis): implement EconometricEstimator using statsmodels OLS"
```

---

### Task 3: DecouplingAnalyzer Service with Indicator 2929 (`service.py`)

**Files:**
- Modify: `src/statscepal/analysis/service.py`
- Modify: `src/statscepal/analysis/metrics.py`
- Modify: `tests/test_analysis_service.py`

**Interfaces:**
- `DecouplingAnalyzer`:
  - Fetches Indicator 2929 using Dimension 79565 member IDs (`79568`, `79578`, `79579`, `79599`, `79604`, `79612`).
  - Matches countries across dimension `Países_agregados regionales especiales VAR IPC`.
  - Calculates `food_inflation_mean_pct` and `food_wage_gap_pct` for each period.
  - Method `run_econometric_regression() -> RegressionModelSummary`.

- [ ] **Step 1: Write unit test with mock Indicator 2929 data in `tests/test_analysis_service.py`**
- [ ] **Step 2: Run test to confirm failure (RED)**
Run: `uv run pytest tests/test_analysis_service.py`
- [ ] **Step 3: Implement Indicator 2929 integration in `service.py`**
- [ ] **Step 4: Run test to confirm pass (GREEN)**
Run: `uv run pytest tests/test_analysis_service.py`
- [ ] **Step 5: Commit**
```bash
git add src/statscepal/analysis/service.py src/statscepal/analysis/metrics.py tests/test_analysis_service.py
git commit -m "feat(analysis): integrate food inflation Indicator 2929 into DecouplingAnalyzer"
```

---

### Task 4: Custom BMAD Agent & Superpowers Skill (`cepal-econometrician`)

**Files:**
- Create: `.agents/skills/bmad-agent-econometrician/SKILL.md` (BMAD Agent: Raúl, 📈)
- Create: `.agents/skills/bmad-agent-econometrician/customize.toml`
- Create: `.agents/skills/cepalstat-econometrics/SKILL.md` (Superpowers Skill: CEPAL Econometrics Methodology)
- Test: `tests/test_skill_structure.py`

**Content:**
- **Agent Raúl (`bmad-agent-econometrician`):**
  - Identity: Latin American macro-structuralist economist channeling Raúl Prebisch, Celso Furtado, and modern empirical econometrics.
  - Specialization: Elasticity estimation, terms-of-trade, food inflation pass-through, wage-profit share distribution, and growth-wellbeing decoupling.
  - Voice: Measured, rigorous, passionate about structural heterogeneity and verifiable regression evidence.
- **Skill `cepalstat-econometrics`:**
  - Standard instructions, mathematical formulations of social elasticity, OLS regression interpretation rules with `statsmodels`, and CEPALSTAT series harmonization best practices.

- [ ] **Step 1: Write skill tests in `tests/test_skill_structure.py` checking agent and skill validation**
- [ ] **Step 2: Run test to confirm failure (RED)**
- [ ] **Step 3: Create agent and skill files**
- [ ] **Step 4: Run test to confirm pass (GREEN)**
Run: `uv run pytest tests/test_skill_structure.py`
- [ ] **Step 5: Commit**
```bash
git add .agents/skills/bmad-agent-econometrician/ .agents/skills/cepalstat-econometrics/ tests/test_skill_structure.py
git commit -m "feat(agents): create bmad-agent-econometrician and cepalstat-econometrics skill"
```

---

### Task 5: CLI Subcommand Integration (`cli.py`)

**Files:**
- Modify: `src/statscepal/cli.py`
- Modify: `tests/test_cli_analyze.py`

- [ ] **Step 1: Write test for `--econometrics` flag and new table columns**
- [ ] **Step 2: Implement `--econometrics` flag in `cli.py` displaying OLS regression summary table**
- [ ] **Step 3: Run `uv run pytest tests/test_cli_analyze.py`**
- [ ] **Step 4: Commit**
```bash
git add src/statscepal/cli.py tests/test_cli_analyze.py
git commit -m "feat(cli): add econometrics regression output to analyze desacople"
```

---

### Task 6: Interactive Plotly & Econometric Jupyter Notebook (`01_desacople_crecimiento_bienestar.ipynb`)

**Files:**
- Modify: `notebooks/01_desacople_crecimiento_bienestar.ipynb`
- Modify: `tests/test_notebook_syntax.py`

**Requirements:**
- Upgrade Section 3: Comparative table with food inflation and wage-food gap.
- Upgrade Section 4:
  1. Interactive Plotly bubble chart (`plotly.express.scatter`):
     - Hover tooltip: Country, Period, GDP pc growth, Poverty change, Food inflation, Real wage change, Wage-Food Gap, Quadrant.
     - Bubble size: Absolute magnitude of Food-Wage Gap.
     - Color: Socioeconomic Quadrant.
     - Bounding boxes and quadrant watermarks.
  2. Trajectory lines linking P1 (2015-2019) to P2 (2021-2023).
- Upgrade Section 5:
  1. Execution and display of `EconometricEstimator.fit_poverty_growth_model(dataset)` with summary table ($R^2$, p-values, coefficients).
  2. Diagnostic conclusions by Raúl / ECLAC Econometrician on the food inflation vs wage mechanism.

- [ ] **Step 1: Update `tests/test_notebook_syntax.py` to assert Plotly & statsmodels presence**
- [ ] **Step 2: Generate enhanced notebook JSON**
- [ ] **Step 3: Run `uv run pytest tests/test_notebook_syntax.py`**
- [ ] **Step 4: Commit**
```bash
git add notebooks/01_desacople_crecimiento_bienestar.ipynb tests/test_notebook_syntax.py
git commit -m "feat(notebooks): upgrade 01_desacople with statsmodels OLS and interactive Plotly visualization"
```

---

### Task 7: Whole-Branch Integration & Verification

- [ ] **Step 1: Run complete test suite**
Run: `uv run pytest -m "not integration"`
Expected: 120+ passed, 0 failures.

- [ ] **Step 2: Test live CLI command with econometrics flag**
Run: `uv run statscepal analyze desacople --countries México,Argentina,Chile --econometrics`

- [ ] **Step 3: Final verification**
```bash
git status
```
Confirm working tree is clean.
