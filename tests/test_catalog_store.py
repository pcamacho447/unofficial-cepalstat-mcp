from pathlib import Path

import httpx
import pandas as pd
import respx

from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.client import CepalStatClient

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
                                "name": "Tasa anual de crecimiento",
                                "order": 50,
                                "indicator_id": 4795,
                            },
                        ],
                    }
                ],
            },
            {
                "name": "Económicos",
                "area_id": 414,
                "children": [
                    {
                        "name": "PIB y Cuentas Nacionales",
                        "area_id": 415,
                        "children": [
                            {
                                "name": "PIB Anual a precios constantes",
                                "order": 100,
                                "indicator_id": 415,
                            }
                        ],
                    }
                ],
            },
        ],
    },
}


def test_catalog_store_initial_state(tmp_path: Path):
    db_path = tmp_path / "test_catalog.db"
    store = CatalogStore(db_path=db_path)
    assert not store.is_built()
    stats = store.get_stats()
    assert stats.total_indicators == 0
    assert stats.themes_count == 0
    assert stats.by_theme == {}


@respx.mock
def test_catalog_store_build_and_search(tmp_path: Path):
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree").mock(
        return_value=httpx.Response(200, json=MOCK_TREE_PAYLOAD)
    )

    db_path = tmp_path / "test_catalog.db"
    client = CepalStatClient()
    store = CatalogStore(db_path=db_path, client=client)

    assert not store.is_built()
    count = store.build()
    assert count == 3
    assert store.is_built()

    # Search by keyword (case and accent insensitive)
    results = store.search("poblacion")
    assert len(results) == 1
    assert results[0].indicator_id == 4788
    assert results[0].theme == "Demográficos y sociales"
    assert results[0].area == "Demográficos"
    assert results[0].full_path == "Demográficos y sociales > Demográficos"

    # Search with theme filter
    econ_results = store.search("PIB", theme="Económicos")
    assert len(econ_results) == 1
    assert econ_results[0].indicator_id == 415
    assert econ_results[0].theme == "Económicos"

    # Search with non-matching theme filter
    empty_econ = store.search("Población", theme="Económicos")
    assert len(empty_econ) == 0

    # Search by area
    area_results = store.search("Cuentas Nacionales")
    assert len(area_results) == 1
    assert area_results[0].indicator_id == 415

    # Get stats
    stats = store.get_stats()
    assert stats.total_indicators == 3
    assert stats.themes_count == 2
    assert stats.areas_count == 2
    assert stats.by_theme["Demográficos y sociales"] == 2
    assert stats.by_theme["Económicos"] == 1

    # Export to JSON
    out_json = tmp_path / "export.json"
    store.export(out_json, format="json")
    assert out_json.exists()
    df_json = pd.read_json(out_json)
    assert len(df_json) == 3

    # Export to CSV
    out_csv = tmp_path / "export.csv"
    store.export(out_csv, format="csv")
    assert out_csv.exists()
    df_csv = pd.read_csv(out_csv)
    assert len(df_csv) == 3


@respx.mock
def test_catalog_store_build_force_and_caching(tmp_path: Path):
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree").mock(
        return_value=httpx.Response(200, json=MOCK_TREE_PAYLOAD)
    )

    db_path = tmp_path / "test_catalog.db"
    client = CepalStatClient()
    store = CatalogStore(db_path=db_path, client=client)

    # Initial build makes network call
    count = store.build()
    assert count == 3
    assert route.call_count == 1

    # Second build without force should not make network call
    count_cached = store.build()
    assert count_cached == 3
    assert route.call_count == 1

    # Third build with force=True should refetch
    count_forced = store.build(force=True)
    assert count_forced == 3
    assert route.call_count == 2


@respx.mock
def test_catalog_store_search_limits_and_empty(tmp_path: Path):
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree").mock(
        return_value=httpx.Response(200, json=MOCK_TREE_PAYLOAD)
    )

    db_path = tmp_path / "test_catalog.db"
    store = CatalogStore(db_path=db_path)
    store.build()

    # Limit parameter
    results_limit_1 = store.search("", limit=1)
    assert len(results_limit_1) == 1

    # Empty search query returns all up to limit
    results_all = store.search("", limit=10)
    assert len(results_all) == 3

    # Query with no match
    results_none = store.search("no_such_indicator")
    assert len(results_none) == 0
