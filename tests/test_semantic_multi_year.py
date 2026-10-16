from unittest.mock import patch
import pandas as pd
import pytest
from statscepal.semantic.fetcher import SemanticDataFetcher
from statscepal.semantic.models import (
    AppliedFilters,
    ParsedIntent,
    ResolutionStatus,
    SelectedCandidate,
    SemanticResolutionResponse,
)


def test_applied_filters_multi_year_defaults_and_assignment():
    filters = AppliedFilters(country_code="PER", country_name="Perú", year=2023, years=[2022, 2023], time_mode="LIST")
    assert filters.year == 2023
    assert filters.years == [2022, 2023]
    assert filters.time_mode == "LIST"
    assert filters.relative_window_size is None


def test_applied_filters_default_values():
    filters = AppliedFilters()
    assert filters.year is None
    assert filters.years == []
    assert filters.time_mode == "SINGLE"
    assert filters.relative_window_size is None


def test_parsed_intent_multi_year_fields():
    intent = ParsedIntent(
        raw_query="en 2022 y 2023",
        clean_query="en 2022 y 2023",
        years=[2022, 2023],
        time_mode="LIST",
    )
    assert intent.years == [2022, 2023]
    assert intent.time_mode == "LIST"
    assert intent.relative_window_size is None


def test_parsed_intent_default_values():
    intent = ParsedIntent(raw_query="test", clean_query="test")
    assert intent.year is None
    assert intent.years == []
    assert intent.time_mode == "SINGLE"
    assert intent.relative_window_size is None


def test_parsed_intent_importable_from_models_and_parser():
    from statscepal.semantic.parser import ParsedIntent as ParserParsedIntent
    from statscepal.semantic.models import ParsedIntent as ModelsParsedIntent

    assert ParserParsedIntent is ModelsParsedIntent


def test_parser_extracts_discrete_year_list():
    from statscepal.semantic.parser import QueryParser

    parser = QueryParser()
    intent = parser.parse("Cual fue la plata minima real en peru en el 2023 y 2022")
    assert intent.time_mode == "LIST"
    assert sorted(intent.years) == [2022, 2023]
    assert intent.year == 2023  # Primary anchor is latest


def test_parser_extracts_closed_year_range():
    from statscepal.semantic.parser import QueryParser

    parser = QueryParser()
    intent = parser.parse("inflacion en chile del 2019 al 2022")
    assert intent.time_mode == "RANGE"
    assert intent.years == [2019, 2020, 2021, 2022]
    assert intent.year == 2022

    intent_dash = parser.parse("PIB de Colombia 2020-2023")
    assert intent_dash.time_mode == "RANGE"
    assert intent_dash.years == [2020, 2021, 2022, 2023]
    assert intent_dash.year == 2023


def test_parser_extracts_relative_time_window():
    from statscepal.semantic.parser import QueryParser

    parser = QueryParser()
    intent = parser.parse("inflacion de alimentos en peru los ultimos 4 anos")
    assert intent.time_mode == "RELATIVE_WINDOW"
    assert intent.relative_window_size == 4
    assert intent.year is None  # Anchored dynamically by fetcher

    intent_decada = parser.parse("pobreza en colombia la ultima decada")
    assert intent_decada.time_mode == "RELATIVE_WINDOW"
    assert intent_decada.relative_window_size == 10
    assert intent_decada.year is None

    intent_quinquenio = parser.parse("desempleo en uruguay en el ultimo quinquenio")
    assert intent_quinquenio.time_mode == "RELATIVE_WINDOW"
    assert intent_quinquenio.relative_window_size == 5
    assert intent_quinquenio.year is None

    intent_trienio = parser.parse("gini en brasil ultimo trienio")
    assert intent_trienio.time_mode == "RELATIVE_WINDOW"
    assert intent_trienio.relative_window_size == 3
    assert intent_trienio.year is None


def test_parser_single_year_canonical_mode():
    from statscepal.semantic.parser import QueryParser

    parser = QueryParser()
    intent = parser.parse("pobreza en chile 2021")
    assert intent.time_mode == "SINGLE"
    assert intent.years == [2021]
    assert intent.year == 2021


def test_engine_propagates_multi_year_filters():
    from statscepal.semantic.engine import SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    res = engine.resolve_query("inflacion en chile del 2019 al 2022")
    assert res.applied_filters.time_mode == "RANGE"
    assert res.applied_filters.years == [2019, 2020, 2021, 2022]
    assert res.applied_filters.year == 2022


def test_fetcher_extracts_multi_year_series():
    mock_df = pd.DataFrame([
        {"country": "Peru", "year": 2021, "value": 100.0, "notes": ""},
        {"country": "Peru", "year": 2022, "value": 104.2, "notes": ""},
        {"country": "Peru", "year": 2023, "value": 101.8, "notes": ""},
    ])

    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="plata minima en peru en 2022 y 2023",
        selected_candidate=SelectedCandidate(indicator_id=3337, name="Salario mínimo real", unit="índice 2018=100"),
        applied_filters=AppliedFilters(country_name="Perú", country_code="PER", year=2023, years=[2022, 2023], time_mode="LIST"),
    )

    fetcher = SemanticDataFetcher()
    with patch.object(fetcher, "_load_indicator_data", return_value=mock_df):
        payload = fetcher.fetch_resolved_data(response)

    assert payload["observation_exists"] is True
    assert "series" in payload
    assert len(payload["series"]) == 2
    assert payload["series"][0]["year"] == 2022
    assert payload["series"][0]["value"] == 104.2
    assert payload["series"][1]["year"] == 2023
    assert payload["series"][1]["value"] == 101.8


def test_fetcher_extracts_relative_window_series():
    mock_df = pd.DataFrame([
        {"country": "Peru", "year": 2019, "value": 95.0},
        {"country": "Peru", "year": 2020, "value": 98.0},
        {"country": "Peru", "year": 2021, "value": 100.0},
        {"country": "Peru", "year": 2022, "value": 104.2},
        {"country": "Peru", "year": 2023, "value": 101.8},
    ])

    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="ultimos 3 anos",
        selected_candidate=SelectedCandidate(indicator_id=3337, name="Salario mínimo real", unit="índice 2018=100"),
        applied_filters=AppliedFilters(country_name="Perú", country_code="PER", time_mode="RELATIVE_WINDOW", relative_window_size=3),
    )

    fetcher = SemanticDataFetcher()
    with patch.object(fetcher, "_load_indicator_data", return_value=mock_df):
        payload = fetcher.fetch_resolved_data(response)

    assert len(payload["series"]) == 3
    assert [s["year"] for s in payload["series"]] == [2021, 2022, 2023]


