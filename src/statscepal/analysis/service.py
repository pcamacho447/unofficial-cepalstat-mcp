"""Service orchestrator for growth-wellbeing decoupling analysis."""

import unicodedata
import pandas as pd

from statscepal.analysis.econometrics import EconometricEstimator
from statscepal.analysis.metrics import (
    classify_quadrant,
    compute_elasticity,
    compute_food_wage_gap,
)
from statscepal.analysis.models import (
    CountryPeriodMetric,
    DecouplingDataset,
    RegressionModelSummary,
)
from statscepal.extractor import DataExtractor

# Mapeo de IDs de países oficiales en series económicas y sociales de CEPALSTAT
COUNTRY_MEMBER_MAP: dict[str, int] = {
    "argentina": 216,
    "chile": 224,
    "colombia": 225,
    "méxico": 233,
    "mexico": 233,
    "perú": 244,
    "peru": 244,
    "uruguay": 258,
}

# Mapeo de IDs de países en la serie de inflación de alimentos (Indicador 2929, Dimensión 79565)
FOOD_INFLATION_MEMBER_MAP: dict[str, int] = {
    "argentina": 79568,
    "chile": 79578,
    "colombia": 79579,
    "méxico": 79599,
    "mexico": 79599,
    "perú": 79604,
    "peru": 79604,
    "uruguay": 79612,
}


def _normalize(text: str) -> str:
    """Normalize string by removing accents, converting to lowercase and stripping whitespace."""
    return (
        unicodedata.normalize("NFKD", str(text))
        .encode("ascii", "ignore")
        .decode("utf-8")
        .lower()
        .strip()
    )


def _find_food_country_column(columns: list[str]) -> str | None:
    """Find country column in Indicator 2929 DataFrame."""
    if "Países_agregados regionales especiales VAR IPC" in columns:
        return "Países_agregados regionales especiales VAR IPC"
    for col in columns:
        norm = _normalize(col)
        if "pais" in norm:
            return col
    for col in columns:
        norm = _normalize(col)
        if "agregados regionales" in norm or "var ipc" in norm:
            return col
    return None


def _find_year_column(columns: list[str]) -> str | None:
    """Find year column in DataFrame."""
    for col in ["Años__ESTANDAR", "Años", "Anos__ESTANDAR", "Año", "year", "Year"]:
        if col in columns:
            return col
    for col in columns:
        norm = _normalize(col)
        if "ano" in norm or "year" in norm:
            return col
    return None


