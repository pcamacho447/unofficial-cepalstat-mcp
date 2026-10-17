# Task 1: Dependencies & Data Models (`pyproject.toml`, `models.py`)

## Objective
Add `statsmodels>=0.14.0` and `plotly>=5.20.0` to project dependencies, and update Pydantic models in `src/statscepal/analysis/models.py` with food inflation metrics and an econometric regression model summary.

## Files
- Modify: `pyproject.toml`
- Modify: `src/statscepal/analysis/models.py`
- Modify: `src/statscepal/analysis/__init__.py`
- Modify: `tests/test_analysis_models.py`

## Specifications
1. **`pyproject.toml`**:
   - Add `"statsmodels>=0.14.0"` and `"plotly>=5.20.0"` into `[project.dependencies]`.
2. **`src/statscepal/analysis/models.py`**:
   - In `CountryPeriodMetric`:
     - Add `food_inflation_mean_pct: float | None = None`
     - Add `food_wage_gap_pct: float | None = None`
   - Create class `RegressionModelSummary(BaseModel)`:
     ```python
     class RegressionModelSummary(BaseModel):
         """Econometric OLS regression results summary."""
         r_squared: float
         r_squared_adj: float = 0.0
         coefficients: dict[str, float] = Field(default_factory=dict)
         p_values: dict[str, float] = Field(default_factory=dict)
         std_errors: dict[str, float] = Field(default_factory=dict)
         confidence_intervals: dict[str, tuple[float, float]] = Field(default_factory=dict)
         n_obs: int = 0
         f_pvalue: float = 1.0
     ```
3. **`src/statscepal/analysis/__init__.py`**:
   - Export `RegressionModelSummary` and include in `__all__`.

## TDD Instructions
1. Write failing tests in `tests/test_analysis_models.py` verifying `CountryPeriodMetric` with food inflation fields and `RegressionModelSummary` instantiation.
2. Run `uv run pytest tests/test_analysis_models.py` to confirm failure (RED).
3. Update `pyproject.toml`, run `uv sync --extra dev`.
4. Update `src/statscepal/analysis/models.py` and `__init__.py`.
5. Run `uv run pytest tests/test_analysis_models.py` to confirm pass (GREEN).
6. Run full non-integration test suite: `uv run pytest -m "not integration"`.
7. Commit: `git add pyproject.toml uv.lock src/statscepal/analysis/models.py src/statscepal/analysis/__init__.py tests/test_analysis_models.py && git commit -m "feat(analysis): add statsmodels dependency and econometric regression data models"`.
8. Write report to `.superpowers/sdd/2026-10-14-decoupling-food-inflation-interactive-viz/task-1-report.md`.
9. Return status contract.
