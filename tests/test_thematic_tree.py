import pytest
import respx
import httpx
from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.thematic_tree import ThematicTree, IndicatorItem


MOCK_TREE_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "name": "Clasificación temática general",
        "theme_id": 27,
        "children": [
            {
                "name": "Demográficos y sociales",
                "area_id": 394,
                "children": [
                    {
                        "name": "Demográficos",
                        "area_id": 395,
                        "children": [
                            {
                                "name": "Población total, según sexo",
                                "order": 10,
                                "indicator_id": 4788,
                            },
                            {
                                "name": "Tasa de crecimiento anual",
                                "order": 50,
                                "indicator_id": 4795,
                            },
                        ],
                    },
                    {
                        "name": "Educación",
                        "area_id": 396,
                        "children": [
                            {
                                "name": "Tasa de alfabetización",
                                "order": 20,
                                "indicator_id": 4800,
                            }
                        ],
                    },
                ],
            },
            {
                "name": "Económicos",
                "area_id": 400,
                "children": [
                    {
                        "name": "PIB anual a precios constantes",
                        "order": 1,
                        "indicator_id": 1234,
                    }
                ],
            },
        ],
    },
    "footer": {"records": 1},
}


@respx.mock
def test_get_raw_tree_and_caching():
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree").mock(
        return_value=httpx.Response(200, json=MOCK_TREE_PAYLOAD)
    )

    client = CepalStatClient()
    tree = ThematicTree(client)

    raw_tree = tree.get_raw_tree()
    assert route.call_count == 1
    assert raw_tree["name"] == "Clasificación temática general"
    assert raw_tree["theme_id"] == 27

    # Second call uses cache
    raw_tree_cached = tree.get_raw_tree()
    assert route.call_count == 1
    assert raw_tree_cached == raw_tree

    # Force refresh makes another network call
    raw_tree_refreshed = tree.get_raw_tree(force_refresh=True)
    assert route.call_count == 2
    assert raw_tree_refreshed == raw_tree


@respx.mock
def test_list_all_indicators_recursive_and_path():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree").mock(
        return_value=httpx.Response(200, json=MOCK_TREE_PAYLOAD)
    )

    client = CepalStatClient()
    tree = ThematicTree(client)

    indicators = tree.list_all_indicators()
    assert len(indicators) == 4

    item_4788 = next(ind for ind in indicators if ind.indicator_id == 4788)
    assert item_4788.name == "Población total, según sexo"
    assert item_4788.order == 10
    assert (
        item_4788.path
        == "Clasificación temática general > Demográficos y sociales > Demográficos"
    )

    item_1234 = next(ind for ind in indicators if ind.indicator_id == 1234)
    assert item_1234.name == "PIB anual a precios constantes"
    assert item_1234.order == 1
    assert item_1234.path == "Clasificación temática general > Económicos"


@respx.mock
def test_search_indicators_case_insensitive_and_path():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree").mock(
        return_value=httpx.Response(200, json=MOCK_TREE_PAYLOAD)
    )

    client = CepalStatClient()
    tree = ThematicTree(client)

    # Search by indicator name (case-insensitive)
    results_name = tree.search("POBLACIÓN")
    assert len(results_name) == 1
    assert results_name[0].indicator_id == 4788

    # Search by path (case-insensitive)
    results_path = tree.search("educación")
    assert len(results_path) == 1
    assert results_path[0].indicator_id == 4800
    assert "Educación" in results_path[0].path

    # Search common word matching multiple
    results_multiple = tree.search("tasa")
    assert len(results_multiple) == 2
    assert {r.indicator_id for r in results_multiple} == {4795, 4800}

    # Search non-matching term
    results_empty = tree.search("inexistente")
    assert results_empty == []
