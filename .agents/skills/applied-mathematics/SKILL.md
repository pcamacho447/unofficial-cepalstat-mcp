---
name: applied-mathematics
description: Use when calculating growth rates, computing point or arc elasticities, checking matrix conditioning, solving constrained optimization problems, or applying filtering and detrending (Hodrick-Prescott).
---

# Applied Mathematics

## Overview
Applied Mathematics provides analytical and numerical foundations for quantitative economics, including differential calculus for growth and elasticities, numerical linear algebra conditioning, constrained optimization, and time series filtering.

## When to Use
- Computing discrete growth rates, continuous log-growth ($\Delta \ln X$), and Compound Annual Growth Rates (CAGR).
- Calculating point elasticities ($\frac{d \ln Y}{d \ln X}$) and arc (midpoint) elasticities.
- Assessing numerical matrix conditioning ($\kappa(A)$) and preventing singular matrix errors in high-dimensional models.
- Solving constrained optimization problems (cost minimization, utility maximization, resource allocation) via Karush-Kuhn-Tucker (KKT) and numerical solvers.
- Extracting business cycle fluctuations and long-term trends via the Hodrick-Prescott (HP) filter.

When NOT to use:
- For pure statistical inference and hypothesis testing (use `applied-statistics`).
- For structural econometric causal identification (use `applied-econometrics`).

---

## 1. Growth Rates & Elasticity Calculus

### Discrete Growth vs Continuous Log-Growth
For small percentage changes ($|g| < 0.10$), first differences of natural logarithms approximate discrete growth:
$$\Delta \ln X_t = \ln X_t - \ln X_{t-1} \approx \frac{X_t - X_{t-1}}{X_{t-1}} = g_t$$

> [!WARNING]
> For large shocks (e.g. GDP contraction of -15% or hyperinflation of +80%), the log approximation diverges significantly:
> - True discrete growth: $g_t = \exp(\Delta \ln X_t) - 1$
> - Log change: $\Delta \ln X_t = \ln(1 + g_t)$
> Never report log differences as percentage points during crisis periods without exact transformation.

### Elasticity Formulas
1. **Point Elasticity**:
   $$\epsilon = \frac{dY}{dX} \cdot \frac{X}{Y} = \frac{d \ln Y}{d \ln X}$$
2. **Arc Elasticity (Midpoint formula)**:
   Avoids base-year asymmetry when calculating elasticity between two discrete points $(X_1, Y_1)$ and $(X_2, Y_2)$:
   $$\epsilon_{arc} = \frac{Y_2 - Y_1}{(Y_1 + Y_2) / 2} \div \frac{X_2 - X_1}{(X_1 + X_2) / 2} = \frac{Y_2 - Y_1}{X_2 - X_1} \cdot \frac{X_1 + X_2}{Y_1 + Y_2}$$

```python
import numpy as np
import pandas as pd


def compute_growth_rates(series: pd.Series) -> pd.DataFrame:
  """Compute exact discrete growth, log growth, and annualized rate."""
  clean = series.dropna()
  discrete = clean.pct_change()
  log_growth = np.log(clean) - np.log(clean.shift(1))

  return pd.DataFrame({
      'level': clean,
      'discrete_growth': discrete,
      'log_growth': log_growth,
      'approx_error_pct': np.abs(discrete - log_growth) * 100,
  })


def cagr(start_val: float, end_val: float, periods: float) -> float:
  """Compound Annual Growth Rate (CAGR)."""
  if start_val <= 0 or end_val <= 0 or periods <= 0:
    raise ValueError("CAGR requires strictly positive values and periods > 0.")
  return float((end_val / start_val) ** (1.0 / periods) - 1.0)


def arc_elasticity(x1: float, y1: float, x2: float, y2: float) -> float:
  """Calculate symmetric midpoint arc elasticity between two coordinates."""
  delta_y = y2 - y1
  delta_x = x2 - x1
  if delta_x == 0:
    raise ZeroDivisionError("delta_x cannot be zero for elasticity calculation.")
  return float((delta_y / ((y1 + y2) / 2.0)) / (delta_x / ((x1 + x2) / 2.0)))
```

---

## 2. Linear Algebra Conditioning & Matrix Inversion

In structural estimation and OLS, computing $(X^T X)^{-1}$ requires numerical inversion. If regressors are nearly collinear, the Gram matrix $A = X^T X$ is ill-conditioned.

### Condition Number Diagnostic
$$\kappa(A) = \|A\| \cdot \|A^{-1}\| = \frac{\sigma_{max}}{\sigma_{min}}$$
- **$\kappa(A) < 100$**: Well-conditioned; standard inversion is reliable.
- **$100 \le \kappa(A) < 1,000$**: Moderate multicollinearity; monitor coefficient variance.
- **$\kappa(A) \ge 1,000$**: Severe ill-conditioning; standard OLS coefficients have extreme numerical instability.

