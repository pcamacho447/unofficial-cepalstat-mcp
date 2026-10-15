---
name: applied-econometrics
description: Use when estimating regression models, conducting time series unit root or cointegration tests, fitting panel data regressions, calculating robust standard errors, or diagnosing endogeneity and heteroscedasticity.
---

# Applied Econometrics

## Overview
Applied Econometrics provides rigorous statistical methodology to estimate economic relationships, test theoretical hypotheses, and establish empirical causality while avoiding spurious correlations, endogeneity traps, and distorted standard errors.

## When to Use
- Estimating elasticities, structural multipliers, or behavioral equations across cross-sectional, time series, or panel data.
- Testing for unit roots ($I(1)$ vs $I(0)$) and cointegrating relationships between non-stationary series.
- Controlling for unobserved heterogeneity using Panel Fixed Effects or Random Effects.
- Estimating causal policy impacts via Instrumental Variables (2SLS) or Difference-in-Differences (DiD).

When NOT to use:
- For pure out-of-sample machine learning prediction without causal or structural interpretation (use standard ML pipelines).
- For non-statistical mathematical accounting identities ($Y \equiv C + I + G + X - M$).

---

## 1. Anti-Spurious Regression Protocol (Time Series)

> [!WARNING]
> Never run OLS on trending non-stationary series in levels ($R^2 > 0.90$ with low Durbin-Watson is almost always spurious).

### Step 1: Dual Unit Root Verification
Always run both ADF (null: non-stationary) and KPSS (null: stationary):

```python
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss


def verify_stationarity(series: pd.Series) -> str:
  """Diagnose stationarity using joint ADF and KPSS tests."""
  clean = series.dropna()
  adf_p = adfuller(clean)[1]
  kpss_p = kpss(clean, regression='c', nlags='auto')[1]

  if adf_p < 0.05 and kpss_p >= 0.05:
    return 'I(0) Stationary'
  elif adf_p >= 0.05 and kpss_p < 0.05:
    return 'I(1) Non-stationary (Unit Root)'
  elif adf_p >= 0.05 and kpss_p >= 0.05:
    return 'Inconclusive (Likely Non-stationary)'
  else:
    return 'Trend-stationary (Needs detrending)'
```

### Step 2: Cointegration vs. First-Differences
- If $Y_t$ and $X_t$ are $I(1)$ and **cointegrated** (residuals are $I(0)$): estimate an **Error Correction Model (ECM)** or **ARDL** to capture long-run equilibrium + short-run dynamics.
- If $Y_t$ and $X_t$ are $I(1)$ and **NOT cointegrated**: estimate in first differences ($\Delta Y_t = \beta \Delta X_t + \epsilon_t$).

---

## 2. Robust Standard Errors & Diagnostic Checklist

Standard OLS standard errors assume i.i.d. spherical errors. In economic data, this assumption almost always fails.

### Diagnostic Matrix
| Problem | Diagnostic Test | Correction Method |
| :--- | :--- | :--- |
| **Heteroscedasticity** | Breusch-Pagan / White test (`p < 0.05`) | White-Huber Robust Errors (`cov_type='HC3'`) |
| **Serial Autocorrelation** | Breusch-Godfrey / Ljung-Box test | Newey-West HAC Errors (`cov_type='HAC', maxlags=p`) |
| **Multicollinearity** | Variance Inflation Factor (`VIF > 10`) | Ridge / Drop redundant collinear regressor |
| **Endogeneity** | Durbin-Wu-Hausman test | Two-Stage Least Squares (`IV2SLS`) |

### Production Python Pattern (`statsmodels`)
```python
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_breusch_godfrey, het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor

# 1. Fit OLS with Newey-West HAC standard errors
X = sm.add_constant(df[['x1', 'x2']])
y = df['y']
model = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': 4})

# 2. Check Heteroscedasticity
bp_stat, bp_pval, _, _ = het_breuschpagan(model.resid, X)

# 3. Check Serial Autocorrelation
bg_stat, bg_pval, _, _ = acorr_breusch_godfrey(model, nlags=2)

# 4. Check Multicollinearity (VIF)
vif_data = pd.DataFrame({
    'Variable': X.columns,
    'VIF': [
        variance_inflation_factor(X.values, i) for i in range(X.shape[1])
    ],
})
```

---

## 3. Panel Data Econometrics (`linearmodels`)

When observing entities (countries, firms, individuals) over time:

1. **Fixed Effects (`PanelOLS`, entity_effects=True)**: Always preferred when unobserved entity traits (e.g. geography, institutional history) correlate with regressors.
2. **Clustered Standard Errors**: Always cluster at the entity level to allow arbitrary autocorrelation within entity time series.

```python
from linearmodels import PanelOLS

# MultiIndex index: [entity, time]
panel = df.set_index(['country_code', 'year'])

# Two-way fixed effects (country + year) with clustered standard errors
fe_model = PanelOLS(
    dependent=panel['y'],
    exog=panel[['x1', 'x2']],
    entity_effects=True,
    time_effects=True,
).fit(cov_type='clustered', cluster_entity=True)
print(fe_model.summary)
```

---

## 4. Common Mistakes & Anti-Patterns

| Anti-Pattern | Why it Fails | Correct Approach |
| :--- | :--- | :--- |
| **Reporting $R^2$ as proof of causality** | Confounded by common time trends. | Test stationarity, cointegration, and report F-statistics. |
| **Uncorrected OLS standard errors** | Understates standard errors, generating false $p < 0.01$ results. | Apply HC3 or Newey-West HAC corrections. |
| **Dropping outliers without justification** | Induces sample selection bias. | Use robust regression (`RLM`) or Winsorization with documentation. |
| **Estimating non-cointegrated levels** | Spurious regression. | Estimate first differences ($\Delta Y \sim \Delta X$). |
