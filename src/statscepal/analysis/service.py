"""Service orchestrator for growth-wellbeing decoupling analysis."""

import unicodedata
import pandas as pd

from statscepal.analysis.metrics import (
    classify_quadrant,
    compute_elasticity,
)
from statscepal.analysis.models import CountryPeriodMetric, DecouplingDataset
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


def _normalize(text: str) -> str:
    """Normalize string by removing accents, converting to lowercase and stripping whitespace."""
    return (
        unicodedata.normalize("NFKD", str(text))
        .encode("ascii", "ignore")
        .decode("utf-8")
        .lower()
        .strip()
    )


class DecouplingAnalyzer:
    """Orchestrates indicator fetching, temporal alignment, and metrics computation."""

    def __init__(self, extractor: DataExtractor) -> None:
        self.extractor = extractor

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
        for c in countries:
            key = c.lower()
            if key in COUNTRY_MEMBER_MAP:
                member_ids.append(COUNTRY_MEMBER_MAP[key])
            elif _normalize(c) in COUNTRY_MEMBER_MAP:
                member_ids.append(COUNTRY_MEMBER_MAP[_normalize(c)])

        unique_member_ids = list(dict.fromkeys(member_ids)) or None

        # Descarga de los 4 indicadores clave:
        # 3894: PIB pc tasa de crecimiento anual
        # 3328: Pobreza por área y situación
        # 340: Salario mínimo real (índice 2018=100)
        # 3289: Índice de Gini
        df_pib = self.extractor.get_dataframe(3894, members=unique_member_ids)
        df_pob = self.extractor.get_dataframe(3328, members=unique_member_ids)
        df_sal = self.extractor.get_dataframe(340, members=unique_member_ids)
        df_gini = self.extractor.get_dataframe(3289, members=unique_member_ids)

        for df in [df_pib, df_pob, df_sal, df_gini]:
            if df is not None and not df.empty:
                if "Años__ESTANDAR" in df.columns:
                    df["Años__ESTANDAR"] = pd.to_numeric(df["Años__ESTANDAR"], errors="coerce")
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

                # 5. Rango de años observados
                years_range = (
                    f"{int(pob_tot.iloc[0]['Años__ESTANDAR'])}-{int(pob_tot.iloc[-1]['Años__ESTANDAR'])}"
                    if len(pob_tot) >= 2
                    else f"{start_year}-{end_year}"
                )

                # 6. Elasticidad social y cuadrante socioeconómico
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
                        social_elasticity=elasticity,
                        quadrant=quadrant,
                    )
                )

        return DecouplingDataset(
            records=records,
            metadata={"countries": countries, "total_records": len(records)},
        )
