"""Tests for multidimensional breakdowns and facet conmutation."""
import pytest

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus
from unofficial_cepalstat_mcp.semantic.parser import QueryParser


def test_parser_extracts_ethnic_facet():
    parser = QueryParser()

    # Query with general 'etnica' (the user's motivating query)
    intent1 = parser.parse("cual es la pobreza etnica en el peru del 2020")
    assert intent1.root_concept == "POBREZA"
    assert "etnia" in intent1.facets
    assert intent1.facets["etnia"] == "ETNICO_TOTAL"

    # Query with specific 'indigena'
    intent2 = parser.parse("tasa de pobreza indigena en bolivia 2021")
    assert intent2.root_concept == "POBREZA"
    assert intent2.facets.get("etnia") == "INDIGENA"

    # Query with 'afrodescendiente'
    intent3 = parser.parse("pobreza extrema en afrodescendientes en colombia")
    assert intent3.root_concept == "POBREZA"
    assert intent3.facets.get("etnia") == "AFRODESCENDIENTE"

    # Negative check: non-ethnic query has no etnia facet
    intent4 = parser.parse("tasa de desocupacion en chile 2022")
    assert "etnia" not in intent4.facets


def test_member_matcher_resolves_ethnic_dimension():
    from unofficial_cepalstat_mcp.semantic.matcher import DynamicMemberMatcher
    from unofficial_cepalstat_mcp.semantic.registry import DEFAULT_OFFICIAL_DIMENSIONS

    matcher = DynamicMemberMatcher()
    dims_3342 = DEFAULT_OFFICIAL_DIMENSIONS[3342]

    # Test general ethnic facet -> Breakdown across all ethnic members (NEVER collapsed to just 'Total')
    success1, filters1, unhandled1 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "ETNICO_TOTAL", "area": "NACIONAL"}
    )
    assert success1 is True
    assert len(unhandled1) == 0
    ethnic_filter1 = next((f for f in filters1 if f.dim_id == 43039), None)
    assert ethnic_filter1 is not None
    assert ethnic_filter1.is_breakdown is True
    assert ethnic_filter1.member_name != "Total"
    assert {"Afrodescendiente", "Indígena", "No indígena ni afrodescendiente"}.issubset(
        set(ethnic_filter1.member_names)
    )
    assert len(ethnic_filter1.member_ids) >= 3

    # Test specific indigenous facet
    success2, filters2, unhandled2 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "INDIGENA"}
    )
    assert success2 is True
    assert len(unhandled2) == 0
    ethnic_filter2 = next((f for f in filters2 if f.dim_id == 43039), None)
    assert ethnic_filter2 is not None
    assert ethnic_filter2.is_breakdown is False
    assert ethnic_filter2.member_name == "Indígena"

    # Test specific afrodescendant facet
    success3, filters3, unhandled3 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "AFRODESCENDIENTE"}
    )
    assert success3 is True
    assert len(unhandled3) == 0
    ethnic_filter3 = next((f for f in filters3 if f.dim_id == 43039), None)
    assert ethnic_filter3 is not None
    assert ethnic_filter3.is_breakdown is False
    assert ethnic_filter3.member_name == "Afrodescendiente"

    # Test specific no-indigena facet
    success4, filters4, unhandled4 = matcher.match_facets_to_dimensions(
        3342, dims_3342, {"etnia": "NO_INDIGENA"}
    )
    assert success4 is True
    assert len(unhandled4) == 0
    ethnic_filter4 = next((f for f in filters4 if f.dim_id == 43039), None)
    assert ethnic_filter4 is not None
    assert ethnic_filter4.is_breakdown is False
    assert ethnic_filter4.member_name == "No indígena ni afrodescendiente"


