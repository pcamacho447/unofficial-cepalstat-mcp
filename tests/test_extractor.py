import pytest
import respx
import httpx
import pandas as pd
from statscepal.client import CepalStatClient
from statscepal.dimensions import DimensionManager
from statscepal.extractor import DataExtractor


MOCK_METADATA_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "metadata": {
            "indicator_id": 4788,
            "indicator_name": "Población total, según sexo",
            "unit": "Miles de personas",
        }
    },
    "footer": {"records": 1},
}

MOCK_RECORDS_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "data": [
            {
                "value": "19370.6",
                "iso3": "CHL",
                "dim_208": 224,
                "dim_29117": 29190,
            }
        ]
    },
    "footer": {"records": 1},
}

MOCK_DIMENSIONS_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "dimensions": [
            {
                "id": 208,
                "name": "País__ESTANDAR",
                "members": [
                    {"id": 224, "name": "Chile"},
                    {"id": 218, "name": "Argentina"},
                ],
            },
            {
                "id": 29117,
                "name": "Años__ESTANDAR",
                "members": [
                    {"id": 29190, "name": "2020"},
                    {"id": 29191, "name": "2021"},
                ],
            },
        ]
    },
    "footer": {"records": 2},
}


@respx.mock
def test_get_metadata():
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/metadata").mock(
        return_value=httpx.Response(200, json=MOCK_METADATA_PAYLOAD)
    )

    client = CepalStatClient()
    extractor = DataExtractor(client)

    metadata = extractor.get_metadata(4788)
    assert route.called
    assert metadata["indicator_id"] == 4788
    assert metadata["indicator_name"] == "Población total, según sexo"
    assert metadata["unit"] == "Miles de personas"


@respx.mock
def test_get_records_without_members():
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/records").mock(
        return_value=httpx.Response(200, json=MOCK_RECORDS_PAYLOAD)
    )

    client = CepalStatClient()
    extractor = DataExtractor(client)

    records = extractor.get_records(4788)
    assert route.called
    assert len(records) == 1
    assert records[0]["iso3"] == "CHL"
    assert records[0]["value"] == "19370.6"

    # Verify query params did not contain members
    request = route.calls.last.request
    assert "members" not in request.url.params


@respx.mock
def test_get_records_with_members():
    route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/records").mock(
        return_value=httpx.Response(200, json=MOCK_RECORDS_PAYLOAD)
    )

    client = CepalStatClient()
    extractor = DataExtractor(client)

    records = extractor.get_records(4788, members=[224, 29190])
    assert route.called
    assert len(records) == 1

    # Verify query params contained comma-separated members
    request = route.calls.last.request
    assert request.url.params.get("members") == "224,29190"


@respx.mock
def test_get_dataframe_decoded():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/metadata").mock(
        return_value=httpx.Response(200, json=MOCK_METADATA_PAYLOAD)
    )
    records_route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/records").mock(
        return_value=httpx.Response(200, json=MOCK_RECORDS_PAYLOAD)
    )
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/dimensions").mock(
        return_value=httpx.Response(200, json=MOCK_DIMENSIONS_PAYLOAD)
    )

    client = CepalStatClient()
    extractor = DataExtractor(client)

    df = extractor.get_dataframe(4788, members=[224, 29190], decode_labels=True)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1

    # Verify numeric casting of value column
    assert df.loc[0, "value"] == 19370.6
    assert pd.api.types.is_numeric_dtype(df["value"])

    # Verify other columns
    assert df.loc[0, "iso3"] == "CHL"

    # Verify decoded dimensions and dropped raw dim_ columns
    assert df.loc[0, "País__ESTANDAR"] == "Chile"
    assert df.loc[0, "Años__ESTANDAR"] == "2020"
    assert "dim_208" not in df.columns
    assert "dim_29117" not in df.columns

    # Verify members param passed
    assert records_route.calls.last.request.url.params.get("members") == "224,29190"


@respx.mock
def test_get_dataframe_without_decoding():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/records").mock(
        return_value=httpx.Response(200, json=MOCK_RECORDS_PAYLOAD)
    )
    dims_route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/dimensions").mock(
        return_value=httpx.Response(200, json=MOCK_DIMENSIONS_PAYLOAD)
    )

    client = CepalStatClient()
    extractor = DataExtractor(client)

    df = extractor.get_dataframe(4788, decode_labels=False)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.loc[0, "value"] == 19370.6
    assert df.loc[0, "dim_208"] == 224
    assert df.loc[0, "dim_29117"] == 29190
    assert "País__ESTANDAR" not in df.columns
    # Dimensions endpoint should not be fetched when decode_labels=False
    assert not dims_route.called


@respx.mock
def test_get_dataframe_empty():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/records").mock(
        return_value=httpx.Response(
            200,
            json={"header": {"success": True, "code": 200}, "body": {"data": []}, "footer": {"records": 0}},
        )
    )

    client = CepalStatClient()
    extractor = DataExtractor(client)

    df = extractor.get_dataframe(4788)
    assert isinstance(df, pd.DataFrame)
    assert df.empty


@respx.mock
def test_custom_dimension_manager_injection():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/records").mock(
        return_value=httpx.Response(200, json=MOCK_RECORDS_PAYLOAD)
    )
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/dimensions").mock(
        return_value=httpx.Response(200, json=MOCK_DIMENSIONS_PAYLOAD)
    )

    client = CepalStatClient()
    custom_dm = DimensionManager(client)
    extractor = DataExtractor(client, dimension_manager=custom_dm)

    assert extractor.dimension_manager is custom_dm
    df = extractor.get_dataframe(4788, decode_labels=True)
    assert df.loc[0, "País__ESTANDAR"] == "Chile"
