---
name: applied-statistics
description: Use when calculating statistical moments, conducting normality or hypothesis tests, computing inequality and concentration metrics (Gini, Palma, Herfindahl), or performing bootstrap resampling.
---

# Applied Statistics

## Overview
Applied Statistics provides rigorous methodologies to summarize empirical distributions, test statistical hypotheses, quantify inequality and market concentration, and estimate non-parametric confidence intervals without unrealistic distributional assumptions.

## When to Use
- Evaluating distribution properties (skewness, kurtosis, fat tails, outliers).
- Testing normality and choosing between parametric ($t$-test, ANOVA) and non-parametric tests (Mann-Whitney, Wilcoxon).
- Measuring economic and social inequality (Gini index, Palma ratio, Lorenz curve, 20/20 ratio).
- Measuring concentration in industrial, trade, or geographical distributions (Herfindahl-Hirschman Index, Theil index).
- Calculating robust standard errors and confidence intervals via empirical bootstrap when analytic formulas are unavailable or asymptotic assumptions fail.

When NOT to use:
- For multi-variable causal identification with endogeneity and unobserved confounders (use `applied-econometrics`).
- For structural macroeconomic accounting identities (use `macroeconomic-analysis`).

---

## 1. Distribution Diagnostics & Hypothesis Testing Protocol

> [!IMPORTANT]
> Never assume Gaussian normality for economic, income, trade, or asset variables without testing. Income and wealth distributions are heavily right-skewed and fat-tailed.

### Step 1: Normality & Moment Diagnostics
```python
import numpy as np
import pandas as pd
from scipy import stats


def evaluate_distribution(data: pd.Series) -> dict[str, float | str]:
  """Diagnose sample moments and formal normality tests."""
  clean = data.dropna()
  n = len(clean)

  # Descriptive moments
  mean_val = float(clean.mean())
  median_val = float(clean.median())
  skew_val = float(stats.skew(clean))
  kurt_val = float(stats.kurtosis(clean))  # excess kurtosis (normal = 0)

  # Normality tests: Shapiro-Wilk for N <= 5000, Jarque-Bera for larger samples
  if n <= 5000:
    stat, p_val = stats.shapiro(clean)
    test_used = 'Shapiro-Wilk'
  else:
    stat, p_val = stats.jarque_bera(clean)
    test_used = 'Jarque-Bera'

  is_normal = p_val >= 0.05

  return {
      'n': n,
      'mean': mean_val,
      'median': median_val,
      'skewness': skew_val,
      'excess_kurtosis': kurt_val,
      'test_name': test_used,
      'p_value': p_val,
      'is_normal': is_normal,
      'recommendation': (
          'Parametric (t-test, ANOVA)'
          if is_normal
          else 'Non-parametric (Mann-Whitney, Wilcoxon, Bootstrap)'
      ),
  }
```

### Step 2: Parametric vs Non-Parametric Selection Matrix

| Scenario | Parametric Test (Normal) | Non-Parametric Test (Skewed / Heavy Tails) |
| :--- | :--- | :--- |
| **Two independent groups** | Two-sample Independent $t$-test (`scipy.stats.ttest_ind`) | Mann-Whitney $U$ test (`scipy.stats.mannwhitneyu`) |
| **Two paired / repeated measures** | Paired $t$-test (`scipy.stats.ttest_rel`) | Wilcoxon signed-rank test (`scipy.stats.wilcoxon`) |
| **Three or more groups** | One-way ANOVA (`scipy.stats.f_oneway`) | Kruskal-Wallis $H$-test (`scipy.stats.kruskal`) |
| **Correlation** | Pearson $r$ (`scipy.stats.pearsonr`) | Spearman $\rho$ / Kendall $\tau$ (`scipy.stats.spearmanr`) |

---

## 2. Inequality & Concentration Metrics

In socioeconomic analysis, summary averages (e.g. GDP per capita) mask extreme distributional disparities. Always accompany averages with inequality and concentration metrics.