class DecouplingAnalyzer:
    """Orchestrates indicator fetching, temporal alignment, and metrics computation."""

    def __init__(self, extractor: DataExtractor) -> None:
        self.extractor = extractor
        self._last_dataset: DecouplingDataset | None = None

    def analyze_countries(
        self,
        countries: list[str],
        periods: list[tuple[str, int, int]],
    ) -> DecouplingDataset:
        """Analyze a list of countries across defined time periods.

        Args:
            countries: List of country names (e.g. ['Chile', 'Argentina']).
            periods: List of tuples with (period_label, start_year, end_year).

        Returns:
            DecouplingDataset with calculated metrics per country and period.
        """
        member_ids: list[int] = []
        food_member_ids: list[int] = []
        for c in countries:
            key = c.lower()
            if key in COUNTRY_MEMBER_MAP:
                member_ids.append(COUNTRY_MEMBER_MAP[key])
            elif _normalize(c) in COUNTRY_MEMBER_MAP:
                member_ids.append(COUNTRY_MEMBER_MAP[_normalize(c)])

            if key in FOOD_INFLATION_MEMBER_MAP:
                food_member_ids.append(FOOD_INFLATION_MEMBER_MAP[key])
            elif _normalize(c) in FOOD_INFLATION_MEMBER_MAP:
                food_member_ids.append(FOOD_INFLATION_MEMBER_MAP[_normalize(c)])

        unique_member_ids = list(dict.fromkeys(member_ids)) or None
        unique_food_member_ids = list(dict.fromkeys(food_member_ids)) or None

        # Descarga de los 5 indicadores clave:
        # 3894: PIB pc tasa de crecimiento anual
        # 3328: Pobreza por área y situación
        # 340: Salario mínimo real (índice 2018=100)
        # 3289: Índice de Gini
        # 2929: Variación de precios de alimentos
        df_pib = self.extractor.get_dataframe(3894, members=unique_member_ids)
        df_pob = self.extractor.get_dataframe(3328, members=unique_member_ids)
        df_sal = self.extractor.get_dataframe(340, members=unique_member_ids)
        df_gini = self.extractor.get_dataframe(3289, members=unique_member_ids)
        df_food = self.extractor.get_dataframe(
            2929, members=unique_food_member_ids, decode_labels=True
        )

        for df in [df_pib, df_pob, df_sal, df_gini, df_food]:
            if df is not None and not df.empty:
                y_col = _find_year_column(df.columns.tolist())
                if y_col and y_col in df.columns:
                    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
                if "value" in df.columns:
                    df["value"] = pd.to_numeric(df["value"], errors="coerce")

        records: list[CountryPeriodMetric] = []

        for country_name in countries:
            norm_country = _normalize(country_name)
            # Determinación de área geográfica (Argentina usa Total del área urbana)
            area = "Total del área urbana" if norm_country == "argentina" else "Nacional"

            for period_label, start_year, end_year in periods:
                # Filtrar PIB
                if (
                    df_pib is not None
                    and not df_pib.empty
                    and "País__ESTANDAR" in df_pib.columns
                    and "Años__ESTANDAR" in df_pib.columns
                ):
                    pib_match = df_pib["País__ESTANDAR"].apply(_normalize) == norm_country
                    pib_years = df_pib["Años__ESTANDAR"].between(start_year, end_year)
                    sub_pib = df_pib[pib_match & pib_years]
                else:
                    sub_pib = pd.DataFrame()

                # Filtrar Pobreza
                if (
                    df_pob is not None
                    and not df_pob.empty
                    and "País__ESTANDAR" in df_pob.columns
                    and "Años__ESTANDAR" in df_pob.columns
                ):
                    pob_match = df_pob["País__ESTANDAR"].apply(_normalize) == norm_country
                    pob_years = df_pob["Años__ESTANDAR"].between(start_year, end_year)
                    mask = pob_match & pob_years
                    if "Area geográfica_(EH)" in df_pob.columns:
                        mask = mask & (df_pob["Area geográfica_(EH)"] == area)
                    sub_pob = df_pob[mask]
                else:
                    sub_pob = pd.DataFrame()

                # Filtrar Salario Real
                if (
                    df_sal is not None
                    and not df_sal.empty
                    and "País__ESTANDAR" in df_sal.columns
                    and "Años__ESTANDAR" in df_sal.columns
                ):
                    sal_match = df_sal["País__ESTANDAR"].apply(_normalize) == norm_country
                    sal_years = df_sal["Años__ESTANDAR"].between(start_year, end_year)
                    sub_sal = df_sal[sal_match & sal_years]
                else:
                    sub_sal = pd.DataFrame()

                # Filtrar Gini
                if (
                    df_gini is not None
                    and not df_gini.empty
                    and "País__ESTANDAR" in df_gini.columns
                    and "Años__ESTANDAR" in df_gini.columns
                ):
                    gini_match = df_gini["País__ESTANDAR"].apply(_normalize) == norm_country
                    gini_years = df_gini["Años__ESTANDAR"].between(start_year, end_year)
                    sub_gini = df_gini[gini_match & gini_years]
                else:
                    sub_gini = pd.DataFrame()

                # Filtrar Inflación de Alimentos (Indicador 2929)
                food_country_col = (
                    _find_food_country_column(df_food.columns.tolist())
                    if (df_food is not None and not df_food.empty)
                    else None
                )
                food_year_col = (
                    _find_year_column(df_food.columns.tolist())
                    if (df_food is not None and not df_food.empty)
                    else None
                )

                if (
                    df_food is not None
                    and not df_food.empty
                    and food_country_col is not None
                    and food_year_col is not None
                    and "value" in df_food.columns
                ):
                    food_match = df_food[food_country_col].apply(_normalize) == norm_country
                    food_years = df_food[food_year_col].between(start_year, end_year)
                    sub_food = df_food[food_match & food_years]
                else:
                    sub_food = pd.DataFrame()

                # 1. Promedio anual del crecimiento de PIB pc
                if not sub_pib.empty and "value" in sub_pib.columns:
                    valid_pib = sub_pib["value"].dropna()
                    pib_mean = float(valid_pib.mean()) if not valid_pib.empty else 0.0
                else:
                    pib_mean = 0.0

                # 2. Pobreza total y extrema
                pob_tot = pd.DataFrame()
                pob_ext = pd.DataFrame()
                if not sub_pob.empty:
                    if (
                        "Pobreza extrema y pobreza" in sub_pob.columns
                        and "Años__ESTANDAR" in sub_pob.columns
                        and "value" in sub_pob.columns
                    ):
                        pob_tot = (
                            sub_pob[sub_pob["Pobreza extrema y pobreza"] == "Pobreza"]
                            .dropna(subset=["value"])
                            .sort_values("Años__ESTANDAR")
                        )
                        pob_ext = (
                            sub_pob[sub_pob["Pobreza extrema y pobreza"] == "Pobreza extrema"]
                            .dropna(subset=["value"])
                            .sort_values("Años__ESTANDAR")
                        )

                pob_tot_chg = (
                    float(pob_tot.iloc[-1]["value"] - pob_tot.iloc[0]["value"])
                    if len(pob_tot) >= 2
                    else None
                )
                pob_ext_chg = (
                    float(pob_ext.iloc[-1]["value"] - pob_ext.iloc[0]["value"])
                    if len(pob_ext) >= 2
                    else None
                )

                # 3. Cambio porcentual salario mínimo real
                sal_sorted = (
                    sub_sal.dropna(subset=["value"]).sort_values("Años__ESTANDAR")
                    if not sub_sal.empty and "Años__ESTANDAR" in sub_sal.columns and "value" in sub_sal.columns
                    else pd.DataFrame()
                )
                sal_chg = (
                    float(((sal_sorted.iloc[-1]["value"] / sal_sorted.iloc[0]["value"]) - 1.0) * 100.0)
                    if len(sal_sorted) >= 2 and sal_sorted.iloc[0]["value"] > 0
                    else None
                )

                # 4. Cambio en índice de Gini
                gini_sorted = (
                    sub_gini.dropna(subset=["value"]).sort_values("Años__ESTANDAR")
                    if not sub_gini.empty and "Años__ESTANDAR" in sub_gini.columns and "value" in sub_gini.columns
                    else pd.DataFrame()
                )
                gini_chg = (
                    float(gini_sorted.iloc[-1]["value"] - gini_sorted.iloc[0]["value"])
                    if len(gini_sorted) >= 2
                    else None
                )

                # 5. Inflación de alimentos y brecha poder adquisitivo
                if not sub_food.empty and "value" in sub_food.columns:
                    valid_food = sub_food["value"].dropna()
                    food_inflation_mean = (
                        round(float(valid_food.mean()), 2)
                        if not valid_food.empty
                        else None
                    )
                else:
                    food_inflation_mean = None

                food_wage_gap = compute_food_wage_gap(
                    round(sal_chg, 2) if sal_chg is not None else None,
                    food_inflation_mean,
                )

                # 6. Rango de años observados
                years_range = (
                    f"{int(pob_tot.iloc[0]['Años__ESTANDAR'])}-{int(pob_tot.iloc[-1]['Años__ESTANDAR'])}"
                    if len(pob_tot) >= 2
                    else f"{start_year}-{end_year}"
                )

                # 7. Elasticidad social y cuadrante socioeconómico
                elasticity = compute_elasticity(pob_tot_chg, pib_mean)
                quadrant = classify_quadrant(pib_mean, pob_tot_chg, gini_chg)

                records.append(
                    CountryPeriodMetric(
                        country=country_name,
                        period_label=period_label,
                        years_range=years_range,
                        gdp_pc_growth_mean=round(pib_mean, 2),
                        poverty_total_change_pp=round(pob_tot_chg, 2) if pob_tot_chg is not None else None,
                        poverty_extreme_change_pp=round(pob_ext_chg, 2) if pob_ext_chg is not None else None,
                        real_min_wage_change_pct=round(sal_chg, 2) if sal_chg is not None else None,
                        gini_change=round(gini_chg, 4) if gini_chg is not None else None,
                        food_inflation_mean_pct=food_inflation_mean,
                        food_wage_gap_pct=food_wage_gap,
                        social_elasticity=elasticity,
                        quadrant=quadrant,
                    )
                )

        dataset = DecouplingDataset(
            records=records,
            metadata={"countries": countries, "total_records": len(records)},
        )
        self._last_dataset = dataset
        return dataset

    def run_econometric_regression(
        self,
        dataset: DecouplingDataset | None = None,
        impute_missing: bool = False,
    ) -> RegressionModelSummary:
        """Fit econometric poverty-growth regression model on a decoupling dataset.

        Delegates to EconometricEstimator.fit_poverty_growth_model.

        Args:
            dataset: DecouplingDataset containing CountryPeriodMetric records.
                     If None, uses the dataset from the last call to analyze_countries.
            impute_missing: If True, imputes 0.0 for missing wage and food inflation changes.

        Returns:
            RegressionModelSummary with R², coefficients, p-values, standard errors,
            confidence intervals, and observation count.
        """
        target = dataset if dataset is not None else self._last_dataset
        if target is None:
            target = DecouplingDataset()
        return EconometricEstimator.fit_poverty_growth_model(target, impute_missing=impute_missing)

