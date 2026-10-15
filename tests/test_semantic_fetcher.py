"""Tests for the SemanticDataFetcher empirical data retrieval component."""

from unittest.mock import MagicMock
import pandas as pd
import pytest

from statscepal.extractor import DataExtractor
from statscepal.semantic.fetcher import SemanticDataFetcher
from statscepal.semantic.models import (
    AppliedDimensionFilter,
    AppliedFilters,
    ResolutionStatus,
    SelectedCandidate,
    SemanticResolutionResponse,
)


def test_semantic_data_fetcher_extracts_and_formats_observation():
    mock_extractor = MagicMock(spec=DataExtractor)
    mock_extractor.get_dataframe.return_value = pd.DataFrame(
        [
            {
                "country": "Brasil",
                "year": 2021,
                "value": 31.8,
                "notes_ids": "",
            }
        ]
    )

    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="pobreza brasil 2021",
        selected_candidate=SelectedCandidate(
            indicator_id=3328,
            name="Población en situación de pobreza",
            measure_type="INCIDENCIA",
            unit="%",
        ),
        applied_filters=AppliedFilters(
            country_name="Brasil",
            country_code="BRA",
            year=2021,
            dimensions=[
                AppliedDimensionFilter(
                    dim_id=144,
                    dim_name="Sexo",
                    member_id=146,
                    member_name="Ambos sexos",
                )
            ],
        ),
    )

    fetcher = SemanticDataFetcher(extractor=mock_extractor)
    payload = fetcher.fetch_resolved_data(response)

    assert payload["observation_exists"] is True
    assert payload["indicator_id"] == 3328
    assert payload["indicator_name"] == "Población en situación de pobreza"
    assert payload["value"] == 31.8
    assert payload["unit"] == "%"
    assert payload["country"] == "Brasil"
    assert payload["year"] == 2021
    assert len(payload["dimensions_applied"]) == 1
    assert payload["dimensions_applied"][0]["member_name"] == "Ambos sexos"
    assert payload["notes"] == ""
    assert response.empirical_data == payload

    mock_extractor.get_dataframe.assert_called_once_with(3328, members=[146])


def test_semantic_data_fetcher_handles_unresolved_status():
    mock_extractor = MagicMock(spec=DataExtractor)

    response = SemanticResolutionResponse(
        status=ResolutionStatus.ABSTAINED,
        query="pobreza multidimensional chile 2020",
        abstention_reason="Unsupported facet: multidimensional",
        unsupported_facet="multidimensional",
    )

    fetcher = SemanticDataFetcher(extractor=mock_extractor)
    payload = fetcher.fetch_resolved_data(response)

    assert payload["observation_exists"] is False
    assert payload["reason"] == "Query not resolved or abstained"
    assert response.empirical_data == payload
    mock_extractor.get_dataframe.assert_not_called()


def test_semantic_data_fetcher_handles_missing_observation():
    mock_extractor = MagicMock(spec=DataExtractor)
    mock_extractor.get_dataframe.return_value = pd.DataFrame()

    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="pobreza brasil 2025",
        selected_candidate=SelectedCandidate(
            indicator_id=3328,
            name="Población en situación de pobreza",
            measure_type="INCIDENCIA",
            unit="%",
        ),
        applied_filters=AppliedFilters(
            country_name="Brasil",
            year=2025,
        ),
    )

    fetcher = SemanticDataFetcher(extractor=mock_extractor)
    payload = fetcher.fetch_resolved_data(response)

    assert payload["observation_exists"] is False
    assert payload["indicator_id"] == 3328
    assert payload["indicator_name"] == "Población en situación de pobreza"
    assert payload["unit"] == "%"
    assert payload["country"] == "Brasil"
    assert payload["year"] == 2025
    assert payload["reason"] == "No observation available for the specified filters/period"
    assert response.empirical_data == payload


