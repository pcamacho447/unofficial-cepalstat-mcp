from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus


def test_co2_per_capita_emissions_resolves_to_specific_indicator_not_gross_gei() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    resp = engine.resolve("emisiones de co2 per capita en mexico 2019")
    assert resp.status == ResolutionStatus.RESOLVED
    assert resp.selected_candidate is not None
    # Must resolve to 5649 (CO2 por habitante), NEVER 5681 (GEI total con LULUCF)
    assert resp.selected_candidate.indicator_id == 5649
    assert "5681" not in str(resp.selected_candidate.indicator_id)


def test_co2_per_capita_fails_closed_in_official_25_profile() -> None:
    engine = SemanticResolutionEngine(catalog_profile="official_25")
    resp = engine.resolve("emisiones de co2 per capita en mexico 2019")
    # In official_25, 5649 is not in slice, so engine must abstain rather than returning false aggregate 5681
    assert resp.status in (ResolutionStatus.ABSTAINED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    if resp.status == ResolutionStatus.ABSTAINED:
        assert resp.selected_candidate is None or resp.selected_candidate.indicator_id != 5681


def test_gross_vs_net_and_methane_specificity() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    # Methane query should not resolve to gross CO2
    resp_ch4 = engine.resolve("emisiones de metano en colombia 2020")
    if resp_ch4.status == ResolutionStatus.RESOLVED:
        assert "metano" in (resp_ch4.selected_candidate.name.lower() if resp_ch4.selected_candidate else "")
    else:
        assert resp_ch4.status == ResolutionStatus.ABSTAINED
