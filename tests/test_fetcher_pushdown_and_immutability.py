import json

import pandas as pd

from unofficial_cepalstat_mcp.dimensions import Dimension, DimensionManager, Member
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.fetcher import SemanticDataFetcher


def test_fetcher_pushes_country_and_year_member_ids_and_does_not_mutate_response(mocker) -> None:
    dims = [
        Dimension(id=208, name="País__ESTANDAR", members=[Member(id=79578, name="Chile"), Member(id=210, name="Perú")]),
        Dimension(id=29117, name="Años__ESTANDAR", members=[Member(id=29190, name="2022"), Member(id=29191, name="2023")]),
    ]
    df = pd.DataFrame([{"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "value": 11.6}])
    extractor = mocker.Mock()
    extractor.dimension_manager.get_dimensions.return_value = dims
    extractor.get_dataframe.return_value = df

    resp = SemanticResolutionEngine().resolve("inflación anual en Chile 2022")
    trace_before = list(resp.execution_trace)
    out = SemanticDataFetcher(extractor=extractor).fetch_resolved_data(resp)

    assert out["observation_exists"] is True
    called_members = extractor.get_dataframe.call_args.kwargs.get("members") or extractor.get_dataframe.call_args.args[1]
    assert 79578 in called_members and 29190 in called_members
    assert resp.execution_trace == trace_before
    assert resp.empirical_data is None


def test_fetcher_fails_closed_on_unconstrained_dimension_without_total_member(mocker) -> None:
    df = pd.DataFrame([
        {"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "Producto CUCI": "Cobre", "value": 45000.0},
        {"País__ESTANDAR": "Chile", "iso3": "CHL", "Años__ESTANDAR": 2022, "Producto CUCI": "Celulosa", "value": 3200.0},
    ])
    extractor = mocker.Mock(get_dataframe=mocker.Mock(return_value=df))
    extractor.dimension_manager.get_dimensions.return_value = []
    resp = SemanticResolutionEngine().resolve("inflación anual en Chile 2022")
    out = SemanticDataFetcher(extractor=extractor).fetch_resolved_data(resp)
    assert out["observation_exists"] is False
    assert "AMBIGUOUS_UNCONSTRAINED_DIMENSION" in out["reason"]


def test_summarize_indicator_structure_stays_under_250_tokens(mocker) -> None:
    client = mocker.Mock()
    dm = DimensionManager(client)
    dm._cache[127] = [
        Dimension(id=208, name="País__ESTANDAR", members=[Member(id=i, name=f"Country {i}") for i in range(40)]),
        Dimension(id=29117, name="Años__ESTANDAR", members=[Member(id=100 + y, name=str(y)) for y in range(1980, 2026)]),
        Dimension(id=144, name="Sexo__ESTANDAR", members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")]),
    ]
    summary = dm.summarize_indicator_structure(127)
    serialized = json.dumps(summary, ensure_ascii=False)
    assert len(serialized) < 900  # ~220 tokens max
    assert summary["country_count"] == 40
    assert summary["year_range"] == [1980, 2025]
    assert len(summary["breakdown_dimensions"]) == 1