def test_engine_resolves_ethnic_poverty_to_3342():
    engine = SemanticResolutionEngine()

    # Exact user query that originally failed
    resp = engine.resolve("cual es la pobreza etnica en el peru del 2020")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 3342
    assert resp.applied_filters.country_code == "PER"
    assert resp.applied_filters.year == 2020

    # Ensure dimension 43039 (Tipo de etnia) is bound as a full breakdown, NOT collapsed to 'Total'
    ethnic_dim = next((f for f in resp.applied_filters.dimensions if f.dim_id == 43039), None)
    assert ethnic_dim is not None
    assert ethnic_dim.is_breakdown is True
    assert ethnic_dim.member_name != "Total"
    assert {"Afrodescendiente", "Indígena", "No indígena ni afrodescendiente"}.issubset(
        set(ethnic_dim.member_names)
    )


def test_critical_facet_never_collapses_to_unrequested_aggregate_member():
    """Fail if any critical facet ends up bound to its aggregate ('Total', 'Nacional', 'Ambos sexos') when not requested."""
    from unofficial_cepalstat_mcp.dimensions import Dimension, Member
    from unofficial_cepalstat_mcp.semantic.matcher import DynamicMemberMatcher

    engine = SemanticResolutionEngine()

    # 1. User's exact extreme ethnic poverty query must return all ethnic members, never just 'Total'
    resp = engine.resolve("cual es la pobreza extrema etnica en el peru del 2020")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 3342

    sev_dim = next((f for f in resp.applied_filters.dimensions if f.dim_id == 1361), None)
    assert sev_dim is not None
    assert sev_dim.member_name == "Pobreza extrema"

    ethnic_dim = next((f for f in resp.applied_filters.dimensions if f.dim_id == 43039), None)
    assert ethnic_dim is not None
    assert ethnic_dim.member_name != "Total", "Critical facet 'etnia' must NEVER collapse to aggregate 'Total'"
    assert ethnic_dim.is_breakdown is True
    assert {"Afrodescendiente", "Indígena", "No indígena ni afrodescendiente"}.issubset(
        set(ethnic_dim.member_names)
    )

    # 2. If a dimension only has an aggregate member ('Total') and lacks actual breakdown members,
    # DynamicMemberMatcher must NOT bind 'Total' for a critical facet request.
    matcher = DynamicMemberMatcher()
    degenerate_dims = [
        Dimension(id=43039, name="Tipo de etnia", members=[Member(id=43043, name="Total")]),
    ]
    ok_gen, filters_gen, unhandled_gen = matcher.match_facets_to_dimensions(
        99999, degenerate_dims, {"etnia": "ETNICO_TOTAL"}
    )
    assert ok_gen is False
    assert "etnia" in unhandled_gen
    assert len(filters_gen) == 0

    ok_spec, filters_spec, unhandled_spec = matcher.match_facets_to_dimensions(
        99999, degenerate_dims, {"etnia": "INDIGENA"}
    )
    assert ok_spec is False
    assert "etnia" in unhandled_spec
    assert len(filters_spec) == 0



def test_engine_resolves_indigenous_poverty_to_3342_with_member():
    engine = SemanticResolutionEngine()
    resp = engine.resolve("tasa de pobreza indigena en bolivia 2021")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 3342
    assert resp.applied_filters.country_code == "BOL"

    # Must bind specific member 'Indígena'
    ethnic_dim = next((f for f in resp.applied_filters.dimensions if f.dim_id == 43039), None)
    assert ethnic_dim is not None
    assert ethnic_dim.member_name == "Indígena"


def test_engine_resolves_afrodescendant_poverty_to_3342_with_member():
    engine = SemanticResolutionEngine()
    resp = engine.resolve("pobreza extrema en afrodescendientes en colombia 2020")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 3342
    assert resp.applied_filters.country_code == "COL"

    # Must bind specific member 'Afrodescendiente'
    ethnic_dim = next((f for f in resp.applied_filters.dimensions if f.dim_id == 43039), None)
    assert ethnic_dim is not None
    assert ethnic_dim.member_name == "Afrodescendiente"


def test_engine_abstains_on_unsupported_facet_without_false_substitution():
    engine = SemanticResolutionEngine()
    # A facet with no breakdown indicator anywhere
    resp = engine.resolve("pobreza monetaria por nivel de coeficiencia intelectual en uruguay")
    assert resp.status == ResolutionStatus.ABSTAINED


