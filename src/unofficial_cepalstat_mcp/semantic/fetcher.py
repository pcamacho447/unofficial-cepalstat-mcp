"""Empirical data fetcher for resolved CEPALSTAT semantic queries."""

import re
import unicodedata
from typing import Any

import pandas as pd

from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.extractor import DataExtractor
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus, SemanticResolutionResponse
from unofficial_cepalstat_mcp.semantic.registry import (
    EMPIRICAL_INDICATOR_ID_MAP,
    SYNTHETIC_DIMENSION_MEMBER_IDS,
)

DIM_NAME_ALIASES: dict[str, list[str]] = {
    "estrato de ingreso": [
        "quintil",
        "decil",
        "estrato",
        "quintiles",
        "deciles",
        "estratos",
        "estrato de ingresos",
    ],
}

MEMBER_VALUE_ALIASES: dict[str, list[str]] = {
    "primer quintil": ["quintil 1", "i", "quintil i", "1", "q1", "i quintil"],
    "segundo quintil": ["quintil 2", "ii", "quintil ii", "2", "q2", "ii quintil"],
    "tercer quintil": ["quintil 3", "iii", "quintil iii", "3", "q3", "iii quintil"],
    "cuarto quintil": ["quintil 4", "iv", "quintil iv", "4", "q4", "iv quintil"],
    "quinto quintil": ["quintil 5", "v", "quintil v", "5", "q5", "v quintil"],
    "primer decil": ["decil 1", "i", "decil i", "1", "d1", "i decil"],
    "segundo decil": ["decil 2", "ii", "decil ii", "2", "d2", "ii decil"],
    "tercer decil": ["decil 3", "iii", "decil iii", "3", "d3", "iii decil"],
    "cuarto decil": ["decil 4", "iv", "decil iv", "4", "d4", "iv decil"],
    "quinto decil": ["decil 5", "v", "decil v", "5", "d5", "v decil"],
    "sexto decil": ["decil 6", "vi", "decil vi", "6", "d6", "vi decil"],
    "septimo decil": ["decil 7", "vii", "decil vii", "7", "d7", "vii decil"],
    "octavo decil": ["decil 8", "viii", "decil viii", "8", "d8", "viii decil"],
    "noveno decil": ["decil 9", "ix", "decil ix", "9", "d9", "ix decil"],
    "decimo decil": ["decil 10", "x", "decil x", "10", "d10", "x decil"],
}


def _strip_accents(text: str) -> str:
    """Normalize text by converting to lowercase, stripping whitespace and combining accents."""
    normalized = unicodedata.normalize("NFD", str(text).lower().strip())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def _normalize_member_text(text: str) -> str:
    """Normalize member name or value for robust matching."""
    return _strip_accents(str(text)).lower().strip()


def _get_acceptable_member_forms(member_name: str) -> set[str]:
    """Return all normalized acceptable aliases and representations for a member name."""
    norm_m = _normalize_member_text(member_name)
    acceptable = {norm_m}
    if norm_m in MEMBER_VALUE_ALIASES:
        for alias in MEMBER_VALUE_ALIASES[norm_m]:
            acceptable.add(_normalize_member_text(alias))
    for canonical, aliases in MEMBER_VALUE_ALIASES.items():
        norm_aliases = {_normalize_member_text(a) for a in aliases}
        if norm_m in norm_aliases:
            acceptable.add(_normalize_member_text(canonical))
            acceptable |= norm_aliases
    return acceptable


def _match_dim_column(col_name: str, target_name: str) -> bool:
    """Check if a DataFrame column name matches a target dimension name, ignoring case, accents, and __estandar."""
    cl = _strip_accents(col_name).lower().strip().replace("__estandar", "")
    dl = _strip_accents(target_name).lower().strip().replace("__estandar", "")
    if cl == dl or cl.replace(" ", "") == dl.replace(" ", ""):
        return True
    aliases_dl = DIM_NAME_ALIASES.get(dl, [])
    if cl in aliases_dl or cl.replace(" ", "") in [a.replace(" ", "") for a in aliases_dl]:
        return True
    aliases_cl = DIM_NAME_ALIASES.get(cl, [])
    if dl in aliases_cl or dl.replace(" ", "") in [a.replace(" ", "") for a in aliases_cl]:
        return True
    return False




