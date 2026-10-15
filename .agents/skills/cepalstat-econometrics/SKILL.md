---
name: cepalstat-econometrics
description: Use when modeling, estimating, or interpreting econometrics, poverty elasticities, real wage pass-through, or OLS regressions with statsmodels using CEPALSTAT data.
---

# CEPALSTAT Structuralist Econometrics & Decoupling Analysis

This skill provides the methodological, econometric, and statistical foundations for analyzing Latin American growth-wellbeing decoupling, social elasticity of growth, real wage pass-through, and food inflation shocks using UN CEPAL / ECLAC official data series.

---

## 1. Theoretical Framework: Latin American Structuralism

Latin American structuralist economics (pioneered by Raúl Prebisch and CEPAL) posits that macroeconomic growth does not automatically translate into linear social well-being improvements. Due to **structural heterogeneity** (*heterogeneidad estructural*), labor market segmentation, and asymmetric consumption baskets, the social impact of macroeconomic expansions varies significantly across countries and cycles.

Key transmission channels include:
1. **Food Inflation Channel (Indicator 2929):** The poorest quintiles allocate between 40% and 60% of household income to basic food baskets. High food inflation directly erodes real disposable income even when headline CPI or GDP growth appears favorable.
2. **Real Wage Erosion Channel (Indicator 2928):** Minimum wage adjustments lagging behind food inflation trigger a negative **Purchasing Power Gap** ($\Delta\% \text{Salario} - \text{InflAlimentos}$), driving poverty increases amidst aggregate economic expansion.
3. **Growth-Wellbeing Decoupling:** When GDP per capita expands but poverty fails to decline (or increases), economies enter an **Exclusionary Growth** (*Crecimiento Excluyente*) regime.

---

## 2. Social Elasticity of Growth

The social elasticity of poverty with respect to economic growth measures the responsiveness of poverty reduction to output expansion:

$$\epsilon_{\text{pobreza}} = \frac{\Delta\% \text{Pobreza}}{\Delta\% \text{PIB}}$$

Where:
- $\Delta\% \text{Pobreza} = \frac{\text{Pobreza}_t - \text{Pobreza}_{t-1}}{\text{Pobreza}_{t-1}} \times 100$ (or percentage point variation $\Delta \text{pp}$)
- $\Delta\% \text{PIB} = \text{Annualized growth rate of GDP per capita}$

### Elasticity Diagnostic Benchmarks
- **Virtuous Elasticity ($\epsilon < -1.0$):** High social pass-through. A 1% increase in GDP per capita generates more than a 1% decline in poverty.
- **Inelastic Transmission ($-1.0 \le \epsilon < 0$):** Moderate pass-through. Growth reduces poverty, but dampened by structural rigidities.
- **Decoupled / Pathological Regime ($\epsilon \ge 0$ while $\Delta \text{PIB} > 0$):** Growth decoupling. Output expands while poverty stagnates or worsens (*Crecimiento Excluyente*).

---

## 3. Multivariate OLS Econometric Model Specification

To isolate the structural determinants of poverty changes across multi-country panel windows, `statscepal.analysis.econometrics.EconometricEstimator` specifies the following multivariate Ordinary Least Squares (OLS) model:

$$\Delta \text{Pobreza}_{i,t} = \beta_0 + \beta_1 \cdot \text{PIB}_{i,t} + \beta_2 \cdot \Delta\% \text{Salario}_{i,t} + \beta_3 \cdot \text{InflAlimentos}_{i,t} + \varepsilon_{i,t}$$

### Variables
- **Dependent Variable:**
  - `poverty_total_change_pp` ($\Delta \text{Pobreza}_{i,t}$): Percentage point change in national poverty rate (Indicator 4788) over the period.
- **Independent Variables:**
  - `gdp_pc_growth_mean` ($\text{PIB}_{i,t}$): Mean annualized real GDP per capita growth rate (Indicator 2207).
  - `real_min_wage_change_pct` ($\Delta\% \text{Salario}_{i,t}$): Percentage change in the real minimum wage index (Indicator 2928).
  - `food_inflation_mean_pct` ($\text{InflAlimentos}_{i,t}$): Mean annual food and non-alcoholic beverages inflation rate (Indicator 2929).
  - $\varepsilon_{i,t}$: Idiosyncratic structural disturbance term.

### Expected Structural Signs
- $\beta_1 < 0$: Faster economic growth reduces poverty.
- $\beta_2 < 0$: Real minimum wage gains expand labor income at the base of the distribution, accelerating poverty reduction.
- $\beta_3 > 0$: Surging food inflation elevates the extreme poverty line (canasta básica alimentaria), aggravating poverty.

---

## 4. Statistical Diagnostic and Interpretation Norms

When presenting and interpreting regressions fitted by `EconometricEstimator` via `statsmodels`:

### P-Value ($p$) Significance Thresholds
- $p < 0.01$ (***): Robust empirical evidence rejecting $H_0: \beta_k = 0$.
- $p < 0.05$ (**): Conventional statistical significance standard.
- $p < 0.10$ (*): Marginally significant; indicative trend requiring larger sample size ($N$).
- $p \ge 0.10$: Statistically insignificant; cannot reject null hypothesis.

