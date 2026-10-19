"""Econometric estimation engine for growth-wellbeing decoupling analysis."""

from typing import Any
import numpy as np
import pandas as pd
import statsmodels.api as sm

from unofficial_cepalstat_mcp.analysis.models import DecouplingDataset, RegressionModelSummary


def _clean_metric(val: Any, default: float = 0.0) -> float:
    """Safely convert and round numerical estimation metrics to 4 decimal places."""
    if val is None or pd.isna(val) or np.isinf(val):
        return default
    return round(float(val), 4)


class EconometricEstimator:
    """Fits multivariate econometric models on decoupling and poverty datasets."""

    INDEPENDENT_VARS = [
        "gdp_pc_growth_mean",
        "real_min_wage_change_pct",
        "food_inflation_mean_pct",
    ]
    DEPENDENT_VAR = "poverty_total_change_pp"

    @classmethod
    def fit_poverty_growth_model(
        cls,
        dataset: DecouplingDataset,
        impute_missing: bool = False,
    ) -> RegressionModelSummary:
        """Estimate multivariate OLS model explaining poverty change.

        Model specification:
            ΔPobreza_{i,t} = β_0 + β_1 * PIB_{i,t} + β_2 * ΔSalario_{i,t} + β_3 * InflAlimentos_{i,t} + ε_{i,t}

        Args:
            dataset: DecouplingDataset containing CountryPeriodMetric records.
            impute_missing: If True, imputes 0.0 for missing wage and food inflation changes.
                           If False, drops records with any missing regression variable.

        Returns:
            RegressionModelSummary with R², coefficients, p-values, standard errors,
            confidence intervals, and observation count.
        """
        if not dataset.records:
            return RegressionModelSummary(
                r_squared=0.0,
                r_squared_adj=0.0,
                coefficients={},
                p_values={},
                std_errors={},
                confidence_intervals={},
                n_obs=0,
                f_pvalue=1.0,
            )

        df = pd.DataFrame([r.model_dump() for r in dataset.records])

        if cls.DEPENDENT_VAR not in df.columns:
            return RegressionModelSummary(
                r_squared=0.0,
                r_squared_adj=0.0,
                coefficients={},
                p_values={},
                std_errors={},
                confidence_intervals={},
                n_obs=0,
                f_pvalue=1.0,
            )

        # Ensure numeric values and drop null dependent variables
        df[cls.DEPENDENT_VAR] = pd.to_numeric(df[cls.DEPENDENT_VAR], errors="coerce")
        df = df.dropna(subset=[cls.DEPENDENT_VAR])

        for col in cls.INDEPENDENT_VARS:
            if col not in df.columns:
                df[col] = np.nan
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if impute_missing:
            # Impute neutral 0.0 for wage and food inflation
            df["real_min_wage_change_pct"] = df["real_min_wage_change_pct"].fillna(0.0)
            df["food_inflation_mean_pct"] = df["food_inflation_mean_pct"].fillna(0.0)
            df = df.dropna(subset=["gdp_pc_growth_mean"])
        else:
            df = df.dropna(subset=cls.INDEPENDENT_VARS)

        n_usable = len(df)
        # If usable sample size is less than 4 (k=4 parameters including constant), return minimal summary
        if n_usable < 4:
            return RegressionModelSummary(
                r_squared=0.0,
                r_squared_adj=0.0,
                coefficients={},
                p_values={},
                std_errors={},
                confidence_intervals={},
                n_obs=n_usable,
                f_pvalue=1.0,
            )

        y = df[cls.DEPENDENT_VAR].astype(float)
        x = df[cls.INDEPENDENT_VARS].astype(float)

        try:
            x_const = sm.add_constant(x)
            model = sm.OLS(y, x_const)
            results = model.fit()

            conf_df = results.conf_int()
            confidence_intervals: dict[str, tuple[float, float]] = {
                str(k): (
                    _clean_metric(conf_df.loc[k, 0]),
                    _clean_metric(conf_df.loc[k, 1]),
                )
                for k in conf_df.index
            }

            return RegressionModelSummary(
                r_squared=_clean_metric(results.rsquared),
                r_squared_adj=_clean_metric(results.rsquared_adj),
                coefficients={str(k): _clean_metric(v) for k, v in results.params.items()},
                p_values={str(k): _clean_metric(v, 1.0) for k, v in results.pvalues.items()},
                std_errors={str(k): _clean_metric(v) for k, v in results.bse.items()},
                confidence_intervals=confidence_intervals,
                n_obs=int(results.nobs),
                f_pvalue=_clean_metric(getattr(results, "f_pvalue", 1.0), 1.0),
            )
        except Exception:
            return RegressionModelSummary(
                r_squared=0.0,
                r_squared_adj=0.0,
                coefficients={},
                p_values={},
                std_errors={},
                confidence_intervals={},
                n_obs=n_usable,
                f_pvalue=1.0,
            )
