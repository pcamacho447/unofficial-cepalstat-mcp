"""Dimension and Member resolution for CEPALSTAT indicators."""

from typing import Any
from pydantic import BaseModel
from statscepal.client import CepalStatClient


class Member(BaseModel):
    """A member element inside a dimension (e.g. Chile, 2020, Ambos sexos)."""

    id: int
    name: str
    order: int | None = None
    parent: int | None = None
    selected: int | None = None


class Dimension(BaseModel):
    """A dimension of an indicator (e.g. País, Años, Sexo)."""

    id: int
    name: str
    members: list[Member] = []


class DimensionManager:
    """Retrieves and searches dimensions and member IDs for indicators."""

    def __init__(self, client: CepalStatClient) -> None:
        self.client = client
        self._cache: dict[int, list[Dimension]] = {}

    def get_dimensions(self, indicator_id: int, force_refresh: bool = False) -> list[Dimension]:
        """Fetch all dimensions and members for an indicator.

        Args:
            indicator_id: ID of the indicator.
            force_refresh: If True, bypass the internal cache and refetch from API.

        Returns:
            A list of Dimension objects, each containing its Member objects.
        """
        if indicator_id in self._cache and not force_refresh:
            return self._cache[indicator_id]

        response = self.client.get(f"/cepalstat/api/v1/indicator/{indicator_id}/dimensions")
        body = response.get("body") or {}
        raw_dims = body.get("dimensions", []) if isinstance(body, dict) else []

        dimensions: list[Dimension] = []
        if isinstance(raw_dims, list):
            for raw_dim in raw_dims:
                if not isinstance(raw_dim, dict):
                    continue
                members = [
                    Member(
                        id=int(m["id"]),
                        name=str(m.get("name", "")),
                        order=m.get("order"),
                        parent=m.get("parent"),
                        selected=m.get("selected"),
                    )
                    for m in raw_dim.get("members", [])
                    if isinstance(m, dict) and "id" in m
                ]
                dimensions.append(
                    Dimension(
                        id=int(raw_dim["id"]),
                        name=str(raw_dim.get("name", "")),
                        members=members,
                    )
                )

        self._cache[indicator_id] = dimensions
        return dimensions

    def find_member_id(
        self,
        indicator_id: int,
        dimension_name_or_id: str | int,
        member_name: str,
    ) -> int | None:
        """Find numeric member ID by partial or exact matching.

        Args:
            indicator_id: ID of the indicator.
            dimension_name_or_id: Dimension name (case-insensitive partial match) or integer dimension ID.
            member_name: Member name to match (exact or substring).

        Returns:
            The integer member ID if found, or None.
        """
        dims = self.get_dimensions(indicator_id)
        target_dim: Dimension | None = None

        if isinstance(dimension_name_or_id, int):
            for d in dims:
                if d.id == dimension_name_or_id:
                    target_dim = d
                    break
        else:
            dim_q = str(dimension_name_or_id).lower()
            for d in dims:
                if dim_q in d.name.lower():
                    target_dim = d
                    break

        if not target_dim:
            return None

        mem_q = str(member_name).lower().strip()

        # Exact match first
        for m in target_dim.members:
            if m.name.lower().strip() == mem_q:
                return m.id

        # Fallback to substring match
        for m in target_dim.members:
            if mem_q in m.name.lower():
                return m.id

        return None
