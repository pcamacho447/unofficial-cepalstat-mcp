import pytest
import respx
import httpx
from statscepal.client import CepalStatClient
from statscepal.exceptions import (
    CepalStatError,
    CepalStatAPIError,
    CepalStatNetworkError,
)


@respx.mock
def test_client_get_json_success():
    mock_route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/test").mock(
        return_value=httpx.Response(
            200,
            json={
                "header": {"success": True, "code": 200},
                "body": {"message": "ok"},
                "footer": {"records": 1},
            },
        )
    )

    client = CepalStatClient()
    response = client.get("/cepalstat/api/v1/test")

    assert mock_route.called
    assert response["body"]["message"] == "ok"
    # Verify default query parameters
    assert mock_route.calls.last.request.url.params["lang"] == "es"
    assert mock_route.calls.last.request.url.params["format"] == "json"


@respx.mock
def test_client_get_custom_params():
    mock_route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/test").mock(
        return_value=httpx.Response(200, json={"data": 123})
    )

    client = CepalStatClient(lang="en")
    response = client.get("cepalstat/api/v1/test", params={"in": 12, "lang": "fr"})

    assert mock_route.called
    assert response["data"] == 123
    assert mock_route.calls.last.request.url.params["in"] == "12"
    assert mock_route.calls.last.request.url.params["lang"] == "fr"


@respx.mock
def test_client_get_raw_success():
    csv_bytes = b"id,val\n1,100\n"
    mock_route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/export").mock(
        return_value=httpx.Response(200, content=csv_bytes)
    )

    with CepalStatClient() as client:
        raw = client.get_raw("/cepalstat/api/v1/export", response_format="csv")

    assert mock_route.called
    assert raw == csv_bytes
    assert mock_route.calls.last.request.url.params["format"] == "csv"


@respx.mock
def test_client_api_error_raised_on_404():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/bad").mock(
        return_value=httpx.Response(404, json={"message": "Not found"})
    )

    client = CepalStatClient()
    with pytest.raises(CepalStatAPIError) as exc_info:
        client.get("/cepalstat/api/v1/bad")

    assert exc_info.value.status_code == 404
    assert issubclass(CepalStatAPIError, CepalStatError)


@respx.mock
def test_client_api_error_raised_on_500():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/error").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    client = CepalStatClient()
    with pytest.raises(CepalStatAPIError) as exc_info:
        client.get_raw("/cepalstat/api/v1/error")

    assert exc_info.value.status_code == 500


@respx.mock
def test_client_api_error_on_invalid_json():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/invalid-json").mock(
        return_value=httpx.Response(200, text="NOT_JSON_BODY")
    )

    client = CepalStatClient()
    with pytest.raises(CepalStatAPIError) as exc_info:
        client.get("/cepalstat/api/v1/invalid-json")

    assert "Invalid JSON" in str(exc_info.value)


@respx.mock
def test_client_network_error():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/timeout").mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )

    client = CepalStatClient()
    with pytest.raises(CepalStatNetworkError):
        client.get("/cepalstat/api/v1/timeout")


def test_client_context_manager():
    client = CepalStatClient()
    with client as c:
        assert c is client
        assert not client._client.is_closed
    assert client._client.is_closed


def test_package_exports():
    import statscepal

    assert hasattr(statscepal, "CepalStatClient")
    assert hasattr(statscepal, "CepalStatError")
    assert hasattr(statscepal, "CepalStatNetworkError")
    assert hasattr(statscepal, "CepalStatAPIError")

