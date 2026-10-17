"""Empirical data fetcher for resolved CEPALSTAT semantic queries."""

from typing import Any
import unicodedata
import pandas as pd

from statscepal.client import CepalStatClient
from statscepal.extractor import DataExtractor
from statscepal.semantic.models import ResolutionStatus, SemanticResolutionResponse


def _strip_accents(text: str) -> str:
    """Normalize text by converting to lowercase, stripping whitespace and combining accents."""
    normalized = unicodedata.normalize("NFD", str(text).lower().strip())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


class SemanticDataFetcher:
    """Bridges resolved semantic queries to concrete CEPALSTAT data extraction."""

    _STRUCTURAL_AND_META_COLS: frozenset[str] = frozenset({
        "value",
        "source_id",
        "notes_ids",
        "notes",
        "notas",
        "notes_id",
        "iso3",
        "country",
        "country_code",
        "country_name",
        "pais",
        "país",
        "pais__estandar",
        "país__estandar",
        "year",
        "ano",
        "anio",
        "anios",
        "anos",
        "anios__estandar",
        "anos__estandar",
        "period",
        "periodo",
        "record_id",
        "indicator_id",
        "id_indicador",
        "indicador",
        "unit",
        "unidad",
    })

    _AGGREGATE_MEMBER_PRIORITY: tuple[str, ...] = (
        "total",
        "ambos sexos",
        "jefe ambos sexos",
        "nacional",
        "total nacional",
        "total pais",
        "total del pais",
        "total pobreza",
        "pobreza",
        "indice general",
        "general",
        "todas las edades",
    )

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

    def _load_indicator_data(
        self, indicator_id: int, member_ids: list[int] | None = None
    ) -> pd.DataFrame | None:
        """Load indicator dataframe using available extractor method."""
        df: pd.DataFrame | None = None
        if hasattr(self.extractor, "fetch_indicator_dataframe"):
            df = self.extractor.fetch_indicator_dataframe(  # type: ignore[attr-defined]
                indicator_id, members=member_ids or None
            )
            if (df is None or df.empty) and member_ids:
                df = self.extractor.fetch_indicator_dataframe(indicator_id, members=None)  # type: ignore[attr-defined]
        else:
            df = self.extractor.get_dataframe(indicator_id, members=member_ids or None)
            if (df is None or df.empty) and member_ids:
                df = self.extractor.get_dataframe(indicator_id, members=None)
        return df

    def _filter_unconstrained_dimensions(
        self,
        df: pd.DataFrame,
        filtered_dim_cols: set[str],
        country_col: str | None,
        year_col: str | None,
    ) -> pd.DataFrame:
        """Collapse any non-structural DataFrame dimension column not in filtered_dim_cols to its aggregate member."""
        if df.empty:
            return df
        result = df
        norm_filtered_cols = {_strip_accents(c).lower() for c in filtered_dim_cols}
        norm_country_col = _strip_accents(country_col).lower() if country_col else None
        norm_year_col = _strip_accents(year_col).lower() if year_col else None

        for col in list(result.columns):
            if (
                col in filtered_dim_cols
                or col == country_col
                or col == year_col
            ):
                continue
            cl = _strip_accents(col).lower()
            if (
                cl in norm_filtered_cols
                or cl == norm_country_col
                or cl == norm_year_col
                or cl in self._STRUCTURAL_AND_META_COLS
            ):
                continue
            unique_vals = result[col].dropna().astype(str).str.strip().unique()
            if len(unique_vals) <= 1:
                continue
            norm_to_raw = {_strip_accents(v).lower(): v for v in unique_vals}
            chosen_raw: str | None = None
            for agg_pat in self._AGGREGATE_MEMBER_PRIORITY:
                if agg_pat in norm_to_raw:
                    chosen_raw = norm_to_raw[agg_pat]
                    break
            if chosen_raw is not None:
                chosen_norm = _strip_accents(chosen_raw).lower()
                result = result[
                    result[col].astype(str).str.strip().map(lambda s: _strip_accents(s).lower())
                    == chosen_norm
                ]
        return result


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
        member_ids: list[int] = []
        for f in response.applied_filters.dimensions:
            if getattr(f, "is_breakdown", False) and getattr(f, "member_ids", None):
                member_ids.extend(f.member_ids)
            elif f.member_id is not None:
                member_ids.append(f.member_id)

        df = self._load_indicator_data(indicator_id, member_ids)

        time_mode = getattr(response.applied_filters, "time_mode", "SINGLE")
        target_years = getattr(response.applied_filters, "years", []) or []
        target_year = response.applied_filters.year
        relative_window_size = getattr(
            response.applied_filters, "relative_window_size", None
        )
        is_multi_year = (
            time_mode in ("LIST", "RANGE", "RELATIVE_WINDOW")
            or len(target_years) > 1
        )
        has_breakdown = any(
            getattr(d, "is_breakdown", False)
            for d in response.applied_filters.dimensions
        )

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
            if is_multi_year:
                payload["series"] = []
            response.empirical_data = payload
            return payload

        filtered_df = df.copy()

        # 1. Filter by country if specified
        target_country_names = list(
            getattr(response.applied_filters, "country_names", [])
            or ([response.applied_filters.country_name] if response.applied_filters.country_name else [])
        )
        target_country_codes = list(
            getattr(response.applied_filters, "country_codes", [])
            or ([response.applied_filters.country_code] if response.applied_filters.country_code else [])
        )
        is_multi_country = len(target_country_codes) > 1 or len(target_country_names) > 1
        country_col = None
        if target_country_names or target_country_codes:
            for candidate in (
                "país__estandar",
                "pais__estandar",
                "country_name",
                "country",
                "país",
                "pais",
            ):
                for col in filtered_df.columns:
                    if col.lower() == candidate:
                        country_col = col
                        break
                if country_col is not None:
                    break

            if country_col is None:
                for candidate in ("iso3", "country_code"):
                    for col in filtered_df.columns:
                        if col.lower() == candidate:
                            country_col = col
                            break
                    if country_col is not None:
                        break

            if country_col is None:
                for col in filtered_df.columns:
                    cl = col.lower()
                    if "pais" in cl or "país" in cl or "country" in cl:
                        country_col = col
                        break

            if country_col is not None:
                mask = pd.Series(False, index=filtered_df.index)
                col_str = filtered_df[country_col].astype(str).str.strip()
                if target_country_names:
                    col_norm = col_str.map(_strip_accents)
                    for t_name in target_country_names:
                        norm_target_name = _strip_accents(t_name)
                        mask |= (col_norm == norm_target_name)
                if target_country_codes:
                    col_upper = col_str.str.upper()
                    for t_code in target_country_codes:
                        mask |= (col_upper == t_code.strip().upper())
                filtered_df = filtered_df[mask]

        # Build country lookup for mapping names and codes to standardized codes
        code_by_name: dict[str, str] = {}
        for c, n in zip(target_country_codes, target_country_names):
            if c and n:
                code_by_name[_strip_accents(n).lower()] = c.upper()
                code_by_name[n.lower()] = c.upper()
        if response.applied_filters.country_code and response.applied_filters.country_name:
            code_by_name[_strip_accents(response.applied_filters.country_name).lower()] = response.applied_filters.country_code.upper()
            code_by_name[response.applied_filters.country_name.lower()] = response.applied_filters.country_code.upper()

        country_anchor_map: dict[str, dict[int, list[int]]] = {}
        if response.temporal_info:
            if getattr(response.temporal_info, "country_anchors", None):
                for c_code, ca in response.temporal_info.country_anchors.items():
                    c_key = c_code.upper()
                    country_anchor_map[c_key] = {}
                    if ca.country_name:
                        code_by_name[_strip_accents(ca.country_name).lower()] = c_key
                        code_by_name[ca.country_name.lower()] = c_key
                    unobs = list(ca.unobserved_years) if ca.unobserved_years else (
                        [response.temporal_info.requested_year] if response.temporal_info.requested_year else []
                    )
                    if ca.previous_anchor_year is not None:
                        country_anchor_map[c_key][ca.previous_anchor_year] = unobs
                    if ca.next_anchor_year is not None:
                        country_anchor_map[c_key][ca.next_anchor_year] = unobs
            elif (
                response.temporal_info.previous_anchor_year is not None
                or response.temporal_info.next_anchor_year is not None
            ):
                primary_code = (response.applied_filters.country_code or "").upper()
                if primary_code:
                    country_anchor_map[primary_code] = {}
                    unobs = list(response.temporal_info.unobserved_years) if response.temporal_info.unobserved_years else (
                        [response.temporal_info.requested_year] if response.temporal_info.requested_year else []
                    )
                    if response.temporal_info.previous_anchor_year is not None:
                        country_anchor_map[primary_code][response.temporal_info.previous_anchor_year] = unobs
                    if response.temporal_info.next_anchor_year is not None:
                        country_anchor_map[primary_code][response.temporal_info.next_anchor_year] = unobs

        def _get_row_country_code(row: pd.Series) -> str | None:
            if country_col is not None and country_col in row and not pd.isna(row[country_col]):
                c_val = str(row[country_col]).strip()
                if c_val.upper() in country_anchor_map:
                    return c_val.upper()
                c_norm = _strip_accents(c_val).lower()
                if c_norm in code_by_name:
                    return code_by_name[c_norm]
                if c_val.lower() in code_by_name:
                    return code_by_name[c_val.lower()]
                for target_code in target_country_codes:
                    if c_val.upper() == target_code.strip().upper():
                        return target_code.strip().upper()
            if len(country_anchor_map) == 1:
                return next(iter(country_anchor_map.keys()))
            if response.applied_filters.country_code:
                return response.applied_filters.country_code.upper()
            return None

        # 2. Filter by resolved dimensions if specified
        filtered_dim_cols: set[str] = set()
        if response.applied_filters.dimensions and not filtered_df.empty:
            for dim_filter in response.applied_filters.dimensions:
                dim_col = None
                for col in filtered_df.columns:
                    cl = col.lower()
                    dl = dim_filter.dim_name.lower()
                    if (
                        cl == dl
                        or cl.replace("__estandar", "") == dl.replace("__estandar", "")
                        or _strip_accents(cl).replace("__estandar", "")
                        == _strip_accents(dl).replace("__estandar", "")
                    ):
                        dim_col = col
                        break
                if dim_col is None and dim_filter.dim_id is not None:
                    if f"dim_{dim_filter.dim_id}" in filtered_df.columns:
                        dim_col = f"dim_{dim_filter.dim_id}"

                if dim_col is not None:
                    filtered_dim_cols.add(dim_col)
                    dim_mask = pd.Series(False, index=filtered_df.index)
                    candidate_names = (
                        list(dim_filter.member_names)
                        if getattr(dim_filter, "is_breakdown", False) and getattr(dim_filter, "member_names", None)
                        else ([dim_filter.member_name] if dim_filter.member_name else [])
                    )
                    candidate_ids = (
                        list(dim_filter.member_ids)
                        if getattr(dim_filter, "is_breakdown", False) and getattr(dim_filter, "member_ids", None)
                        else ([dim_filter.member_id] if dim_filter.member_id is not None else [])
                    )
                    for m_name in candidate_names:
                        dim_mask |= (
                            filtered_df[dim_col]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            == m_name.strip().lower()
                        )
                        dim_mask |= (
                            filtered_df[dim_col]
                            .astype(str)
                            .str.strip()
                            .map(_strip_accents)
                            == _strip_accents(m_name.strip())
                        )
                    for m_id in candidate_ids:
                        dim_mask |= (
                            filtered_df[dim_col].astype(str).str.strip()
                            == str(m_id)
                        )
                    filtered_df = filtered_df[dim_mask]

        # 3. Identify year column
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

        filtered_df = self._filter_unconstrained_dimensions(
            filtered_df, filtered_dim_cols, country_col, year_col
        )

        has_rescued_anchors = False
        requested_year_set: set[int] = (
            set(target_years)
            if target_years
            else ({target_year} if target_year is not None else set())
        )

        # 4. Filter by temporal constraints
        if not filtered_df.empty and year_col is not None:
            if time_mode == "RELATIVE_WINDOW":
                window_size = relative_window_size or 5
                val_df = filtered_df
                if "value" in val_df.columns:
                    val_num = pd.to_numeric(val_df["value"], errors="coerce")
                    valid_rows = val_df[val_num.notna()]
                    if not valid_rows.empty:
                        val_df = valid_rows

                num_years = (
                    pd.to_numeric(val_df[year_col], errors="coerce")
                    .dropna()
                    .astype(int)
                )
                unique_years = sorted(num_years.unique())
                if unique_years:
                    selected_years = (
                        unique_years[-window_size:]
                        if len(unique_years) > window_size
                        else unique_years
                    )
                    col_years = pd.to_numeric(filtered_df[year_col], errors="coerce")
                    filtered_df = filtered_df[col_years.isin(selected_years)]
            elif country_anchor_map:
                col_years = pd.to_numeric(filtered_df[year_col], errors="coerce")
                normal_mask = col_years.isin(requested_year_set)

                anchor_indices = []
                for idx, row in filtered_df.iterrows():
                    ry_raw = row.get(year_col)
                    try:
                        ry_val = int(float(str(ry_raw).split()[0]))
                    except (ValueError, TypeError):
                        continue

                    row_c_code = _get_row_country_code(row)
                    if row_c_code and row_c_code in country_anchor_map:
                        if ry_val in country_anchor_map[row_c_code]:
                            anchor_indices.append(idx)

                if anchor_indices:
                    has_rescued_anchors = True
                    mask = normal_mask | filtered_df.index.isin(anchor_indices)
                    filtered_df = filtered_df[mask]
                else:
                    filtered_df = filtered_df[normal_mask]
            elif target_years:
                col_years = pd.to_numeric(filtered_df[year_col], errors="coerce")
                filtered_df = filtered_df[col_years.isin(target_years)]
            elif target_year is not None:
                col_years = pd.to_numeric(filtered_df[year_col], errors="coerce")
                filtered_df = filtered_df[col_years == target_year]
            elif (
                target_year is None
                and not target_years
                and time_mode == "SINGLE"
                and (is_multi_country or has_breakdown)
            ):
                val_df = filtered_df
                if "value" in val_df.columns:
                    val_num = pd.to_numeric(val_df["value"], errors="coerce")
                    valid_rows = val_df[val_num.notna()]
                    if not valid_rows.empty:
                        val_df = valid_rows
                col_years = pd.to_numeric(val_df[year_col], errors="coerce")
                if not col_years.dropna().empty:
                    if (
                        is_multi_country
                        and country_col is not None
                        and country_col in val_df.columns
                    ):
                        max_years_by_country = (
                            val_df.assign(_num_year=col_years)
                            .groupby(country_col)["_num_year"]
                            .transform("max")
                        )
                        keep_indices = val_df.index[col_years == max_years_by_country]
                        filtered_df = filtered_df.loc[filtered_df.index.isin(keep_indices)]
                    else:
                        max_y = col_years.max()
                        if pd.notna(max_y):
                            all_years = pd.to_numeric(filtered_df[year_col], errors="coerce")
                            filtered_df = filtered_df[all_years == max_y]

        # 5. Format observation result
        if not filtered_df.empty:
            if is_multi_year or has_breakdown or is_multi_country or has_rescued_anchors:
                if year_col is not None and year_col in filtered_df.columns:
                    sorted_df = filtered_df.assign(
                        _sort_year=pd.to_numeric(
                            filtered_df[year_col], errors="coerce"
                        ).fillna(0)
                    ).sort_values(by="_sort_year", ascending=True).drop(
                        columns=["_sort_year"]
                    )
                else:
                    sorted_df = filtered_df

                breakdown_cols: list[str] = []
                for dim_filter in response.applied_filters.dimensions:
                    if not getattr(dim_filter, "is_breakdown", False):
                        continue
                    for col in sorted_df.columns:
                        cl = col.lower()
                        dl = dim_filter.dim_name.lower()
                        if cl == dl or cl.replace("__estandar", "") == dl.replace("__estandar", ""):
                            breakdown_cols.append(col)
                            break
                        if dim_filter.dim_id is not None and col == f"dim_{dim_filter.dim_id}":
                            breakdown_cols.append(col)
                            break

                series: list[dict[str, Any]] = []
                for _, row in sorted_df.iterrows():
                    val_raw = row.get("value")
                    try:
                        val = float(val_raw)
                    except (ValueError, TypeError):
                        val = None

                    if val is None or pd.isna(val_raw):
                        continue

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

                    row_notes = ""
                    for n_col in ("notes_ids", "notes", "notas", "notes_id"):
                        if n_col in row and not pd.isna(row[n_col]):
                            row_notes = str(row[n_col])
                            break

                    item_dict: dict[str, Any] = {
                        "year": row_year,
                        "value": val,
                        "unit": response.selected_candidate.unit,
                        "notes": row_notes,
                    }
                    if is_multi_country and country_col is not None and country_col in row and not pd.isna(row[country_col]):
                        item_dict["country"] = str(row[country_col]).strip()
                    if breakdown_cols:
                        member_parts = [
                            str(row[bc]).strip()
                            for bc in breakdown_cols
                            if bc in row and not pd.isna(row[bc])
                        ]
                        if member_parts:
                            item_dict["member"] = " / ".join(member_parts)

                    # Check if this row is a rescued anchor
                    row_c_code = _get_row_country_code(row)
                    is_anchor_row = False
                    anchor_unobs_years: list[int] = []
                    if (
                        country_anchor_map
                        and row_c_code
                        and row_c_code in country_anchor_map
                        and row_year not in requested_year_set
                    ):
                        if row_year in country_anchor_map[row_c_code]:
                            is_anchor_row = True
                            anchor_unobs_years = country_anchor_map[row_c_code][row_year]

                    if is_anchor_row:
                        item_dict["is_anchor"] = True
                        item_dict["anchor_for_years"] = anchor_unobs_years
                        anchor_tag = f"[Ancla oficial para {', '.join(str(y) for y in anchor_unobs_years)}]"
                        item_dict["notes"] = f"{row_notes} {anchor_tag}".strip()
                    else:
                        item_dict["is_anchor"] = False

                    series.append(item_dict)

                if not series:
                    payload = {
                        "observation_exists": False,
                        "indicator_id": indicator_id,
                        "indicator_name": response.selected_candidate.name,
                        "unit": response.selected_candidate.unit,
                        "country": response.applied_filters.country_name
                        or response.applied_filters.country_code,
                        "year": response.applied_filters.year,
                        "reason": "No observation available for the specified filters/period",
                        "series": [],
                    }
                else:
                    latest_item = series[-1]
                    payload = {
                        "observation_exists": True,
                        "indicator_id": indicator_id,
                        "indicator_name": response.selected_candidate.name,
                        "value": latest_item["value"],
                        "unit": response.selected_candidate.unit,
                        "country": response.applied_filters.country_name
                        or response.applied_filters.country_code,
                        "year": latest_item["year"],
                        "dimensions_applied": [
                            f.model_dump() for f in response.applied_filters.dimensions
                        ],
                        "notes": latest_item["notes"],
                        "series": series,
                    }
            else:
                if target_year is None and year_col is not None:
                    valid_df = (
                        filtered_df.dropna(subset=["value"])
                        if "value" in filtered_df.columns
                        else filtered_df
                    )
                    if not valid_df.empty:
                        numeric_y = pd.to_numeric(
                            valid_df[year_col], errors="coerce"
                        ).fillna(0)
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
            if is_multi_year or has_rescued_anchors:
                payload["series"] = []

        response.empirical_data = payload
        if payload.get("observation_exists"):
            response.execution_trace.append(
                f"[Stage 6: Empirical Extraction] Observation found: {payload['value']} {payload.get('unit', '')} for {payload.get('country')} ({payload.get('year')})"
            )
            if has_rescued_anchors:
                response.execution_trace.append(
                    "[Stage 6: Empirical Extraction] Rescued official anchor observations for unobserved survey periods."
                )
        else:
            response.execution_trace.append(
                f"[Stage 6: Empirical Extraction] Observation unavailable: {payload.get('reason')}"
            )
        return payload