def test_semantic_data_fetcher_filters_by_country_and_year_and_dimension():
    mock_extractor = MagicMock(spec=DataExtractor)
    mock_extractor.get_dataframe.return_value = pd.DataFrame(
        [
            {"País__ESTANDAR": "Chile", "Años__ESTANDAR": 2020, "Sexo": "Mujeres", "value": 11.2, "notes_ids": "A1"},
            {"País__ESTANDAR": "Brasil", "Años__ESTANDAR": 2020, "Sexo": "Mujeres", "value": 29.5, "notes_ids": "B1"},
            {"País__ESTANDAR": "Brasil", "Años__ESTANDAR": 2021, "Sexo": "Hombres", "value": 28.0, "notes_ids": "B2"},
            {"País__ESTANDAR": "Brasil", "Años__ESTANDAR": 2021, "Sexo": "Mujeres", "value": 32.1, "notes_ids": "B3"},
        ]
    )

    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED_WITH_ANCHORS,
        query="pobreza brasil mujeres 2021",
        selected_candidate=SelectedCandidate(
            indicator_id=3328,
            name="Población en situación de pobreza",
            measure_type="INCIDENCIA",
            unit="%",
        ),
        applied_filters=AppliedFilters(
            country_name="Brasil",
            year=2021,
            dimensions=[
                AppliedDimensionFilter(
                    dim_id=144,
                    dim_name="Sexo",
                    member_id=266,
                    member_name="Mujeres",
                )
            ],
        ),
    )

    fetcher = SemanticDataFetcher(extractor=mock_extractor)
    payload = fetcher.fetch_resolved_data(response)

    assert payload["observation_exists"] is True
    assert payload["value"] == 32.1
    assert payload["year"] == 2021
    assert payload["notes"] == "B3"


def test_semantic_data_fetcher_default_initialization():
    fetcher = SemanticDataFetcher()
    assert fetcher.extractor is not None
    assert fetcher.client is not None
    fetcher.client.close()


def test_semantic_data_fetcher_handles_none_selected_candidate():
    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="pobreza",
        selected_candidate=None,
    )
    fetcher = SemanticDataFetcher()
    payload = fetcher.fetch_resolved_data(response)
    assert payload["observation_exists"] is False
    assert payload["reason"] == "Query not resolved or abstained"
    fetcher.client.close()


def test_semantic_data_fetcher_handles_nan_value_row():
    mock_extractor = MagicMock(spec=DataExtractor)
    mock_extractor.get_dataframe.return_value = pd.DataFrame(
        [
            {"country": "Brasil", "year": 2021, "value": None}
        ]
    )

    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="pobreza brasil 2021",
        selected_candidate=SelectedCandidate(
            indicator_id=3328,
            name="Población en situación de pobreza",
            unit="%",
        ),
        applied_filters=AppliedFilters(
            country_name="Brasil",
            year=2021,
        ),
    )

    fetcher = SemanticDataFetcher(extractor=mock_extractor)
    payload = fetcher.fetch_resolved_data(response)
    assert payload["observation_exists"] is False
    assert payload["reason"] == "No observation available for the specified filters/period"


def test_semantic_data_fetcher_uses_fetch_indicator_dataframe_if_present():
    class CustomExtractor:
        def fetch_indicator_dataframe(self, indicator_id: int, members: list[int] | None = None):
            return pd.DataFrame([{"country": "Chile", "year": 2020, "value": 10.5}])

    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="pobreza chile 2020",
        selected_candidate=SelectedCandidate(
            indicator_id=3328,
            name="Población en situación de pobreza",
            unit="%",
        ),
        applied_filters=AppliedFilters(
            country_name="Chile",
            year=2020,
        ),
    )

    fetcher = SemanticDataFetcher(extractor=CustomExtractor())  # type: ignore[arg-type]
    payload = fetcher.fetch_resolved_data(response)
    assert payload["observation_exists"] is True
    assert payload["value"] == 10.5

