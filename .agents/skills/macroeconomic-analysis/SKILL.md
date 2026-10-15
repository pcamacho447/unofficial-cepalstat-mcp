---
name: macroeconomic-analysis
description: Use when analyzing National Accounts, decomposing GDP expenditure or production, calculating terms of trade, estimating inflation pass-through, assessing fiscal sustainability, or evaluating balance of payments constraints.
---

# Macroeconomic Analysis

## Overview
Macroeconomic Analysis provides structural frameworks and empirical identities to analyze national accounts, trade balances, exchange rate dynamics, inflation pass-through, and public debt sustainability across developing and advanced economies.

## When to Use
- Validating and decomposing National Accounts (expenditure approach $C + I + G + X - M$, production approach, and income approach).
- Converting between current prices, constant base prices, and chain-linked volume measures.
- Analyzing external sector dynamics, terms of trade ($P_X / P_M$), and balance-of-payments constrained growth (Thirlwall's Law).
- Measuring inflation dynamics (headline vs core inflation) and estimating Exchange Rate Pass-Through (ERPT).
- Evaluating sovereign debt dynamics and primary balance requirements for debt stabilization.

When NOT to use:
- For low-level statistical test selection without macroeconomic theory (use `applied-statistics`).
- For generic microeconomic optimization (use `applied-mathematics`).

---

## 1. National Accounts Consistency & Accounting Identities

Macroeconomic aggregates must satisfy strict structural accounting identities. Any empirical model violating these identities is misspecified.

### Core Identities
1. **Expenditure Identity**:
   $$GDP \equiv C_{private} + G + I + (X - M)$$
   where $I = GFCF + \Delta \text{Inventories}$.
2. **Gross National Income (GNI)**:
   $$GNI \equiv GDP + BPI$$
   where $BPI$ is Net Primary Income from the rest of the world (repatriated profits, cross-border interest).
3. **Twin Deficits / Savings-Investment Gap**:
   $$(S_{private} - I_{private}) + (T - G) \equiv X - M + BPI + BSI \equiv CA$$
   where $CA$ is the Current Account Balance, and $(T - G)$ is the Fiscal Balance.

```python
import numpy as np
import pandas as pd


def verify_gdp_expenditure_identity(
    c: pd.Series,
    g: pd.Series,
    gfcf: pd.Series,
    inventories: pd.Series,
    exports: pd.Series,
    imports: pd.Series,
    gdp_reported: pd.Series,
    tolerance_pct: float = 0.5,
) -> pd.DataFrame:
  """Audit whether expenditure components sum to reported GDP within statistical discrepancy."""
  gdp_calc = c + g + gfcf + inventories + (exports - imports)
  discrepancy = gdp_reported - gdp_calc
  discrepancy_pct = (np.abs(discrepancy) / gdp_reported) * 100

  is_valid = discrepancy_pct <= tolerance_pct

  return pd.DataFrame({
      'gdp_reported': gdp_reported,
      'gdp_calculated': gdp_calc,
      'discrepancy': discrepancy,
      'discrepancy_pct': discrepancy_pct,
      'is_valid': is_valid,
  })
```

---

## 2. External Sector & Terms of Trade (Structuralist Economics)

In commodity-exporting economies (characteristic of Latin America and the Caribbean), terms of trade swings exert first-order shocks on domestic income and fiscal revenue.

### Terms of Trade ($TOT$) & Export Purchasing Power
$$TOT_t = \frac{P_{exports, t}}{P_{imports, t}} \times 100$$
$$\text{Purchasing Power of Exports} = Q_{exports, t} \times \frac{TOT_t}{100}$$

### Balance of Payments Constrained Growth (Thirlwall's Law)
In the long run, small open economies cannot sustainably grow faster than the rate permitted by balance of payments equilibrium without explosive external debt:
$$y_B = \frac{\epsilon \cdot z}{\pi}$$
where:
- $y_B$: Balance of payments constrained GDP growth rate.
- $\epsilon$: Income elasticity of export demand.
- $z$: Growth rate of global/partner GDP.
- $\pi$: Domestic income elasticity of import demand.

```python
def thirlwall_sustainable_growth(
    world_growth: float, export_elasticity: float, import_elasticity: float
) -> float:
  """Calculate Thirlwall's balance-of-payments constrained growth rate."""
  if import_elasticity <= 0:
    raise ValueError(
        "Import elasticity must be strictly positive (income elasticity of"
        " imports)."
    )
  return float((export_elasticity * world_growth) / import_elasticity)
```

---

## 3. Inflation Dynamics & Exchange Rate Pass-Through (ERPT)

Depreciation of the domestic currency increases import costs, passing through into domestic consumer prices.

### Econometric Specification for Pass-Through
$$\Delta \ln CPI_t = \alpha + \sum_{i=0}^p \beta_i \Delta \ln E_{t-i} + \sum_{j=1}^q \gamma_j \Delta \ln CPI_{t-j} + \theta \Delta \ln P_{foreign, t} + u_t$$

- **Short-run Pass-Through Elasticity**: $\beta_0$
- **Long-run Cumulative Pass-Through Elasticity**:
  $$ERPT_{long} = \frac{\sum_{i=0}^p \beta_i}{1 - \sum_{j=1}^q \gamma_j}$$

```python
import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate_erpt(
    df: pd.DataFrame, cpi_col: str, fx_col: str, lags: int = 4
) -> dict[str, float]:
  """Estimate short-run and long-run Exchange Rate Pass-Through (ERPT)."""
  d_ln_cpi = np.log(df[cpi_col]).diff()
  d_ln_fx = np.log(df[fx_col]).diff()

  reg_data = pd.DataFrame({'d_cpi': d_ln_cpi, 'd_fx': d_ln_fx}).dropna()

  # Create lag features
  fx_lag_cols = []
  for lag in range(lags + 1):
    col = f'd_fx_lag{lag}'
    reg_data[col] = reg_data['d_fx'].shift(lag)
    fx_lag_cols.append(col)

  cpi_lag_cols = []
  for lag in range(1, lags + 1):
    col = f'd_cpi_lag{lag}'
    reg_data[col] = reg_data['d_cpi'].shift(lag)
    cpi_lag_cols.append(col)

  clean = reg_data.dropna()
  X = sm.add_constant(clean[fx_lag_cols + cpi_lag_cols])
  y = clean['d_cpi']

  model = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': lags})

  sr_erpt = float(model.params['d_fx_lag0'])
  sum_fx = float(sum(model.params[col] for col in fx_lag_cols))
  sum_cpi = float(sum(model.params[col] for col in cpi_lag_cols))

  lr_erpt = float(sum_fx / (1.0 - sum_cpi)) if (1.0 - sum_cpi) != 0 else np.nan

  return {
      'short_run_erpt': sr_erpt,
      'long_run_erpt': lr_erpt,
      'r_squared': float(model.rsquared),
  }
```

---

## 4. Public Debt Sustainability Dynamics

The evolution of sovereign debt-to-GDP ratio $d_t = \frac{D_t}{Y_t}$ is governed by:
$$\Delta d_t = \frac{r_t - g_t}{1 + g_t} d_{t-1} - pb_t + sfa_t$$
where:
- $r_t$: Real effective interest rate on public debt.
- $g_t$: Real GDP growth rate.
- $pb_t$: Primary fiscal balance as percentage of GDP ($T - G$, excluding interest payments).
- $sfa_t$: Stock-flow adjustment (exchange rate revaluation, contingent liabilities).

### Debt-Stabilizing Primary Balance
To keep debt constant ($\Delta d_t = 0$):
$$pb^* = \frac{r - g}{1 + g} d$$

> [!NOTE]
> If $r > g$ (growth is lower than borrowing cost), the government must run structural primary surpluses just to stop debt from exploding. If $g > r$, positive growth naturally erodes the debt ratio.

```python
def debt_stabilizing_primary_balance(
    debt_to_gdp: float, real_interest_rate: float, real_gdp_growth: float
) -> float:
  """Calculate the primary balance (% of GDP) required to stabilize the debt-to-GDP ratio."""
  r = real_interest_rate
  g = real_gdp_growth
  d = debt_to_gdp
  return float(((r - g) / (1.0 + g)) * d)
```

---

## 5. Common Macroeconomic Pitfalls & Anti-Patterns

| Anti-Pattern | Why it Fails | Correct Approach |
| :--- | :--- | :--- |
| **Comparing Nominal GDP Across Countries** | Distorted by exchange rate volatility and inflation differentials. | Use **Constant Local Currency Units**, **Chain-linked USD**, or **PPP (Purchasing Power Parity)** dollars. |
| **Adding Core and Headline Inflation** | Core inflation is an extracted sub-index of headline CPI, not an additive component. | Report core inflation as an underlying trend alongside headline. |
| **Confusing Total and Primary Deficit** | Total deficit includes interest obligations from past debt; does not reflect current fiscal stance. | Use **Primary Balance** ($T - G$) to assess policy effort and sustainability. |
| **Ignoring Terms of Trade in National Income** | In commodity boom/busts, real GDP may grow slowly while real gross national income (GNDI) surges due to terms of trade gains. | Complement real GDP with **Trading Gains/Losses** and Real Disposable National Income. |
