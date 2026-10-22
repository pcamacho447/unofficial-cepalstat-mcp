"""Data and records extractor for CEPALSTAT indicators."""

from typing import Any

import pandas as pd

from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.dimensions import DimensionManager


class DataExtractor:
    """Extracts indicator metadata and records as dictionaries or DataFrames."""

    def __init__(
        self,
        client: CepalStatClient,
        dimension_manager: DimensionManager | None = None,
    ) -> None:
        self.client = client
        self.dimension_manager = dimension_manager or DimensionManager(client)

    def get_metadata(self, indicator_id: int) -> dict[str, Any]:
        """Fetch metadata for an indicator.

        Args:
            indicator_id: ID of the indicator.

        Returns:
            Dictionary containing indicator metadata (e.g. name, unit, description).
        """
        response = self.client.get(f"/cepalstat/api/v1/indicator/{indicator_id}/metadata")
        body = response.get("body") or {}
        if isinstance(body, dict):
            metadata = body.get("metadata")
            if isinstance(metadata, dict):
                return metadata
        return {}

    def get_records(
        self, indicator_id: int, members: list[int] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch raw records for an indicator.

        Args:
            indicator_id: ID of the indicator.
            members: Optional list of numeric member IDs to filter data by.

        Returns:
            A list of dictionary records representing indicator observations.
        """
        params: dict[str, Any] = {}
        if members:
            params["members"] = ",".join(str(m) for m in members)

        response = self.client.get(f"/cepalstat/api/v1/indicator/{indicator_id}/records", params=params)
        body = response.get("body") or {}
        if isinstance(body, dict):
            data = body.get("data")
            if isinstance(data, list):
                return data
        return []

    def get_dataframe(
        self,
        indicator_id: int,
        members: list[int] | None = None,
        decode_labels: bool = True,
    ) -> pd.DataFrame:
        """Fetch indicator records converted into a clean Pandas DataFrame.

        Args:
            indicator_id: ID of the indicator.
            members: Optional list of numeric member IDs to filter data by.
            decode_labels: If True, resolves dimension columns (e.g. dim_208) into
                their human-readable dimension name and member label (e.g. País__ESTANDAR = 'Chile').

        Returns:
            A pandas DataFrame with observation records.
        """
        records = self.get_records(indicator_id, members=members)
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        # Convert numeric values to float where possible
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

        if decode_labels:
            dimensions = self.dimension_manager.get_dimensions(indicator_id)
            for dim in dimensions:
                dim_col = f"dim_{dim.id}"
                if dim_col in df.columns:
                    member_map: dict[Any, str] = {}
                    for m in dim.members:
                        member_map[m.id] = m.name
                        member_map[str(m.id)] = m.name
                    df[dim.name] = df[dim_col].map(member_map).fillna(df[dim_col])
                    df = df.drop(columns=[dim_col])

        return df
