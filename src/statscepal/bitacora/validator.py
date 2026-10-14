"""Statistical Anti-Bias and Data Quality Validator."""

import re
from typing import Any

import pandas as pd

from statscepal.bitacora.models import AntiBiasChecklist, DataQualityReport


class AntiBiasValidator:
    """Validates datasets against common statistical biases, temporal gaps, and metadata integrity."""

    @classmethod
    def audit(
        cls,
        df: pd.DataFrame,
        metadata: dict[str, Any] | None = None,
        year_column: str = "Años__ESTANDAR",
        value_column: str = "value",
    ) -> tuple[DataQualityReport, AntiBiasChecklist]:
        """Perform a statistical quality audit and generate an anti-bias checklist.

        Args:
            df: DataFrame containing the extracted indicator data.
            metadata: Dictionary of indicator metadata (unit, comments, etc.).
            year_column: Expected column name for years.
            value_column: Expected column name for numerical values.

        Returns:
            Tuple of (DataQualityReport, AntiBiasChecklist).
        """
        meta = metadata or {}
        warnings: list[str] = []

        total_records = len(df)
        if total_records == 0:
            return (
                DataQualityReport(total_records=0),
                AntiBiasChecklist(unit_verified=False, warnings=["DataFrame está vacío."]),
            )

        # 1. Null values check
        null_count = int(df[value_column].isna().sum()) if value_column in df.columns else 0
        null_ratio = float(null_count / total_records) if total_records > 0 else 0.0
        if null_count > 0:
            warnings.append(
                f"Se detectaron {null_count} valores nulos/faltantes ({null_ratio:.1%})."
            )

        # 2. Values statistics
        min_val = None
        max_val = None
        if value_column in df.columns:
            valid_vals = pd.to_numeric(df[value_column], errors="coerce").dropna()
            if not valid_vals.empty:
                min_val = float(valid_vals.min())
                max_val = float(valid_vals.max())

        # 3. Temporal gap analysis
        min_year = None
        max_year = None
        has_gaps = False

        # Attempt to find the year column dynamically if needed
        actual_year_col = None
        for col in [year_column, "year", "Años", "año", "Año"]:
            if col in df.columns:
                actual_year_col = col
                break

        if actual_year_col:
            years_series = pd.to_numeric(df[actual_year_col], errors="coerce").dropna().astype(int)
            if not years_series.empty:
                unique_years = sorted(years_series.unique())
                min_year = int(unique_years[0])
                max_year = int(unique_years[-1])
                expected_years = set(range(min_year, max_year + 1))
                if set(unique_years) != expected_years:
                    has_gaps = True
                    missing_years = sorted(expected_years - set(unique_years))
                    warnings.append(
                        f"Discontinuidad temporal detectada. Años faltantes en la serie: {missing_years[:5]}..."
                    )

        # 4. Scale factor and unit verification
        unit = meta.get("unit", "")
        scale_note = f"Unidad oficial: {unit}" if unit else "Unidad no especificada en metadatos."
        if not unit:
            warnings.append("Alerta de sesgo: La unidad de medida oficial no está definida.")
        elif any(k in unit.lower() for k in ["miles de", "millones", "porcentaje", "índice", "indice"]):
            scale_note += " (Atención al factor de escala al interpretar o modelar)."

        # 5. Projection cutoff detection
        base_year_split = None
        is_projection = False
        text_context = " ".join([
            str(meta.get("data_features", "")),
            str(meta.get("comments", "")),
            str(meta.get("calculation_methodology", "")),
        ])
        match_base = re.search(r"año base.*?(\d{4})", text_context, re.IGNORECASE)
        if match_base:
            base_year_split = int(match_base.group(1))
            if max_year and max_year > base_year_split:
                is_projection = True
                warnings.append(
                    f"Advertencia metodológica: Los datos posteriores al año base {base_year_split} son proyecciones."
                )

        quality = DataQualityReport(
            total_records=total_records,
            null_count=null_count,
            null_ratio=null_ratio,
            has_gaps=has_gaps,
            min_year=min_year,
            max_year=max_year,
            min_value=min_val,
            max_value=max_val,
        )

        antibias = AntiBiasChecklist(
            unit_verified=bool(unit),
            scale_factor_note=scale_note,
            is_projection=is_projection,
            base_year_split=base_year_split,
            warnings=warnings,
        )

        return quality, antibias