def _extract_numeric_years(series: pd.Series) -> pd.Series:
    """Convert a year or decade Series (e.g., 2020 or 'Década 2010') into numeric years."""
    num = pd.to_numeric(series, errors="coerce")
    if num.notna().any():
        if num.isna().any():
            extracted = series.astype(str).str.extract(r"(1\d{3}|20\d{2})", expand=False)
            return num.combine_first(pd.to_numeric(extracted, errors="coerce"))
        return num
    extracted = series.astype(str).str.extract(r"(1\d{3}|20\d{2})", expand=False)
    return pd.to_numeric(extracted, errors="coerce")


def _extract_single_year(val: Any) -> int | None:
    """Extract an integer year from a scalar value, string or decade text (e.g., 'Década 2010' -> 2010)."""
    if val is None or pd.isna(val):
        return None
    try:
        return int(float(str(val).split()[0]))
    except (ValueError, TypeError):
        pass
    match = re.search(r"(1\d{3}|20\d{2})", str(val))
    if match:
        return int(match.group(1))
    return None


class SemanticDataFetcher:
    """Bridges resolved semantic queries to concrete CEPALSTAT data extraction."""

    _extract_numeric_years = staticmethod(_extract_numeric_years)
    _extract_single_year = staticmethod(_extract_single_year)

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
        "decada",
        "década",
        "países_agregados regionales especiales var ipc",
        "paises_agregados regionales especiales var ipc",
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
        "total quintiles",
        "total deciles",
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
            if hasattr(self.client, "get_dataframe") and not isinstance(self.client, CepalStatClient):
                self.extractor = self.client  # type: ignore[assignment]
            else:
                self.extractor = DataExtractor(client=self.client)

    def _load_indicator_data(
        self, indicator_id: int, member_ids: list[int] | None = None
    ) -> pd.DataFrame | None:
        """Load indicator dataframe using available extractor method."""
        df: pd.DataFrame | None = None
        if hasattr(self.extractor, "get_dataframe"):
            res = self.extractor.get_dataframe(indicator_id, members=member_ids or None)
            if isinstance(res, pd.DataFrame):
                df = res
                if df.empty and member_ids:
                    fallback_df = self.extractor.get_dataframe(indicator_id, members=None)
                    if isinstance(fallback_df, pd.DataFrame):
                        df = fallback_df
        if (df is None or not isinstance(df, pd.DataFrame)) and hasattr(
            self.extractor, "fetch_indicator_dataframe"
        ):
            res = self.extractor.fetch_indicator_dataframe(  # type: ignore[attr-defined]
                indicator_id, members=member_ids or None
            )
            if isinstance(res, pd.DataFrame):
                df = res
                if df.empty and member_ids:
                    fallback_df = self.extractor.fetch_indicator_dataframe(  # type: ignore[attr-defined]
                        indicator_id, members=None
                    )
                    if isinstance(fallback_df, pd.DataFrame):
                        df = fallback_df
        return df if isinstance(df, pd.DataFrame) else None

    def _filter_unconstrained_dimensions(
        self,
        df: pd.DataFrame,
        filtered_dim_cols: set[str],
        country_col: str | None,
        year_col: str | None,
        response: SemanticResolutionResponse | None = None,
        breakdown_facets: set[str] | None = None,
    ) -> pd.DataFrame:
        """Collapse any non-structural DataFrame dimension column not in filtered_dim_cols to its aggregate member."""
        if df.empty:
            return df
        result = df
        norm_filtered_cols = {_strip_accents(c).lower() for c in filtered_dim_cols}
        norm_country_col = _strip_accents(country_col).lower() if country_col else None
        norm_year_col = _strip_accents(year_col).lower() if year_col else None

        facet_keys_in_breakdown: set[str] = set()
        if response is not None and getattr(response, "applied_filters", None):
            facet_keys_in_breakdown = {
                f_k.lower()
                for f_k, f_v in getattr(response.applied_filters, "facets", {}).items()
                if "_DESGLOSE" in str(f_v) or str(f_v) in ("ETNICO_TOTAL", "ETNICO")
            }
        if breakdown_facets is not None:
            facet_keys_in_breakdown |= {bk.lower() for bk in breakdown_facets}

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
            if any(bk in cl for bk in facet_keys_in_breakdown):
                # User explicitly requested breakdown for this dimension -> DO NOT collapse to aggregate!
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


    def _resolve_empirical_indicator_id(
        self, response: SemanticResolutionResponse
    ) -> int:
        """Map synthetic vertical-slice indicator IDs to verified real CEPALSTAT indicator IDs."""
        assert response.selected_candidate is not None
        ind_id = response.selected_candidate.indicator_id
        if ind_id == 3340:
            estrato = response.applied_filters.facets.get("estrato", "")
            if estrato == "RELACION_Q5_Q1":
                return 3295
            if "QUINTIL" in estrato:
                return 3324
            return 3390
        return EMPIRICAL_INDICATOR_ID_MAP.get(ind_id, ind_id)

    def _get_row_country_code(
        self,
        row: pd.Series,
        country_col: str | None,
        country_anchor_map: dict[str, Any],
        code_by_name: dict[str, str],
        target_country_codes: list[str] | None = None,
        target_country_names: list[str] | None = None,
        default_country_code: str | None = None,
    ) -> str | None:
        """Resolve country code for a specific DataFrame row using ISO columns and country lexicon."""
        target_codes = target_country_codes or []
        target_names = target_country_names or []
        for iso_col in ("iso3", "country_code"):
            if iso_col in row and not pd.isna(row[iso_col]):
                iso_val = str(row[iso_col]).strip().upper()
                if iso_val in country_anchor_map:
                    return iso_val
                if iso_val.lower() in code_by_name:
                    return code_by_name[iso_val.lower()]
                for target_code in target_codes:
                    if iso_val == target_code.strip().upper():
                        return target_code.strip().upper()
        if country_col is not None and country_col in row and not pd.isna(row[country_col]):
            c_val = str(row[country_col]).strip()
            if c_val.upper() in country_anchor_map:
                return c_val.upper()
            c_norm = _strip_accents(c_val).lower()
            if c_norm in code_by_name:
                return code_by_name[c_norm]
            if c_val.lower() in code_by_name:
                return code_by_name[c_val.lower()]
            for target_code, target_name in zip(target_codes, target_names):
                norm_t_name = _strip_accents(target_name).lower()
                if c_norm == norm_t_name or c_norm.startswith(norm_t_name + " ("):
                    return target_code.strip().upper()
            for target_code in target_codes:
                if c_val.upper() == target_code.strip().upper():
                    return target_code.strip().upper()
        if len(country_anchor_map) == 1:
            return next(iter(country_anchor_map.keys()))
        if default_country_code:
            return default_country_code.upper()
        return None

    def _prepare_empirical_fetch(
        self, response: SemanticResolutionResponse
    ) -> tuple[int, pd.DataFrame]:
        """Resolve empirical indicator ID and fetch raw DataFrame with non-synthetic member IDs."""
        assert response.selected_candidate is not None
        empirical_id = self._resolve_empirical_indicator_id(response)
        raw_member_ids: list[int] = []
        for f in response.applied_filters.dimensions:
            if getattr(f, "is_breakdown", False) and getattr(f, "member_ids", None):
                raw_member_ids.extend(f.member_ids)
            elif f.member_id is not None:
                raw_member_ids.append(f.member_id)

        member_ids = [
            m for m in raw_member_ids if m not in SYNTHETIC_DIMENSION_MEMBER_IDS
        ]
        df = self._load_indicator_data(empirical_id, member_ids)
        if df is None:
            return empirical_id, pd.DataFrame()
        df = df.copy()
        if "value" not in df.columns:
            for val_cand in ("valor", "val", "monto", "dato"):
                for c in df.columns:
                    if _strip_accents(c).lower() == val_cand:
                        df["value"] = df[c]
                        break
                if "value" in df.columns:
                    break
        return empirical_id, df

    def _resolve_geography(
        self, df: pd.DataFrame, response: SemanticResolutionResponse
    ) -> tuple[str | None, list[str], list[str], bool, dict[str, str], dict[str, Any]]:
        """Identify country columns, target countries, code mappings, and anchor configurations."""
        target_country_names = list(
            getattr(response.applied_filters, "country_names", [])
            or ([response.applied_filters.country_name] if response.applied_filters.country_name else [])
        )
        target_country_codes = list(
            getattr(response.applied_filters, "country_codes", [])
            or ([response.applied_filters.country_code] if response.applied_filters.country_code else [])
        )
        is_multi_country = len(target_country_codes) > 1 or len(target_country_names) > 1
        country_col: str | None = None

        if target_country_names or target_country_codes:
            for candidate in (
                "país__estandar",
                "pais__estandar",
                "country_name",
                "country",
                "país",
                "pais",
            ):
                for col in df.columns:
                    if col.lower() == candidate or _strip_accents(col).lower() == candidate:
                        country_col = col
                        break
                if country_col is not None:
                    break

            if country_col is None:
                for col in df.columns:
                    cl = col.lower()
                    if ("pais" in cl or "país" in cl or "country" in cl) and not any(
                        s in cl for s in ("iso3", "code", "codigo", "código")
                    ):
                        country_col = col
                        break

            if country_col is None:
                for candidate in ("iso3", "country_code"):
                    for col in df.columns:
                        if col.lower() == candidate:
                            country_col = col
                            break
                    if country_col is not None:
                        break

        code_by_name: dict[str, str] = {}
        for c, n in zip(target_country_codes, target_country_names):
            if c and n:
                code_by_name[_strip_accents(n).lower()] = c.upper()
                code_by_name[n.lower()] = c.upper()
        if response.applied_filters.country_code and response.applied_filters.country_name:
            code_by_name[_strip_accents(response.applied_filters.country_name).lower()] = response.applied_filters.country_code.upper()
            code_by_name[response.applied_filters.country_name.lower()] = response.applied_filters.country_code.upper()
        for c in target_country_codes:
            if c:
                code_by_name[c.strip().lower()] = c.strip().upper()
                code_by_name[c.strip().upper()] = c.strip().upper()
        if response.applied_filters.country_code:
            cc = response.applied_filters.country_code.strip().upper()
            code_by_name[cc.lower()] = cc
            code_by_name[cc] = cc
        if country_col is not None and country_col in df.columns:
            for c_val in df[country_col].dropna().unique():
                c_str = str(c_val).strip()
                c_norm = _strip_accents(c_str).lower()
                for target_code, target_name in zip(target_country_codes, target_country_names):
                    norm_t_name = _strip_accents(target_name).lower()
                    if c_norm == norm_t_name or c_norm.startswith(norm_t_name + " ("):
                        code_by_name[c_norm] = target_code.strip().upper()
                        code_by_name[c_str.lower()] = target_code.strip().upper()

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

        return (
            country_col,
            target_country_names,
            target_country_codes,
            is_multi_country,
            code_by_name,
            country_anchor_map,
        )

    def _filter_geography(
        self,
        df: pd.DataFrame,
        country_col: str | None,
        target_country_names: list[str],
        target_country_codes: list[str],
    ) -> pd.DataFrame:
        """Filter DataFrame rows to requested country targets."""
        if df.empty or (not target_country_names and not target_country_codes):
            return df

        mask = pd.Series(False, index=df.index)
        if country_col is not None:
            col_str = df[country_col].astype(str).str.strip()
            if target_country_names:
                col_norm = col_str.map(_strip_accents)
                for t_name in target_country_names:
                    norm_target_name = _strip_accents(t_name)
                    mask |= (col_norm == norm_target_name) | col_norm.str.startswith(norm_target_name + " (")
            if target_country_codes:
                col_upper = col_str.str.upper()
                for t_code in target_country_codes:
                    mask |= (col_upper == t_code.strip().upper())
        for iso_cand in ("iso3", "country_code"):
            if iso_cand in df.columns and target_country_codes:
                iso_upper = df[iso_cand].astype(str).str.strip().str.upper()
                for t_code in target_country_codes:
                    mask |= (iso_upper == t_code.strip().upper())
        if country_col is not None or any(c in df.columns for c in ("iso3", "country_code")):
            return df[mask]
        return df

    def _apply_dimension_filters(
        self, df: pd.DataFrame, response: SemanticResolutionResponse
    ) -> tuple[pd.DataFrame, set[str]]:
        """Filter DataFrame rows by resolved dimensions using aliases and acceptable forms."""
        filtered_df = df
        filtered_dim_cols: set[str] = set()
        if response.applied_filters.dimensions and not filtered_df.empty:
            for dim_filter in response.applied_filters.dimensions:
                dim_col = None
                for col in filtered_df.columns:
                    if _match_dim_column(col, dim_filter.dim_name):
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
                    if not candidate_names and not candidate_ids:
                        if getattr(dim_filter, "is_breakdown", False):
                            dim_mask = pd.Series(True, index=filtered_df.index)
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
                        acceptable_forms = _get_acceptable_member_forms(m_name)
                        dim_mask |= (
                            filtered_df[dim_col]
                            .astype(str)
                            .str.strip()
                            .map(_normalize_member_text)
                            .isin(acceptable_forms)
                        )
                    for m_id in candidate_ids:
                        dim_mask |= (
                            filtered_df[dim_col].astype(str).str.strip()
                            == str(m_id)
                        )
                    filtered_df = filtered_df[dim_mask]
        return filtered_df, filtered_dim_cols

    def _apply_temporal_and_anchors(
        self,
        df: pd.DataFrame,
        response: SemanticResolutionResponse,
        country_col: str | None,
        filtered_dim_cols: set[str],
        country_anchor_map: dict[str, Any],
        is_multi_country: bool,
        code_by_name: dict[str, str],
    ) -> tuple[pd.DataFrame, str | None, bool, list[int]]:
        """Identify year column, collapse unconstrained dimensions, discover dynamic anchors, and filter temporal range."""
        filtered_df = df
        year_col = None
        for col in filtered_df.columns:
            cl = _strip_accents(col).lower().replace("ñ", "n")
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
                "decada",
            ):
                year_col = col
                break
        if year_col is None:
            for col in filtered_df.columns:
                cl = _strip_accents(col).lower().replace("ñ", "n")
                if any(
                    k in cl
                    for k in ("year", "anio", "ano", "period", "decada")
                ):
                    year_col = col
                    break

        facet_keys_in_breakdown = {
            f_k.lower()
            for f_k, f_v in getattr(response.applied_filters, "facets", {}).items()
            if "_DESGLOSE" in str(f_v) or str(f_v) in ("ETNICO_TOTAL", "ETNICO")
        }
        filtered_df = self._filter_unconstrained_dimensions(
            filtered_df,
            filtered_dim_cols,
            country_col,
            year_col,
            response=response,
            breakdown_facets=facet_keys_in_breakdown,
        )

        has_rescued_anchors = False
        target_years = getattr(response.applied_filters, "years", []) or []
        target_year = response.applied_filters.year
        requested_year_set: set[int] = (
            set(target_years)
            if target_years
            else ({target_year} if target_year is not None else set())
        )

        target_country_names = list(
            getattr(response.applied_filters, "country_names", [])
            or ([response.applied_filters.country_name] if response.applied_filters.country_name else [])
        )
        target_country_codes = list(
            getattr(response.applied_filters, "country_codes", [])
            or ([response.applied_filters.country_code] if response.applied_filters.country_code else [])
        )

        # Dynamic empirical anchor discovery
        if requested_year_set and not filtered_df.empty and year_col is not None:
            candidate_countries: list[str] = []
            if target_country_codes:
                candidate_countries = [c.strip().upper() for c in target_country_codes if c]
            elif response.applied_filters.country_code:
                candidate_countries = [response.applied_filters.country_code.strip().upper()]
            elif response.applied_filters.country_name:
                norm_name = _strip_accents(response.applied_filters.country_name).lower()
                if norm_name in code_by_name:
                    candidate_countries = [code_by_name[norm_name]]

            for c_code in candidate_countries:
                if c_code in country_anchor_map and country_anchor_map[c_code]:
                    continue

                if is_multi_country:
                    country_rows = [
                        idx for idx, row in filtered_df.iterrows()
                        if self._get_row_country_code(
                            row,
                            country_col,
                            country_anchor_map,
                            code_by_name,
                            target_country_codes,
                            target_country_names,
                            response.applied_filters.country_code,
                        ) == c_code
                    ]
                    country_df = filtered_df.loc[country_rows]
                else:
                    country_df = filtered_df

                if country_df.empty:
                    continue

                val_df = country_df
                if "value" in val_df.columns:
                    val_num = pd.to_numeric(val_df["value"], errors="coerce")
                    valid_rows = val_df[val_num.notna()]
                    if not valid_rows.empty:
                        val_df = valid_rows

                num_years = (
                    _extract_numeric_years(val_df[year_col])
                    .dropna()
                    .astype(int)
                )
                avail_years = set(num_years.unique())
                missing_requested = requested_year_set - avail_years

                if missing_requested and avail_years:
                    for req_y in sorted(missing_requested):
                        prev_anchor = max((y for y in avail_years if y < req_y), default=None)
                        next_anchor = min((y for y in avail_years if y > req_y), default=None)
                        if prev_anchor is not None or next_anchor is not None:
                            if c_code not in country_anchor_map:
                                country_anchor_map[c_code] = {}
                            if prev_anchor is not None:
                                country_anchor_map[c_code].setdefault(prev_anchor, [])
                                if req_y not in country_anchor_map[c_code][prev_anchor]:
                                    country_anchor_map[c_code][prev_anchor].append(req_y)
                            if next_anchor is not None:
                                country_anchor_map[c_code].setdefault(next_anchor, [])
                                if req_y not in country_anchor_map[c_code][next_anchor]:
                                    country_anchor_map[c_code][next_anchor].append(req_y)

                            if country_col is not None and country_col in country_df.columns:
                                for c_val in country_df[country_col].dropna().unique():
                                    c_str = str(c_val).strip()
                                    code_by_name[_strip_accents(c_str).lower()] = c_code
                                    code_by_name[c_str.lower()] = c_code
                            has_rescued_anchors = True

        # Filter by temporal constraints
        time_mode = getattr(response.applied_filters, "time_mode", "SINGLE")
        relative_window_size = getattr(
            response.applied_filters, "relative_window_size", None
        )
        has_breakdown = any(
            getattr(d, "is_breakdown", False)
            for d in response.applied_filters.dimensions
        ) or bool(facet_keys_in_breakdown)

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
                    _extract_numeric_years(val_df[year_col])
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
                    col_years = _extract_numeric_years(filtered_df[year_col])
                    filtered_df = filtered_df[col_years.isin(selected_years)]
            elif country_anchor_map:
                col_years = _extract_numeric_years(filtered_df[year_col])
                normal_mask = col_years.isin(requested_year_set)

                anchor_indices = []
                for idx, row in filtered_df.iterrows():
                    ry_val = _extract_single_year(row.get(year_col))
                    if ry_val is None:
                        continue

                    row_c_code = self._get_row_country_code(
                        row,
                        country_col,
                        country_anchor_map,
                        code_by_name,
                        target_country_codes,
                        target_country_names,
                        response.applied_filters.country_code,
                    )
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
                col_years = _extract_numeric_years(filtered_df[year_col])
                filtered_df = filtered_df[col_years.isin(target_years)]
            elif target_year is not None:
                col_years = _extract_numeric_years(filtered_df[year_col])
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
                col_years = _extract_numeric_years(val_df[year_col])
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
                            all_years = _extract_numeric_years(filtered_df[year_col])
                            filtered_df = filtered_df[all_years == max_y]

        if has_rescued_anchors and response.status == ResolutionStatus.RESOLVED:
            response.status = ResolutionStatus.RESOLVED_WITH_ANCHORS

        return filtered_df, year_col, has_rescued_anchors, sorted(requested_year_set)

    def _format_payload(
        self,
        df: pd.DataFrame,
        response: SemanticResolutionResponse,
        empirical_id: int,
        year_col: str | None,
        country_col: str | None,
        is_multi_country: bool,
        is_multi_year: bool,
        has_breakdown: bool,
        has_rescued_anchors: bool,
        country_anchor_map: dict[str, Any],
        requested_year_set: set[int],
        code_by_name: dict[str, str],
        target_year: int | None,
        filtered_dim_cols: set[str] | None = None,
    ) -> dict[str, Any]:
        """Format series items and observation metadata into structured empirical payload."""
        filtered_df = df
        dim_cols = filtered_dim_cols or set()
        target_country_names = list(
            getattr(response.applied_filters, "country_names", [])
            or ([response.applied_filters.country_name] if response.applied_filters.country_name else [])
        )
        target_country_codes = list(
            getattr(response.applied_filters, "country_codes", [])
            or ([response.applied_filters.country_code] if response.applied_filters.country_code else [])
        )
        facet_keys_in_breakdown = {
            f_k.lower()
            for f_k, f_v in getattr(response.applied_filters, "facets", {}).items()
            if "_DESGLOSE" in str(f_v) or str(f_v) in ("ETNICO_TOTAL", "ETNICO")
        }

        if not filtered_df.empty:
            if is_multi_year or has_breakdown or is_multi_country or has_rescued_anchors:
                if year_col is not None and year_col in filtered_df.columns:
                    sorted_df = filtered_df.assign(
                        _sort_year=_extract_numeric_years(
                            filtered_df[year_col]
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
                        if _match_dim_column(col, dim_filter.dim_name):
                            breakdown_cols.append(col)
                            break
                        if dim_filter.dim_id is not None and col == f"dim_{dim_filter.dim_id}":
                            breakdown_cols.append(col)
                            break

                for col in sorted_df.columns:
                    if col in breakdown_cols or col == country_col or col == year_col:
                        continue
                    cl = _strip_accents(col).lower()
                    if cl in self._STRUCTURAL_AND_META_COLS:
                        continue
                    if any(bk in cl for bk in facet_keys_in_breakdown):
                        breakdown_cols.append(col)

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
                        row_year = _extract_single_year(row[year_col])
                    if row_year is None:
                        for c in row.index:
                            cl = _strip_accents(str(c)).lower().replace("ñ", "n")
                            if any(k in cl for k in ("year", "anio", "ano", "period", "decada")):
                                row_year = _extract_single_year(row[c])
                                if row_year is not None:
                                    break
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
                    row_c_code = self._get_row_country_code(
                        row,
                        country_col,
                        country_anchor_map,
                        code_by_name,
                        target_country_codes,
                        target_country_names,
                        response.applied_filters.country_code,
                    )
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
                        "indicator_id": empirical_id,
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
                        "indicator_id": empirical_id,
                        "indicator_name": response.selected_candidate.name,
                        "value": latest_item["value"],
                        "unit": response.selected_candidate.unit,
                        "country": latest_item.get(
                            "country",
                            response.applied_filters.country_name
                            or response.applied_filters.country_code,
                        ),
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
                        numeric_y = _extract_numeric_years(
                            valid_df[year_col]
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
                        "indicator_id": empirical_id,
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
                        row_year = _extract_single_year(row[year_col])
                    if row_year is None:
                        for c in row.index:
                            cl = _strip_accents(str(c)).lower().replace("ñ", "n")
                            if any(k in cl for k in ("year", "anio", "ano", "period", "decada")):
                                row_year = _extract_single_year(row[c])
                                if row_year is not None:
                                    break
                    if row_year is None:
                        row_year = int(response.applied_filters.year or 0)

                    notes_val = ""
                    for n_col in ("notes_ids", "notes", "notas", "notes_id"):
                        if n_col in row and not pd.isna(row[n_col]):
                            notes_val = str(row[n_col])
                            break

                    single_item: dict[str, Any] = {
                        "year": row_year,
                        "value": val,
                        "unit": response.selected_candidate.unit,
                        "notes": notes_val,
                    }
                    if dim_cols:
                        m_parts = [
                            str(row[dc]).strip()
                            for dc in dim_cols
                            if dc in row and not pd.isna(row[dc])
                        ]
                        if m_parts:
                            single_item["member"] = " / ".join(m_parts)

                    payload = {
                        "observation_exists": True,
                        "indicator_id": empirical_id,
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
                        "series": [single_item],
                    }
        else:
            payload = {
                "observation_exists": False,
                "indicator_id": empirical_id,
                "indicator_name": response.selected_candidate.name,
                "unit": response.selected_candidate.unit,
                "country": response.applied_filters.country_name
                or response.applied_filters.country_code,
                "year": response.applied_filters.year,
                "reason": "No observation available for the specified filters/period",
            }
            if is_multi_year or has_rescued_anchors:
                payload["series"] = []

        return payload

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

        time_mode = getattr(response.applied_filters, "time_mode", "SINGLE")
        target_years = getattr(response.applied_filters, "years", []) or []
        target_year = response.applied_filters.year
        is_multi_year = (
            time_mode in ("LIST", "RANGE", "RELATIVE_WINDOW")
            or len(target_years) > 1
        )
        facet_keys_in_breakdown = {
            f_k.lower()
            for f_k, f_v in getattr(response.applied_filters, "facets", {}).items()
            if "_DESGLOSE" in str(f_v) or str(f_v) in ("ETNICO_TOTAL", "ETNICO")
        }
        has_breakdown = any(
            getattr(d, "is_breakdown", False)
            for d in response.applied_filters.dimensions
        ) or bool(facet_keys_in_breakdown)

        empirical_id, df = self._prepare_empirical_fetch(response)

        if df is None or df.empty:
            payload = {
                "observation_exists": False,
                "indicator_id": empirical_id,
                "empirical_indicator_id": empirical_id,
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

        country_col, target_names, target_codes, is_multi_country, code_by_name, country_anchor_map = (
            self._resolve_geography(df, response)
        )
        df = self._filter_geography(df, country_col, target_names, target_codes)
        df, filtered_dim_cols = self._apply_dimension_filters(df, response)
        df, year_col, has_rescued_anchors, requested_years = (
            self._apply_temporal_and_anchors(
                df,
                response,
                country_col,
                filtered_dim_cols,
                country_anchor_map,
                is_multi_country,
                code_by_name,
            )
        )
        payload = self._format_payload(
            df=df,
            response=response,
            empirical_id=empirical_id,
            year_col=year_col,
            country_col=country_col,
            is_multi_country=is_multi_country,
            is_multi_year=is_multi_year,
            has_breakdown=has_breakdown,
            has_rescued_anchors=has_rescued_anchors,
            country_anchor_map=country_anchor_map,
            requested_year_set=set(requested_years),
            code_by_name=code_by_name,
            target_year=target_year,
            filtered_dim_cols=filtered_dim_cols,
        )

        payload["empirical_indicator_id"] = empirical_id
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

