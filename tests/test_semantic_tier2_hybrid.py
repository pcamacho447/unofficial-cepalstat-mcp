from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus
from unofficial_cepalstat_mcp.semantic.registry import SemanticRegistry


def _full_engine(tmp_path, monkeypatch) -> SemanticResolutionEngine:
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(tmp_path / ".statscepal_cache.db"))
    store = CatalogStore()
    return SemanticResolutionEngine(registry=SemanticRegistry(store=store), catalog_profile="full_catalog")


def test_tier2_resolves_uncurated_catalog_indicators_and_competing_alternatives(tmp_path, monkeypatch) -> None:
    engine = _full_engine(tmp_path, monkeypatch)
    # Uncurated catalog indicator (e.g. wholesale price index 544 or literacy 5683)
    r_ipm = engine.resolve("índice de precios al por mayor en Chile 2022")
    assert r_ipm.status == ResolutionStatus.RESOLVED
    assert r_ipm.selected_candidate is not None
    assert r_ipm.selected_candidate.indicator_id == 544

    # Competing series (e.g. exportaciones de bienes -> multiple compatible tables)
    r_exp = engine.resolve("exportaciones de bienes en Chile 2022")
    assert r_exp.status in (ResolutionStatus.RESOLVED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    if r_exp.status == ResolutionStatus.ALTERNATIVE_PROPOSED:
        assert 1 <= len(r_exp.alternatives) <= 4
        assert len(r_exp.conversational_hint or "") < 600


def test_tier2_never_substitutes_adversarial_queries(tmp_path, monkeypatch) -> None:
    engine = _full_engine(tmp_path, monkeypatch)
    for adv in [
        "precio del bitcoin en El Salvador 2023",
        "pobreza por coeficiente intelectual en Chile 2022",
        "inflación anual en Francia 2022",
    ]:
        resp = engine.resolve(adv)
        assert resp.status == ResolutionStatus.ABSTAINED


def test_specificity_guard_rejects_missing_facets_without_loss(tmp_path, monkeypatch) -> None:
    engine = _full_engine(tmp_path, monkeypatch)
    # Query specifies 'rural', but indicator 2204 (PIB) has no geographic area breakdown
    res = engine.resolve("pib total nacional rural a precios constantes")
    assert res.status == ResolutionStatus.ABSTAINED
    assert "area" in res.unmatched_facets
    assert res.indicator_id is None  # 0.00% FSR enforced


def test_facet_ontology_validate_dimensions() -> None:
    from unofficial_cepalstat_mcp.dimensions import Dimension, Member
    from unofficial_cepalstat_mcp.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY

    dims = [
        Dimension(id=144, name="Sexo", members=[Member(id=266, name="Mujeres")]),
        Dimension(id=208, name="País__ESTANDAR", members=[]),
    ]

    assert DEFAULT_FACET_ONTOLOGY.validate_dimensions(dims, {"sexo"}) is True
    assert DEFAULT_FACET_ONTOLOGY.validate_dimensions(dims, set()) is True
    assert DEFAULT_FACET_ONTOLOGY.validate_dimensions(dims, {"area"}) is False
    assert DEFAULT_FACET_ONTOLOGY.validate_dimensions(dims, {"sexo", "area"}) is False


def test_specificity_guard_unit_evaluation() -> None:
    from unofficial_cepalstat_mcp.catalog.models import CatalogCandidate
    from unofficial_cepalstat_mcp.dimensions import Dimension, Member
    from unofficial_cepalstat_mcp.semantic.evaluator import SpecificityGuard

    guard = SpecificityGuard()

    # 1. Candidate with only country and year (no sex, area, age)
    c_national = CatalogCandidate(
        indicator_id=2204,
        name="PIB total anual",
        score=10.0,
        dimensions=[
            Dimension(id=208, name="País__ESTANDAR", members=[Member(id=1, name="Chile")]),
            Dimension(id=209, name="Años__ESTANDAR", members=[Member(id=2022, name="2022")]),
        ],
    )

    # 2. Candidate with Sexo breakdown, but NO aggregate total member (only Mujeres, Hombres)
    c_sex_no_total = CatalogCandidate(
        indicator_id=9901,
        name="Tasa de empleo desagregada por sexo",
        score=8.0,
        dimensions=[
            Dimension(
                id=144,
                name="Sexo",
                members=[Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
            )
        ],
    )

    # 3. Candidate with Sexo breakdown AND aggregate total member
    c_sex_with_total = CatalogCandidate(
        indicator_id=127,
        name="Tasa de desocupación por sexo",
        score=8.5,
        dimensions=[
            Dimension(
                id=144,
                name="Sexo",
                members=[
                    Member(id=264, name="Total"),
                    Member(id=265, name="Hombres"),
                    Member(id=266, name="Mujeres"),
                ],
            )
        ],
    )

    # 4. Competing candidate with similar score
    c_sex_competing = CatalogCandidate(
        indicator_id=128,
        name="Tasa de desocupación nacional abierta",
        score=8.3,
        dimensions=[
            Dimension(
                id=144,
                name="Sexo",
                members=[
                    Member(id=264, name="Total"),
                    Member(id=265, name="Hombres"),
                    Member(id=266, name="Mujeres"),
                ],
            )
        ],
    )

    # Test A: Zero Facet Loss - requesting area on national candidate -> ABSTAINED
    res_area = guard.evaluate([c_national], intent_facets={"area": "RURAL"})
    assert res_area.status == ResolutionStatus.ABSTAINED
    assert "area" in res_area.unmatched_facets
    assert res_area.selected_candidate is None

    # Test B: Aggregate query with series exclusively disaggregated without total -> ABSTAINED
    res_agg = guard.evaluate([c_sex_no_total], intent_facets={}, require_aggregate=True)
    assert res_agg.status == ResolutionStatus.ABSTAINED
    assert res_agg.is_aggregate_conflict is True
    assert res_agg.selected_candidate is None

    # Test C: Single candidate covering all facets -> RESOLVED
    res_resolved = guard.evaluate([c_sex_with_total], intent_facets={"sexo": "FEMENINO"})
    assert res_resolved.status == ResolutionStatus.RESOLVED
    assert res_resolved.selected_candidate is not None
    assert res_resolved.selected_candidate.indicator_id == 127
    assert len(res_resolved.alternatives) == 0

    # Test D: Competing candidates with close scores -> ALTERNATIVE_PROPOSED with payload < 250 tokens
    res_alt = guard.evaluate([c_sex_with_total, c_sex_competing], intent_facets={"sexo": "TOTAL"})
    assert res_alt.status == ResolutionStatus.ALTERNATIVE_PROPOSED
    assert res_alt.selected_candidate is not None
    assert res_alt.selected_candidate.indicator_id == 127
    assert len(res_alt.alternatives) == 1
    assert res_alt.alternatives[0].indicator_id == 128
    assert res_alt.payload_token_count < 250
