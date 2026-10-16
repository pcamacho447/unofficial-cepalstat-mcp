import pytest
from statscepal.semantic.models import AppliedFilters, ParsedIntent


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