### Vectorized Gini Coefficient ($O(n \log n)$) & Palma Ratio
```python
import numpy as np
import pandas as pd


def gini_coefficient(
    values: np.ndarray, weights: np.ndarray | None = None
) -> float:
  """Calculate the Gini coefficient efficiently using sorted cumulative areas.

  Accepts optional survey/sampling weights.
  """
  v = np.asarray(values, dtype=float)
  if np.any(v < 0):
    raise ValueError("Gini coefficient requires non-negative values.")
  if len(v) == 0 or np.sum(v) == 0:
    return 0.0

  if weights is None:
    # Unweighted Gini: O(n log n)
    v_sorted = np.sort(v)
    n = len(v_sorted)
    index = np.arange(1, n + 1)
    return float((2.0 * np.sum(index * v_sorted)) / (n * np.sum(v_sorted)) - (n + 1.0) / n)
  else:
    # Weighted Gini: handles population/survey weights
    w = np.asarray(weights, dtype=float)
    order = np.argsort(v)
    v_sorted, w_sorted = v[order], w[order]
    cw = np.cumsum(w_sorted)
    pw = cw / cw[-1]
    cy = np.cumsum(v_sorted * w_sorted)
    py = cy / cy[-1]
    return float(1.0 - np.sum((pw[1:] - pw[:-1]) * (py[1:] + py[:-1])))


def palma_ratio(values: np.ndarray) -> float:
  """Palma ratio: Share of income/wealth held by the top 10% divided by share held by bottom 40%."""
  v = np.sort(np.asarray(values, dtype=float))
  n = len(v)
  if n < 10:
    raise ValueError("Insufficient observations for decile calculation.")

  p40_cut = int(np.floor(0.40 * n))
  p90_cut = int(np.floor(0.90 * n))

  bottom_40_share = np.sum(v[:p40_cut])
  top_10_share = np.sum(v[p90_cut:])

  if bottom_40_share <= 0:
    return np.nan
  return float(top_10_share / bottom_40_share)
```

### Market / Export Concentration: Herfindahl-Hirschman Index (HHI)
The Herfindahl-Hirschman Index measures concentration of market shares or export baskets:
$$HHI = \sum_{i=1}^N s_i^2 \quad \text{where } s_i \text{ is the percentage share } (0 \le s_i \le 100)$$

- **$HHI < 1,500$**: Unconcentrated / diversified.
- **$1,500 \le HHI \le 2,500$**: Moderately concentrated.
- **$HHI > 2,500$**: Highly concentrated (vulnerable to external commodity price shocks).

```python
def herfindahl_index(shares: np.ndarray) -> float:
  """Calculate HHI given market or product shares (shares summing to 100 or 1)."""
  s = np.asarray(shares, dtype=float)
  if np.isclose(np.sum(s), 1.0):
    s = s * 100.0  # normalize to 0-100 scale
  return float(np.sum(s**2))
```

---

## 3. Bootstrap Resampling for Non-Standard Statistics

When calculating standard errors or confidence intervals for statistics without simple analytical distributions (e.g. median, Palma ratio, Gini coefficient), use the empirical bootstrap.

```python
from scipy.stats import bootstrap


def bootstrap_metric_ci(
    data: np.ndarray,
    metric_func,
    n_resamples: int = 2000,
    confidence_level: float = 0.95,
) -> tuple[float, float, float]:
  """Compute point estimate and bootstrap confidence intervals (BCa method)."""
  res = bootstrap(
      (data,),
      statistic=metric_func,
      n_resamples=n_resamples,
      confidence_level=confidence_level,
      method='BCa',
  )
  point_estimate = float(metric_func(data))
  ci_lower = float(res.confidence_interval.low)
  ci_upper = float(res.confidence_interval.high)
  return point_estimate, ci_lower, ci_upper
```

---

## 4. Common Statistical Pitfalls & Anti-Patterns

| Anti-Pattern | Why it Fails | Correct Approach |
| :--- | :--- | :--- |
| **Using Mean on Skewed Data** | Extreme outliers pull the mean away from the typical observation. | Report **Median + Interquartile Range (IQR)** alongside Mean. |
| **Multiple Comparisons without Correction** | Testing $k$ hypotheses at $\alpha = 0.05$ inflates Family-Wise Error Rate ($1 - 0.95^k$). | Apply **Benjamini-Hochberg (FDR)** or **Bonferroni** correction. |
| **Ignoring Survey Sample Weights** | Raw sample estimates produce severe urban or demographic selection bias. | Use weighted estimators ($w_i$) for means, proportions, and Gini. |
| **Conflating Statistical and Economic Significance** | Huge sample sizes ($N > 100,000$) make tiny, economically irrelevant differences statistically significant ($p < 0.001$). | Always report **Effect Sizes** (Cohen's $d$, percentage changes) alongside $p$-values. |