```python
import numpy as np


def diagnose_matrix_conditioning(X: np.ndarray) -> dict[str, float | str]:
  """Evaluate conditioning of design matrix X and suggest inversion strategy."""
  X_clean = np.asarray(X, dtype=float)
  # Singular values
  s = np.linalg.svd(X_clean, compute_uv=False)
  sigma_max = s[0]
  sigma_min = s[-1]

  cond_num = float(
      sigma_max / sigma_min if sigma_min > 1e-12 else np.finfo(float).max
  )

  if cond_num < 100:
    status = 'Well-conditioned'
    action = 'Standard inversion (np.linalg.solve)'
  elif cond_num < 1000:
    status = 'Moderate collinearity'
    action = 'Check VIF or use QR decomposition'
  else:
    status = 'Severely ill-conditioned (Near Singular)'
    action = 'Use SVD, Ridge regularization (Tikhonov), or drop collinear cols'

  return {
      'condition_number': cond_num,
      'sigma_max': float(sigma_max),
      'sigma_min': float(sigma_min),
      'status': status,
      'recommended_action': action,
  }
```

---

## 3. Constrained Mathematical Optimization (`scipy.optimize`)

Economic problems (e.g. cost minimization subject to production quotas, or optimal portfolio weights) require constrained nonlinear optimization:

$$\min_{x} f(x) \quad \text{subject to } g_i(x) \ge 0, \; h_j(x) = 0$$

```python
import numpy as np
from scipy.optimize import minimize


def optimize_allocation(
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    target_return: float,
) -> np.ndarray:
  """Find minimum variance weights subject to target return and sum(weights) = 1."""
  n = len(expected_returns)

  # Objective: Portfolio variance 0.5 * w.T @ Sigma @ w
  def objective(w):
    return 0.5 * float(w @ cov_matrix @ w)

  # Constraints:
  # 1. Sum of weights = 1
  # 2. Expected return >= target_return
  constraints = [
      {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
      {
          'type': 'ineq',
          'fun': lambda w: float(w @ expected_returns) - target_return,
      },
  ]

  # Bounds: No short-selling (w_i >= 0)
  bounds = [(0.0, 1.0) for _ in range(n)]
  w0 = np.ones(n) / n

  result = minimize(
      objective, w0, method='SLSQP', bounds=bounds, constraints=constraints
  )
  if not result.success:
    raise RuntimeError(f'Optimization failed: {result.message}')

  return result.x
```

---

## 4. Detrending & Business Cycle Filtering (Hodrick-Prescott)

Decompose a macroeconomic time series $y_t$ into a smooth non-linear trend $g_t$ and cyclical component $c_t = y_t - g_t$:

### Standard $\lambda$ Smoothing Penalties
- **Annual data**: $\lambda = 100$ (CEPAL / Ravn-Uhlig recommended: $\lambda = 6.25$ or $100$)
- **Quarterly data**: $\lambda = 1,600$
- **Monthly data**: $\lambda = 14,400$

```python
import pandas as pd
from statsmodels.tsa.filters.hp_filter import hpfilter


def decompose_trend_cycle(
    series: pd.Series, freq: str = 'annual'
) -> pd.DataFrame:
  """Apply Hodrick-Prescott filter to separate trend and business cycle."""
  clean = series.dropna()
  lambdas = {
      'annual': 100.0,
      'annual_low': 6.25,
      'quarterly': 1600.0,
      'monthly': 14400.0,
  }
  lambda_val = lambdas.get(freq, 100.0)

  cycle, trend = hpfilter(clean, lamb=lambda_val)

  return pd.DataFrame({
      'actual': clean,
      'trend': trend,
      'cycle': cycle,
      'cycle_pct_of_trend': (cycle / trend) * 100,
  })
```

---

## 5. Common Mathematical Pitfalls & Anti-Patterns

| Anti-Pattern | Why it Fails | Correct Approach |
| :--- | :--- | :--- |
| **Using $\Delta \ln X$ on Negative or Zero Values** | $\ln(x)$ is undefined for $x \le 0$ (e.g. trade balances, net investment). | Use discrete percentage changes or symmetric arc percentage metrics. |
| **Naive Matrix Inversion `np.linalg.inv(X.T @ X)`** | Numerical truncation error explodes when condition number $\kappa > 10^4$. | Use `np.linalg.solve(X.T @ X, X.T @ y)` or QR decomposition. |
| **HP Filter End-Point Bias** | The HP filter places asymmetric weight on the beginning and end of the sample. | Pad series with ARIMA forecasts before filtering or report caution for last 2 years. |
| **Compound vs Simple Annualization** | Multiplying monthly growth by 12 underestimates compound inflation/growth ($1.05^{12} \neq 1 + 0.05 \times 12$). | Use geometric compounding: $(1 + g_m)^{12} - 1$. |
