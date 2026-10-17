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


def test_fetcher_collapses_unconstrained_dataframe_dimensions_to_aggregate_members():
    """Verify that unbound DataFrame dimensions (e.g. Sexo__ESTANDAR in 3342 or Sexo jefatura in 3345) filter to aggregate instead of duplicating rows."""
    import pandas as pd
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    # Query specifies etnia=INDIGENA, area=NACIONAL, severidad=POBREZA_TOTAL, but leaves Sexo__ESTANDAR unspecified
    res = engine.resolve("pobreza indigena en peru de 2020 al 2021")

    mock_df = pd.DataFrame([
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Años__ESTANDAR": 2020, "Tipo de etnia": "Indígena", "Área geográfica": "Nacional", "Pobreza extrema y pobreza": "Pobreza", "Sexo__ESTANDAR": "Hombres", "value": 24.1, "notes_ids": ""},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Años__ESTANDAR": 2020, "Tipo de etnia": "Indígena", "Área geográfica": "Nacional", "Pobreza extrema y pobreza": "Pobreza", "Sexo__ESTANDAR": "Mujeres", "value": 26.3, "notes_ids": ""},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Años__ESTANDAR": 2020, "Tipo de etnia": "Indígena", "Área geográfica": "Nacional", "Pobreza extrema y pobreza": "Pobreza", "Sexo__ESTANDAR": "Ambos sexos", "value": 25.2, "notes_ids": ""},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Años__ESTANDAR": 2021, "Tipo de etnia": "Indígena", "Área geográfica": "Nacional", "Pobreza extrema y pobreza": "Pobreza", "Sexo__ESTANDAR": "Hombres", "value": 20.0, "notes_ids": ""},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Años__ESTANDAR": 2021, "Tipo de etnia": "Indígena", "Área geográfica": "Nacional", "Pobreza extrema y pobreza": "Pobreza", "Sexo__ESTANDAR": "Mujeres", "value": 22.0, "notes_ids": ""},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Años__ESTANDAR": 2021, "Tipo de etnia": "Indígena", "Área geográfica": "Nacional", "Pobreza extrema y pobreza": "Pobreza", "Sexo__ESTANDAR": "Ambos sexos", "value": 21.0, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher()
    fetcher._load_indicator_data = lambda ind_id, member_ids=None: mock_df

    payload = fetcher.fetch_resolved_data(res)
    assert payload["observation_exists"] is True
    series = payload["series"]
    # Must contain exactly 1 row per year (Ambos sexos), NOT 3 rows per year
    assert len(series) == 2
    assert series[0]["year"] == 2020
    assert series[0]["value"] == 25.2
    assert series[1]["year"] == 2021
    assert series[1]["value"] == 21.0


def test_fetcher_multi_country_without_year_filters_to_latest_year_per_country():
    """Verify multi-country query with no year specified returns only the latest available year per country."""
    import pandas as pd
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    res = engine.resolve("pobreza en peru y chile")

    mock_df = pd.DataFrame([
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Años__ESTANDAR": 2019, "Área geográfica": "Nacional", "Tipo de pobreza": "Total pobreza", "value": 20.2, "notes_ids": ""},
        {"iso3": "PER", "País__ESTANDAR": "Perú", "Años__ESTANDAR": 2022, "Área geográfica": "Nacional", "Tipo de pobreza": "Total pobreza", "value": 27.5, "notes_ids": ""},
        {"iso3": "CHL", "País__ESTANDAR": "Chile", "Años__ESTANDAR": 2017, "Área geográfica": "Nacional", "Tipo de pobreza": "Total pobreza", "value": 10.7, "notes_ids": ""},
        {"iso3": "CHL", "País__ESTANDAR": "Chile", "Años__ESTANDAR": 2022, "Área geográfica": "Nacional", "Tipo de pobreza": "Total pobreza", "value": 6.5, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher()
    fetcher._load_indicator_data = lambda ind_id, member_ids=None: mock_df

    payload = fetcher.fetch_resolved_data(res)
    assert payload["observation_exists"] is True
    series = payload["series"]
    assert len(series) == 2
    by_country = {item["country"]: item for item in series}
    assert by_country["Perú"]["year"] == 2022
    assert by_country["Perú"]["value"] == 27.5
    assert by_country["Chile"]["year"] == 2022
    assert by_country["Chile"]["value"] == 6.5


def test_fetcher_strips_synthetic_member_ids_to_prevent_api_country_collision():
    """Verify synthetic member_id 79578 in 2929 is NOT passed to API get_dataframe, preventing Chile-only filtering."""
    from unittest.mock import MagicMock
    import pandas as pd
    from statscepal.extractor import DataExtractor
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    res = engine.resolve(
        "necesito los datos de la inflacion de alimentos de mexico, peru, argentina, chile, colombia y paraguay del año 2018 al 2023"
    )

    mock_extractor = MagicMock(spec=DataExtractor)
    mock_extractor.get_dataframe.return_value = pd.DataFrame([
        {"iso3": "MEX", "Países_agregados regionales especiales VAR IPC": "México", "Años__ESTANDAR": 2022, "value": 14.1, "notes_ids": ""},
        {"iso3": "PER", "Países_agregados regionales especiales VAR IPC": "Perú", "Años__ESTANDAR": 2022, "value": 15.2, "notes_ids": ""},
        {"iso3": "CHL", "Países_agregados regionales especiales VAR IPC": "Chile", "Años__ESTANDAR": 2022, "value": 21.0, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher(extractor=mock_extractor)
    payload = fetcher.fetch_resolved_data(res)

    # Synthetic member_id 79578 must be stripped so members=None is passed to get_dataframe
    mock_extractor.get_dataframe.assert_called_once_with(2929, members=None)
    assert payload["observation_exists"] is True
    assert len(payload["series"]) == 3
    assert [r["country"] for r in payload["series"]] == ["México", "Perú", "Chile"]


def test_fetcher_maps_synthetic_indicator_2928_to_real_cepalstat_2484():
    """Verify synthetic indicator ID 2928 (IPC general in official_25) maps to real CEPALSTAT ID 2484 during fetch."""
    from unittest.mock import MagicMock
    import pandas as pd
    from statscepal.extractor import DataExtractor
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    res = engine.resolve(
        "necesito los datos de la inflacion de peru, argentina, chile, colombia y paraguay del año 2018 al 2023"
    )
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 2928

    mock_extractor = MagicMock(spec=DataExtractor)
    mock_extractor.get_dataframe.return_value = pd.DataFrame([
        {"iso3": "PER", "Países_agregados regionales especiales VAR IPC": "Perú", "Años__ESTANDAR": 2022, "value": 8.46, "notes_ids": ""},
        {"iso3": "CHL", "Países_agregados regionales especiales VAR IPC": "Chile", "Años__ESTANDAR": 2022, "value": 12.8, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher(extractor=mock_extractor)
    payload = fetcher.fetch_resolved_data(res)

    mock_extractor.get_dataframe.assert_called_once_with(2484, members=None)
    assert payload["observation_exists"] is True
    assert payload["empirical_indicator_id"] == 2484
    assert len(payload["series"]) == 2



