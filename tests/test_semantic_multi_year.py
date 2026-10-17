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


def test_engine_resolves_multi_year_range_in_trace_and_stage5_audit():
    from statscepal.semantic.engine import SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    res = engine.resolve("cual es la pobreza extrema etnica en el peru de 2019 al 2021")

    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 3342
    assert res.applied_filters.time_mode == "RANGE"
    assert res.applied_filters.years == [2019, 2020, 2021]

    assert res.temporal_info is not None
    assert res.temporal_info.requested_years == [2019, 2020, 2021]
    assert res.temporal_info.observed_years == [2019, 2020, 2021]
    assert res.temporal_info.unobserved_years == []

    trace_text = "\n".join(res.execution_trace)
    assert "2019-2021" in trace_text
    assert "Mode: RANGE" in trace_text
    assert "Years=[2019, 2020, 2021]" in trace_text
    assert "Year: 2021," not in trace_text
    assert "Year=2021 ->" not in trace_text


def test_engine_multi_year_range_with_survey_gaps_reports_observed_and_unobserved_years():
    from statscepal.semantic.engine import SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    res = engine.resolve("tasa de pobreza en chile de 2019 al 2022")

    assert res.status == ResolutionStatus.RESOLVED_WITH_ANCHORS
    assert res.temporal_info is not None
    assert res.temporal_info.requested_years == [2019, 2020, 2021, 2022]
    assert 2020 in res.temporal_info.observed_years
    assert 2022 in res.temporal_info.observed_years
    assert 2021 in res.temporal_info.unobserved_years
    assert "2021" in res.temporal_info.disclaimer


def test_cli_displays_multi_year_range_and_breakdown_series(capsys):
    from statscepal.cli import main

    ret = main(["semantic", "resolve", "cual es la pobreza extrema etnica en el peru de 2019 al 2021", "--explain"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "2019-2021" in out
    assert "RANGE" in out
    assert "2019, 2020, 2021" in out
    assert "Years=[2019, 2020, 2021]" in out


def test_parser_extracts_multiple_countries_in_query_order():
    from statscepal.semantic.parser import QueryParser

    parser = QueryParser()
    intent = parser.parse("cual fue el ingreso en peru colombia y chile en el 2022")
    assert intent.country_codes == ["PER", "COL", "CHL"]
    assert intent.country_names == ["Perú", "Colombia", "Chile"]
    assert intent.country_code == "PER"
    assert intent.country_name == "Perú"


def test_engine_resolves_multi_country_query_and_audits_all_countries():
    from statscepal.semantic.engine import SemanticResolutionEngine

    engine = SemanticResolutionEngine()

    # 1. User's motivating query with 3 countries
    res1 = engine.resolve("cual fue el ingreso en peru colombia y chile en el 2022")
    assert res1.applied_filters.country_codes == ["PER", "COL", "CHL"]
    assert res1.applied_filters.country_names == ["Perú", "Colombia", "Chile"]
    trace1 = "\n".join(res1.execution_trace)
    assert "Perú (PER), Colombia (COL), Chile (CHL)" in trace1

    # 2. Multi-country query where one country (Chile in 2021) has a survey gap
    res2 = engine.resolve("tasa de pobreza en peru colombia y chile en el 2021")
    assert res2.status == ResolutionStatus.RESOLVED_WITH_ANCHORS
    assert res2.temporal_info is not None
    assert res2.temporal_info.requested_countries == ["PER", "COL", "CHL"]
    assert "PER" in res2.temporal_info.observed_countries
    assert "COL" in res2.temporal_info.observed_countries
    assert "CHL" in res2.temporal_info.unobserved_countries
    assert "CHL" in res2.temporal_info.disclaimer or "Chile" in res2.temporal_info.disclaimer


def test_fetcher_and_cli_support_multi_country_extraction(capsys):
    from statscepal.cli import main
    from statscepal.semantic.engine import SemanticResolutionEngine

    ret = main(["semantic", "resolve", "cual fue el ingreso en peru colombia y chile en el 2022", "--explain"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Country:   Perú (PER), Colombia (COL), Chile (CHL)" in out
    assert "Geography: Perú (PER), Colombia (COL), Chile (CHL)" in out

    engine = SemanticResolutionEngine()
    res = engine.resolve("salario minimo real en peru colombia y chile en el 2022")
    mock_df = pd.DataFrame([
        {"iso3": "PER", "year": 2022, "value": 98.5, "notes": ""},
        {"iso3": "COL", "year": 2022, "value": 103.1, "notes": ""},
        {"iso3": "CHL", "year": 2022, "value": 106.4, "notes": ""},
        {"iso3": "BRA", "year": 2022, "value": 101.0, "notes": ""},
    ])
    fetcher = SemanticDataFetcher()
    with patch.object(fetcher, "_load_indicator_data", return_value=mock_df):
        payload = fetcher.fetch_resolved_data(res)

    assert payload["observation_exists"] is True
    assert "series" in payload
    assert len(payload["series"]) == 3
    assert {item["country"] for item in payload["series"]} == {"PER", "COL", "CHL"}


