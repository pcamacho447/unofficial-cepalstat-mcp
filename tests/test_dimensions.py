import pytest
import respx
import httpx
from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.dimensions import Dimension, DimensionManager, Member


MOCK_DIMENSIONS_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "dimensions": [
            {
                "id": 208,
                "name": "País__ESTANDAR",
                "members": [
                    {"id": 224, "name": "Chile", "order": 110, "parent": None, "selected": 0},
                    {"id": 218, "name": "Argentina", "order": 10, "parent": None, "selected": 0},
                    {"id": 215, "name": "América Latina y el Caribe", "order": 1, "parent": None, "selected": 0},
                ],
            },
            {
                "id": 29117,
                "name": "Años__ESTANDAR",
                "members": [
                    {"id": 29190, "name": "2020", "order": 2020},
                    {"id": 29191, "name": "2021", "order": 2021},
                ],
            },
            {
                "id": 300,
                "name": "Sexo",
                "members": [
                    {"id": 301, "name": "Hombres", "order": 1},
                    {"id": 302, "name": "Mujeres", "order": 2},
                    {"id": 303, "name": "Total", "order": 0},
                ],
            },
        ]
    },
    "footer": {"records": 3},
}


@respx.mock
def test_get_dimensions_and_caching():
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/dimensions").mock(
        return_value=httpx.Response(200, json=MOCK_DIMENSIONS_PAYLOAD)
    )

    client = CepalStatClient()
    manager = DimensionManager(client)

    dims = manager.get_dimensions(4788)
    assert route.call_count == 1
    assert len(dims) == 3

    assert isinstance(dims[0], Dimension)
    assert dims[0].id == 208
    assert dims[0].name == "País__ESTANDAR"
    assert len(dims[0].members) == 3
    assert isinstance(dims[0].members[0], Member)
    assert dims[0].members[0].id == 224
    assert dims[0].members[0].name == "Chile"

    # Second call uses cache
    cached_dims = manager.get_dimensions(4788)
    assert route.call_count == 1
    assert cached_dims == dims

    # Force refresh makes another network call
    refreshed_dims = manager.get_dimensions(4788, force_refresh=True)
    assert route.call_count == 2
    assert len(refreshed_dims) == 3


@respx.mock
def test_find_member_id_by_dimension_name_and_id():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/dimensions").mock(
        return_value=httpx.Response(200, json=MOCK_DIMENSIONS_PAYLOAD)
    )

    client = CepalStatClient()
    manager = DimensionManager(client)

    # By partial / case-insensitive dimension name
    chile_id = manager.find_member_id(4788, "País", "Chile")
    assert chile_id == 224

    chile_case_id = manager.find_member_id(4788, "país", "chile")
    assert chile_case_id == 224

    argentina_id = manager.find_member_id(4788, "País__ESTANDAR", "Argentina")
    assert argentina_id == 218

    # Partial substring matching for member name
    alc_id = manager.find_member_id(4788, "país", "Latina")
    assert alc_id == 215

    # By dimension ID
    year_id = manager.find_member_id(4788, 29117, "2020")
    assert year_id == 29190

    mujer_id = manager.find_member_id(4788, 300, "Mujeres")
    assert mujer_id == 302


@respx.mock
def test_find_member_id_fallback_and_not_found():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/dimensions").mock(
        return_value=httpx.Response(200, json=MOCK_DIMENSIONS_PAYLOAD)
    )

    client = CepalStatClient()
    manager = DimensionManager(client)

    # Dimension not found by name
    assert manager.find_member_id(4788, "inexistente", "Chile") is None

    # Dimension not found by ID
    assert manager.find_member_id(4788, 99999, "Chile") is None

    # Member not found by name in existing dimension
    assert manager.find_member_id(4788, "País", "Francia") is None

    # Member not found in dimension specified by ID
    assert manager.find_member_id(4788, 29117, "1900") is None


def test_member_and_dimension_models():
    member = Member(id=1, name="Total")
    assert member.id == 1
    assert member.name == "Total"
    assert member.order is None
    assert member.parent is None
    assert member.selected is None

    dim = Dimension(id=10, name="Dim1", members=[member])
    assert dim.id == 10
    assert dim.name == "Dim1"
    assert len(dim.members) == 1
    assert dim.members[0].name == "Total"
