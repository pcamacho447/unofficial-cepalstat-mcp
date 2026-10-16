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
