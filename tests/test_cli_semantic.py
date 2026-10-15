"""Tests for semantic CLI subcommands."""

import json
from unittest.mock import MagicMock
import pytest

from statscepal.cli import main
from statscepal.semantic import SemanticDataFetcher


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