### Goodness-of-Fit: R-Squared ($R^2$) and Adjusted $R^2$
- $R^2$ gauges the fraction of total poverty variance explained by macroeconomic growth, real wages, and food inflation.
- In cross-country Latin American growth panels, $R^2$ values typically range between $0.35$ and $0.65$.
- A lower $R^2$ is not inherently a model defect: it empirically evidences the presence of strong non-macro structural factors (e.g., targeted conditional cash transfers, informal sector dynamics, remittance shocks).

### Confidence Intervals
- Evaluate whether the 95% confidence interval $[\hat{\beta}_k - 1.96 \cdot \text{SE}, \hat{\beta}_k + 1.96 \cdot \text{SE}]$ crosses zero. If zero is contained within the bounds, the directional effect cannot be affirmed with 95% confidence.

---

## 5. Food Inflation Channel & Purchasing Power Gap

### Indicator 2929: Variación en doce meses del IPC de alimentos y bebidas
Food prices are notoriously volatile in Latin America due to terms-of-trade fluctuations, exchange rate pass-through, and climate events (El Niño/La Niña). Because basic foods are income-inelastic necessities, low-income households cannot substitute away from food basket shocks.

### Purchasing Power Gap Formula
The purchasing power gap directly compares wage expansion against food price escalation:

$$\text{Gap}_{\text{PoderAdquisitivo}} = \Delta\% \text{Salario} - \text{InflAlimentos}$$

- **Positive Gap ($\text{Gap} > 0$):** Real wage growth outpaces food inflation, shielding household purchasing power.
- **Negative Gap ($\text{Gap} < 0$):** Real purchasing power erosion. Even if general inflation is moderate, food inflation dominates the subsistence threshold.

### 2x2 Socioeconomic Quadrant Matrix
Classification of country-period performance:

| Quadrant | Condition | Structural Interpretation |
|---|---|---|
| **Crecimiento Virtuoso** | $\Delta \text{PIB} > 0 \land \Delta \text{Pobreza} < 0$ | Broad-based growth with effective social transmission and wage protection. |
| **Crecimiento Excluyente** | $\Delta \text{PIB} > 0 \land \Delta \text{Pobreza} \ge 0$ | Economic growth decoupled from welfare; wealth concentration or food shock. |
| **Resiliencia Social** | $\Delta \text{PIB} \le 0 \land \Delta \text{Pobreza} \le 0$ | Economic stagnation/contraction mitigated by social safety nets or remittances. |
| **Doble Vulnerabilidad** | $\Delta \text{PIB} \le 0 \land \Delta \text{Pobreza} > 0$ | Macroeconomic contraction compounded by social deterioration. |

---

## 6. Python API Usage with `EconometricEstimator`

`statscepal` implements the econometric estimation pipeline via `statsmodels` in `statscepal.analysis.econometrics.EconometricEstimator`:

```python
from statscepal.analysis import DecouplingAnalyzer, EconometricEstimator
from statscepal.analysis.models import DecouplingDataset, RegressionModelSummary

# 1. Build or retrieve the decoupling dataset across Latin American economies
analyzer = DecouplingAnalyzer()
dataset: DecouplingDataset = analyzer.build_dataset(
    countries=["Chile", "Colombia", "México", "Brasil", "Perú", "Uruguay"],
    start_year=2015,
    end_year=2023,
)

# 2. Fit the multivariate OLS model using statsmodels
model_summary: RegressionModelSummary = EconometricEstimator.fit_poverty_growth_model(
    dataset=dataset,
    impute_missing=False,  # Set True to impute neutral 0.0 for wage/food inflation
)

# 3. Inspect regression results
print(f"R²: {model_summary.r_squared:.4f}")
print(f"Adjusted R²: {model_summary.r_squared_adj:.4f}")
print(f"Observations (N): {model_summary.n_obs}")
print(f"Overall F-statistic p-value: {model_summary.f_pvalue:.4f}")

print("\nCoefficients & P-Values:")
for var_name, coef in model_summary.coefficients.items():
    pval = model_summary.p_values.get(var_name, 1.0)
    se = model_summary.std_errors.get(var_name, 0.0)
    ci = model_summary.confidence_intervals.get(var_name, (0.0, 0.0))
    sig = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.10 else ""
    print(f"  {var_name:25s}: β = {coef:8.4f} (SE: {se:.4f}, p = {pval:.4f}) {sig} 95% CI {ci}")
```

### Accessing Summary Attributes
- `model_summary.r_squared`: Coefficient of determination ($R^2$).
- `model_summary.r_squared_adj`: Adjusted $R^2$ accounting for parameter count.
- `model_summary.coefficients`: Mapping of variable name to estimated coefficient $\hat{\beta}$.
- `model_summary.p_values`: Two-tailed p-values for testing $H_0: \beta_k = 0$.
- `model_summary.std_errors`: Standard errors of estimated coefficients.
- `model_summary.confidence_intervals`: 95% confidence intervals `(lower, upper)`.
- `model_summary.n_obs`: Number of usable observations with complete data.
- `model_summary.f_pvalue`: Prob > F for overall model significance.
