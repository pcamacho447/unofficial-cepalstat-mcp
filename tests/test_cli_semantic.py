"""Tests for semantic CLI subcommands."""

import json

from unofficial_cepalstat_mcp.cli import main
from unofficial_cepalstat_mcp.semantic import SemanticDataFetcher


def test_cli_semantic_help(capsys):
    """Test statscepal semantic --help exits with 0 and prints subcommands."""
    ret = main(["semantic", "--help"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "resolve" in captured.out


def test_cli_semantic_no_subcommand(capsys):
    """Test statscepal semantic with no subcommand prints help and returns 0."""
    ret = main(["semantic"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "resolve" in captured.out


def test_cli_semantic_resolve_json_output(capsys):
    """Test semantic resolve with --json outputs valid JSON response."""
    ret = main(["semantic", "resolve", "Pobreza total en Brasil en 2021", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "RESOLVED"
    assert data["selected_candidate"] is not None
    assert data["selected_candidate"]["indicator_id"] == 3328
    assert data["applied_filters"]["country_name"] == "Brasil"
    assert data["applied_filters"]["year"] == 2021


def test_cli_semantic_resolve_table_output(capsys):
    """Test semantic resolve default table output contains resolution and anchor info."""
    ret = main(["semantic", "resolve", "Tasa de pobreza de Chile en 2021"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "CEPALSTAT Semantic Resolution Engine" in captured.out
    assert "RESOLVED" in captured.out
    assert "3328" in captured.out
    assert "Chile" in captured.out
    assert "PERIOD_UNOBSERVED" in captured.out
    assert "Prev=2020" in captured.out
    assert "Next=2022" in captured.out


def test_cli_semantic_resolve_fetch_flag(capsys, monkeypatch):
    """Test semantic resolve with --fetch calls SemanticDataFetcher and formats output."""
    def mock_fetch(self, response):
        payload = {
            "observation_exists": True,
            "indicator_id": 3328,
            "indicator_name": "Población en situación de pobreza extrema y pobreza",
            "value": 10.5,
            "unit": "%",
            "country": "Brasil",
            "year": 2021,
            "notes": "Cifras oficiales estimadas",
        }
        response.empirical_data = payload
        return payload

    monkeypatch.setattr(SemanticDataFetcher, "fetch_resolved_data", mock_fetch)

    ret = main(["semantic", "resolve", "Pobreza total en Brasil en 2021", "--fetch"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Empirical Observation:" in captured.out
    assert "Value:     10.5 %" in captured.out
    assert "Year:      2021" in captured.out
    assert "Notes:     Cifras oficiales estimadas" in captured.out


def test_cli_semantic_resolve_fetch_json(capsys, monkeypatch):
    """Test semantic resolve with --fetch and --json includes empirical data in JSON."""
    def mock_fetch(self, response):
        payload = {
            "observation_exists": True,
            "indicator_id": 3328,
            "indicator_name": "Población en situación de pobreza extrema y pobreza",
            "value": 10.5,
            "unit": "%",
            "country": "Brasil",
            "year": 2021,
            "notes": "Cifras oficiales estimadas",
        }
        response.empirical_data = payload
        return payload

    monkeypatch.setattr(SemanticDataFetcher, "fetch_resolved_data", mock_fetch)

    ret = main(["semantic", "resolve", "Pobreza total en Brasil en 2021", "--fetch", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "RESOLVED"
    assert data["empirical_data"] is not None
    assert data["empirical_data"]["observation_exists"] is True
    assert data["empirical_data"]["value"] == 10.5


def test_cli_semantic_resolve_abstention_output(capsys):
    """Test semantic resolve with impossible query produces clean abstention JSON."""
    ret = main(["semantic", "resolve", "Indicador que no existe de algo imposible", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"].startswith("ABSTAINED")
    assert data["selected_candidate"] is None
    assert data["abstention_reason"] is not None


def test_cli_semantic_resolve_abstention_table(capsys):
    """Test semantic resolve with impossible query produces clean table without crashing."""
    ret = main(["semantic", "resolve", "Indicador que no existe de algo imposible"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "CEPALSTAT Semantic Resolution Engine" in captured.out
    assert "Status:    ABSTAINED" in captured.out
    assert "Reason:" in captured.out


def test_cli_semantic_resolve_polarity_display(capsys):
    """Test semantic resolve table output displays polarity information when detected."""
    from unofficial_cepalstat_mcp.cli import main

    code = main(["semantic", "resolve", "Cual fue el deficit primario en Chile 2022"])
    assert code == 0
    captured = capsys.readouterr().out
    assert "Polarity:" in captured
    assert "ACCOUNTING_SIGN" in captured
    assert "deficit" in captured


def test_cli_semantic_resolve_multi_year_series_display(capsys):
    """Test semantic resolve with --fetch displays formatted empirical time series table."""
    from unittest.mock import patch

    from unofficial_cepalstat_mcp.cli import main

    mock_payload = {
        "observation_exists": True,
        "indicator_id": 3337,
        "indicator_name": "Salario mínimo real",
        "unit": "índice 2018=100",
        "country": "Perú",
        "year": 2023,
        "value": 101.8,
        "series": [
            {"year": 2022, "value": 104.2, "unit": "índice 2018=100", "notes": ""},
            {"year": 2023, "value": 101.8, "unit": "índice 2018=100", "notes": ""},
        ],
    }

    with patch(
        "unofficial_cepalstat_mcp.semantic.fetcher.SemanticDataFetcher.fetch_resolved_data",
        return_value=mock_payload,
    ):
        code = main(
            ["semantic", "resolve", "plata minima en peru en 2022 y 2023", "--fetch"]
        )
    assert code == 0
    captured = capsys.readouterr().out
    assert "Empirical Series (2 observations):" in captured
    assert "2022" in captured and "104.2" in captured
    assert "2023" in captured and "101.8" in captured


def test_cli_semantic_resolve_ethnic_poverty(capsys=None):
    """Test CLI resolution of ethnic poverty query displays indicator 3342 and dimension filters."""
    import io
    from contextlib import redirect_stdout

    from unofficial_cepalstat_mcp.cli import main

    f = io.StringIO()
    with redirect_stdout(f):
        ret = main(["semantic", "resolve", "cual es la pobreza etnica en el peru del 2020"])
    assert ret == 0
    output = f.getvalue()
    assert "3342" in output
    assert (
        "Población en situación de pobreza extrema y pobreza, por sexo, autoidentificación étnico-racial y área"
        in output
    )
    assert "PER" in output
    assert "2020" in output
    assert "Tipo de etnia" in output or "etnia" in output.lower()


def test_cli_semantic_resolve_displays_conversational_hint_on_alternative_proposed(capsys):
    """Test CLI displays Hint with alternative indicator IDs when ALTERNATIVE_PROPOSED."""
    ret = main(["semantic", "resolve", "cuentas fiscales de chile 2022"])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "ALTERNATIVE_PROPOSED" in captured
    assert "Hint:" in captured
    assert "1240" in captured


def test_cli_info_canonical_alias_mapping_to_empirical_table(capsys, monkeypatch):
    """Test CLI info 1242 automatically maps to empirical table 821 with header note."""
    from unofficial_cepalstat_mcp.extractor import DataExtractor

    mock_meta = {
        "indicator_name": "Ingresos tributarios por tipo de impuestos en porcentajes del PIB",
        "area": "Finanzas Públicas",
        "unit": "En porcentajes del producto interno bruto",
        "definition": "Los ingresos tributarios son pagos obligatorios...",
    }
    monkeypatch.setattr(
        DataExtractor,
        "get_metadata",
        lambda self, ind_id: mock_meta if ind_id == 821 else None,
    )

    ret = main(["info", "1242"])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "Indicator 821" in captured
    assert "mapped from canonical ID 1242" in captured
    assert "Ingresos tributarios" in captured

