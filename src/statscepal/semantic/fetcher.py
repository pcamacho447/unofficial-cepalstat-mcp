"""Empirical data fetcher for resolved CEPALSTAT semantic queries."""

from typing import Any
import pandas as pd

from statscepal.client import CepalStatClient
from statscepal.extractor import DataExtractor
from statscepal.semantic.models import ResolutionStatus, SemanticResolutionResponse


class SemanticDataFetcher:
    """Bridges resolved semantic queries to concrete CEPALSTAT data extraction."""

    def __init__(
        self,
        extractor: DataExtractor | None = None,
        client: CepalStatClient | None = None,
    ) -> None:
        if extractor is not None:
            self.extractor = extractor
            self.client = client or getattr(extractor, "client", None)
        else:
            self.client = client or CepalStatClient()
            self.extractor = DataExtractor(client=self.client)

    def fetch_resolved_data(
        self, response: SemanticResolutionResponse
    ) -> dict[str, Any]:
        """Fetch and filter concrete observation data for a resolved query response.

        Args:
            response: A SemanticResolutionResponse with resolved indicator and filters.

        Returns:
            Dictionary payload with observation data and provenance.
        """
        if (
            response.status
            not in (
                ResolutionStatus.RESOLVED,
                ResolutionStatus.RESOLVED_WITH_ANCHORS,
            )
            or not response.selected_candidate
        ):
            payload = {
                "observation_exists": False,
                "reason": "Query not resolved or abstained",
            }
            response.empirical_data = payload
            return payload

        indicator_id = response.selected_candidate.indicator_id
        member_ids = [
            f.member_id
            for f in response.applied_filters.dimensions
            if f.member_id is not None
        ]

        if hasattr(self.extractor, "fetch_indicator_dataframe"):
            df = self.extractor.fetch_indicator_dataframe(  # type: ignore[attr-defined]
                indicator_id, members=member_ids or None
            )
        else:
            df = self.extractor.get_dataframe(indicator_id, members=member_ids or None)

        if df is None or df.empty:
            payload = {
                "observation_exists": False,
                "indicator_id": indicator_id,
                "indicator_name": response.selected_candidate.name,
                "unit": response.selected_candidate.unit,
                "country": response.applied_filters.country_name
                or response.applied_filters.country_code,
                "year": response.applied_filters.year,
                "reason": "No observation available for the specified filters/period",
            }
            response.empirical_data = payload
            return payload

        filtered_df = df.copy()

        # 1. Filter by country if specified
        target_country_name = response.applied_filters.country_name
        target_country_code = response.applied_filters.country_code
        if target_country_name or target_country_code:
            country_col = None
            for col in filtered_df.columns:
                cl = col.lower()
                if cl in (
                    "country",
                    "country_name",
                    "país__estandar",
                    "pais__estandar",
                    "país",
                    "pais",
                    "iso3",
                    "country_code",
                ):
                    country_col = col
                    break
            if country_col is None:
                for col in filtered_df.columns:
                    cl = col.lower()
                    if "pais" in cl or "país" in cl or "country" in cl:
                        country_col = col
                        break

            if country_col is not None:
                mask = pd.Series(False, index=filtered_df.index)
                if target_country_name:
                    mask |= (
                        filtered_df[country_col]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        == target_country_name.strip().lower()
                    )
                if target_country_code:
                    mask |= (
                        filtered_df[country_col]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        == target_country_code.strip().upper()
                    )
                filtered_df = filtered_df[mask]

        # 2. Identify year column and filter by year if specified
        year_col = None
        for col in filtered_df.columns:
            cl = col.lower().replace("ñ", "n")
            if cl in (
                "year",
                "ano",
                "anio",
                "anios__estandar",
                "anos__estandar",
                "period",
                "periodo",
                "anios",
                "anos",
            ):
                year_col = col
                break
        if year_col is None:
            for col in filtered_df.columns:
                cl = col.lower().replace("ñ", "n")
                if "year" in cl or "anio" in cl or "ano" in cl or "period" in cl:
                    year_col = col
                    break

        target_year = response.applied_filters.year
        if target_year is not None and not filtered_df.empty:
            if year_col is not None:
                numeric_years = pd.to_numeric(filtered_df[year_col], errors="coerce")
                filtered_df = filtered_df[numeric_years == target_year]

        # 3. Filter by resolved dimensions if specified
        if response.applied_filters.dimensions and not filtered_df.empty:
            for dim_filter in response.applied_filters.dimensions:
                dim_col = None
                for col in filtered_df.columns:
                    cl = col.lower()
                    dl = dim_filter.dim_name.lower()
                    if cl == dl or cl.replace("__estandar", "") == dl.replace(
                        "__estandar", ""
                    ):
                        dim_col = col
                        break
                if dim_col is None and dim_filter.dim_id is not None:
                    if f"dim_{dim_filter.dim_id}" in filtered_df.columns:
                        dim_col = f"dim_{dim_filter.dim_id}"

                if dim_col is not None:
                    dim_mask = pd.Series(False, index=filtered_df.index)
                    if dim_filter.member_name:
                        dim_mask |= (
                            filtered_df[dim_col]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            == dim_filter.member_name.strip().lower()
                        )
                    if dim_filter.member_id is not None:
                        dim_mask |= (
                            filtered_df[dim_col].astype(str).str.strip()
                            == str(dim_filter.member_id)
                        )
                    filtered_df = filtered_df[dim_mask]

        # 4. Format observation result
        if not filtered_df.empty:
            if target_year is None and year_col is not None:
                valid_df = filtered_df.dropna(subset=["value"])
                if not valid_df.empty:
                    numeric_y = pd.to_numeric(valid_df[year_col], errors="coerce").fillna(0)
                    sorted_order = numeric_y.argsort()
                    row = valid_df.iloc[sorted_order.iloc[-1]]
                else:
                    row = filtered_df.iloc[-1]
            else:
                row = filtered_df.iloc[0]

            val_raw = row.get("value")
            try:
                val = float(val_raw)
            except (ValueError, TypeError):
                val = None

            if val is None or pd.isna(val_raw):
                payload = {
                    "observation_exists": False,
                    "indicator_id": indicator_id,
                    "indicator_name": response.selected_candidate.name,
                    "unit": response.selected_candidate.unit,
                    "country": response.applied_filters.country_name
                    or response.applied_filters.country_code,
                    "year": response.applied_filters.year,
                    "reason": "No observation available for the specified filters/period",
                }
            else:
                row_year = None
                if year_col is not None and year_col in row and not pd.isna(row[year_col]):
                    try:
                        row_year = int(float(str(row[year_col]).split()[0]))
                    except (ValueError, TypeError):
                        pass
                if row_year is None:
                    for c in row.index:
                        cl = str(c).lower().replace("ñ", "n")
                        if any(k in cl for k in ("year", "anio", "ano", "period")):
                            try:
                                row_year = int(float(str(row[c]).split()[0]))
                                break
                            except (ValueError, TypeError):
                                pass
                if row_year is None:
                    row_year = int(response.applied_filters.year or 0)

                notes_val = ""
                for n_col in ("notes_ids", "notes", "notas", "notes_id"):
                    if n_col in row and not pd.isna(row[n_col]):
                        notes_val = str(row[n_col])
                        break

                payload = {
                    "observation_exists": True,
                    "indicator_id": indicator_id,
                    "indicator_name": response.selected_candidate.name,
                    "value": val,
                    "unit": response.selected_candidate.unit,
                    "country": response.applied_filters.country_name
                    or response.applied_filters.country_code,
                    "year": row_year,
                    "dimensions_applied": [
                        f.model_dump() for f in response.applied_filters.dimensions
                    ],
                    "notes": notes_val,
                }
        else:
            payload = {
                "observation_exists": False,
                "indicator_id": indicator_id,
                "indicator_name": response.selected_candidate.name,
                "unit": response.selected_candidate.unit,
                "country": response.applied_filters.country_name
                or response.applied_filters.country_code,
                "year": response.applied_filters.year,
                "reason": "No observation available for the specified filters/period",
            }

        response.empirical_data = payload
        if payload.get("observation_exists"):
            response.execution_trace.append(
                f"[Stage 6: Empirical Extraction] Observation found: {payload['value']} {payload.get('unit', '')} for {payload.get('country')} ({payload.get('year')})"
            )
        else:
            response.execution_trace.append(
                f"[Stage 6: Empirical Extraction] Observation unavailable: {payload.get('reason')}"
            )
        return payload
