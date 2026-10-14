"""CEPALSTAT Thematic Tree navigation and indicator search."""

from typing import Any
from pydantic import BaseModel
from statscepal.client import CepalStatClient


class IndicatorItem(BaseModel):
    """An indicator discovered in the thematic tree."""

    indicator_id: int
    name: str
    order: int | None = None
    path: str = ""


class ThematicTree:
    """Manages downloading, traversing, and searching the thematic tree."""

    def __init__(self, client: CepalStatClient) -> None:
        self.client = client
        self._raw_tree: dict[str, Any] | None = None
        self._indicators: list[IndicatorItem] | None = None

    def get_raw_tree(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch the raw thematic tree JSON.

        Args:
            force_refresh: If True, bypass the internal cache and refetch from API.

        Returns:
            The body dictionary of the thematic tree API response.
        """
        if self._raw_tree is None or force_refresh:
            data = self.client.get("/cepalstat/api/v1/thematic-tree")
            self._raw_tree = data.get("body", {})
        return self._raw_tree

    def list_all_indicators(self, force_refresh: bool = False) -> list[IndicatorItem]:
        """Recursively collect all indicators present in the tree.

        Args:
            force_refresh: If True, refetch the raw tree and re-traverse indicators.

        Returns:
            A list of all IndicatorItem objects found in the tree.
        """
        if self._indicators is not None and not force_refresh:
            return self._indicators

        root = self.get_raw_tree(force_refresh=force_refresh)
        items: list[IndicatorItem] = []

        if not isinstance(root, dict):
            self._indicators = items
            return self._indicators

        def traverse(node: dict[str, Any], current_path: list[str]) -> None:
            name = node.get("name", "")
            new_path = current_path + [name] if name else current_path

            if "indicator_id" in node:
                items.append(
                    IndicatorItem(
                        indicator_id=int(node["indicator_id"]),
                        name=name,
                        order=node.get("order"),
                        path=" > ".join(current_path),
                    )
                )

            children = node.get("children")
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, dict):
                        traverse(child, new_path)

        traverse(root, [])
        self._indicators = items
        return self._indicators

    def search(self, query: str) -> list[IndicatorItem]:
        """Search indicators by name or topic path (case-insensitive).

        Args:
            query: Keyword to match against indicator name or path.

        Returns:
            List of matching IndicatorItem objects.
        """
        q = query.lower()
        all_inds = self.list_all_indicators()
        return [ind for ind in all_inds if q in ind.name.lower() or q in ind.path.lower()]
