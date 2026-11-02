import sys
from unittest.mock import MagicMock, patch

import pandas as pd

from unofficial_cepalstat_mcp.dimensions import Dimension, Member
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.fetcher import SemanticDataFetcher


def test_fetcher_ignores_purely_numeric_notes_ids(mocker) -> None:
    dims = [
        Dimension(id=208, name="País__ESTANDAR", members=[Member(id=210, name="Perú")]),
        Dimension(id=29117, name="Años__ESTANDAR", members=[Member(id=29190, name="2022")]),
    ]
    # Simulate API returning notes_ids as numeric 12080 without text notes
    df = pd.DataFrame([{
        "País__ESTANDAR": "Perú",
        "iso3": "PER",
        "Años__ESTANDAR": 2022,
        "value": 236311.0,
        "notes_ids": 12080,
    }])
    extractor = mocker.Mock()
    extractor.dimension_manager.get_dimensions.return_value = dims
    extractor.get_dataframe.return_value = df

    engine = SemanticResolutionEngine()
    resp = engine.resolve("pib del peru 2022")
    fetcher = SemanticDataFetcher(extractor=extractor)
    result = fetcher.fetch_resolved_data(resp)

    assert result["observation_exists"] is True
    # The note should be empty, NOT '12080'
    assert result["notes"] == ""
    for item in result["series"]:
        assert item["notes"] == ""
        assert "12080" not in str(item["notes"])


def test_cli_renders_clean_units_without_stray_numeric_ids(capsys, monkeypatch) -> None:
    from unofficial_cepalstat_mcp.cli import main

    # Mock resolve and fetch to return series with numeric notes_ids
    sample_res = {
        "observation_exists": True,
        "series": [
            {"year": 2020, "value": 202645, "unit": "Millones de USD constantes", "notes": "12080"},
            {"year": 2021, "value": 229834, "unit": "Millones de USD constantes", "notes": ""},
        ],
        "status": "RESOLVED",
    }
    with patch("unofficial_cepalstat_mcp.cli.SemanticDataFetcher") as MockFetcher, \
         patch("unofficial_cepalstat_mcp.cli.SemanticResolutionEngine") as MockEngine:
        mock_engine_inst = MockEngine.return_value
        mock_resp = MagicMock()
        mock_resp.status.value = "RESOLVED"
        mock_resp.selected_candidate.indicator_id = 2204
        mock_resp.selected_candidate.name = "PIB constante"
        mock_resp.selected_candidate.measure_type = "VOLUMEN_REAL"
        mock_resp.selected_candidate.unit = "Millones de USD constantes"
        mock_resp.selected_candidate.relevance_score = 1.0
        mock_resp.temporal_info = None
        mock_resp.applied_filters.country_name = "Perú"
        mock_resp.applied_filters.country_code = "PER"
        mock_resp.applied_filters.country_names = ["Perú"]
        mock_resp.applied_filters.year = 2020
        mock_resp.applied_filters.years = [2020, 2021]
        mock_resp.applied_filters.time_mode = "RANGE"
        mock_resp.applied_filters.facets = {}
        mock_resp.applied_filters.dimensions = []
        mock_resp.empirical_data = sample_res
        mock_resp.alternatives = []
        mock_resp.conversational_hint = None
        mock_resp.polarity_info = None
        mock_resp.abstention_reason = None
        mock_engine_inst.resolve.return_value = mock_resp
        mock_engine_inst.resolve_query.return_value = mock_resp

        mock_fetcher_inst = MockFetcher.return_value
        mock_fetcher_inst.fetch_resolved_data.return_value = sample_res

        sys.argv = ["unofficial-cepalstat-mcp", "semantic", "resolve", "pib del peru entre 2020 y 2021", "--fetch"]
        main()
        captured = capsys.readouterr()
        # Verify 12080 is suppressed from CLI table output
        assert "12080" not in captured.out