def test_fetcher_extracts_ethnic_observation():
    import pandas as pd

    from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
    from unofficial_cepalstat_mcp.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    response = engine.resolve("cual es la pobreza etnica en el peru del 2020")

    # Mock data extractor to verify fetcher dimension member filtering
    mock_df = pd.DataFrame([
        {"iso3": "PER", "Años__ESTANDAR": 2020, "Tipo de etnia": "Total", "Área geográfica": "Nacional", "value": 30.1, "notes_ids": ""},
        {"iso3": "PER", "Años__ESTANDAR": 2020, "Tipo de etnia": "Indígena", "Área geográfica": "Nacional", "value": 45.2, "notes_ids": ""},
        {"iso3": "PER", "Años__ESTANDAR": 2020, "Tipo de etnia": "Afrodescendiente", "Área geográfica": "Nacional", "value": 38.4, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher()
    fetcher._load_indicator_data = lambda ind_id, member_ids=None: mock_df

    data = fetcher.fetch_resolved_data(response)
    assert data["observation_exists"] is True
    assert data["value"] is not None


def test_fetcher_accent_resilient_dimension_filtering():
    import pandas as pd

    from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
    from unofficial_cepalstat_mcp.semantic.fetcher import SemanticDataFetcher

    engine = SemanticResolutionEngine()
    response = engine.resolve("tasa de pobreza indigena en bolivia 2021")

    # Mock data where member in dataframe is unaccented 'Indigena' whereas member_name in response is 'Indígena'
    mock_df = pd.DataFrame([
        {"iso3": "BOL", "Años__ESTANDAR": 2021, "Tipo de etnia": "Indigena", "Área geográfica": "Nacional", "value": 41.5, "notes_ids": ""},
    ])

    fetcher = SemanticDataFetcher()
    fetcher._load_indicator_data = lambda ind_id, member_ids=None: mock_df

    data = fetcher.fetch_resolved_data(response)
    assert data["observation_exists"] is True
    assert data["value"] == 41.5


def test_generic_breakdowns_for_sexo_area_edad_and_deciles():
    """Verify generic breakdown queries ('por sexo', 'por area', 'por edad', 'por deciles') resolve with is_breakdown=True."""
    engine = SemanticResolutionEngine()

    # 1. 'pobreza por sexo' -> swaps 3328 -> 3341 (or 3342) and binds Sexo__ESTANDAR with is_breakdown=True
    r_sexo = engine.resolve("pobreza por sexo en peru 2022")
    assert r_sexo.status == ResolutionStatus.RESOLVED
    assert r_sexo.selected_candidate is not None
    assert r_sexo.selected_candidate.indicator_id in (3341, 3342)
    sexo_dim = next((f for f in r_sexo.applied_filters.dimensions if f.dim_id == 144), None)
    assert sexo_dim is not None
    assert sexo_dim.is_breakdown is True
    assert {"Hombres", "Mujeres"}.issubset(set(sexo_dim.member_names))

    # 2. 'pobreza por area' -> stays on 3328 and binds Área geográfica with is_breakdown=True (not collapsed to Nacional)
    r_area = engine.resolve("pobreza por area en peru 2022")
    assert r_area.status == ResolutionStatus.RESOLVED
    assert r_area.selected_candidate is not None
    assert r_area.selected_candidate.indicator_id == 3328
    area_dim = next((f for f in r_area.applied_filters.dimensions if f.dim_id == 326), None)
    assert area_dim is not None
    assert area_dim.is_breakdown is True
    assert {"Urbano", "Rural"}.issubset(set(area_dim.member_names))

    # 3. 'pobreza por edad' -> swaps 3328 -> 3341 and binds Grupo de edad with is_breakdown=True
    r_edad = engine.resolve("pobreza por edad en peru 2022")
    assert r_edad.status == ResolutionStatus.RESOLVED
    assert r_edad.selected_candidate is not None
    assert r_edad.selected_candidate.indicator_id == 3341
    edad_dim = next((f for f in r_edad.applied_filters.dimensions if f.dim_id == 43054), None)
    assert edad_dim is not None
    assert edad_dim.is_breakdown is True
    assert len(edad_dim.member_names) >= 3

    # 4. 'distribucion del ingreso por deciles' -> binds Estrato de ingreso with is_breakdown=True
    r_decil = engine.resolve("distribucion del ingreso por deciles en peru 2022")
    assert r_decil.status == ResolutionStatus.RESOLVED
    assert r_decil.selected_candidate is not None
    assert r_decil.selected_candidate.indicator_id == 3340
    decil_dim = next((f for f in r_decil.applied_filters.dimensions if f.dim_id == 600), None)
    assert decil_dim is not None
    assert decil_dim.is_breakdown is True
    assert {"Primer decil", "Décimo decil", "Deciles"}.issubset(set(decil_dim.member_names))


def test_ethnic_population_query_with_demonym_resolves_to_indigenous_population_breakdown():
    """Verify 'necesito datos etnicos de la poblacion peruana' extracts PER from 'peruana' and resolves to 4968 with ethnic breakdown."""
    from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
    from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus

    engine = SemanticResolutionEngine()

    res = engine.resolve("necesito datos etnicos de la poblacion peruana")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.applied_filters.country_code == "PER"
    assert res.applied_filters.country_name == "Perú"
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4968
    assert res.applied_filters.facets.get("etnia") == "ETNICO_TOTAL"
    etnia_dims = [
        d for d in res.applied_filters.dimensions
        if "indígena" in d.dim_name.lower() or "etnia" in d.dim_name.lower()
    ]
    assert len(etnia_dims) == 1
    assert etnia_dims[0].is_breakdown is True
    assert "Indígena" in etnia_dims[0].member_names


def test_specific_population_queries_route_to_total_indigenous_and_afrodescendant_indicators():
    """Verify total, indigenous, and afrodescendant population queries resolve to 4788, 4968, and 4969."""
    from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
    from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus

    engine = SemanticResolutionEngine()

    res_tot = engine.resolve("poblacion total de chile en 2022")
    assert res_tot.status == ResolutionStatus.RESOLVED
    assert res_tot.selected_candidate is not None
    assert res_tot.selected_candidate.indicator_id == 4788
    assert res_tot.applied_filters.country_code == "CHL"

    res_ind = engine.resolve("poblacion indigena en bolivia")
    assert res_ind.status == ResolutionStatus.RESOLVED
    assert res_ind.selected_candidate is not None
    assert res_ind.selected_candidate.indicator_id == 4968
    assert res_ind.applied_filters.country_code == "BOL"

    res_afro = engine.resolve("poblacion afrodescendiente en brasil")
    assert res_afro.status == ResolutionStatus.RESOLVED
    assert res_afro.selected_candidate is not None
    assert res_afro.selected_candidate.indicator_id == 4969
    assert res_afro.applied_filters.country_code == "BRA"


@pytest.fixture
def engine():
    from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine

    return SemanticResolutionEngine()


def test_poblacion_por_quintil_y_etnia_routes_to_indicator_4639(engine):
    """Assert 'poblacion indigena por quintil en peru 2021' routes to 4639, not 3340."""
    from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus

    res = engine.resolve("poblacion indigena por quintil en peru 2021")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4639
    assert res.applied_filters.country_code == "PER"


def test_poblacion_especifica_afrodescendiente_no_bloqueada_por_etnico_total(engine):
    """Assert 'poblacion del grupo etnico afrodescendiente en brasil 2020' routes to 4969."""
    from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus

    res = engine.resolve("poblacion del grupo etnico afrodescendiente en brasil 2020")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4969


def test_poblacion_por_area_urbana_rural_routes_to_indicator_4992(engine):
    """Assert 'poblacion por area urbana y rural en colombia 2022' routes to 4992."""
    from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus

    res = engine.resolve("poblacion por area en colombia 2022")
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 4992




