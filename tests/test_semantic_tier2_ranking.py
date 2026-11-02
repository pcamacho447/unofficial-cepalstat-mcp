"""Tests for Tier-2 Re-ranking: Length Damping & Headline Prioritization."""

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus


def test_open_employment_query_prioritizes_headline_over_niche_care_series() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    resp = engine.resolve("como le fue al empleo en ecuador 2021")
    # Must resolve or propose alternatives featuring core employment/unemployment, NOT niche 5531
    assert resp.status in (ResolutionStatus.RESOLVED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    top_id = resp.selected_candidate.indicator_id if resp.selected_candidate else None
    # 5531 is "Población fuera del mercado laboral con dedicación exclusiva al trabajo doméstico..."
    assert top_id != 5531, f"Peripheral niche indicator 5531 was ranked top for generic employment query: {resp.selected_candidate}"

    if resp.status == ResolutionStatus.ALTERNATIVE_PROPOSED:
        alt_ids = [alt.indicator_id for alt in resp.alternatives]
        # Core employment indicators (127, 2321, 2329, 3889, 4207, 5095, 5097) should be present
        headline_ids = {127, 2321, 2329, 3889, 4207, 5095, 5097}
        assert (top_id in headline_ids) or any(aid in headline_ids for aid in alt_ids)


def test_headline_indicators_receive_ranking_boost() -> None:
    from unofficial_cepalstat_mcp.catalog.store import CatalogStore
    from unofficial_cepalstat_mcp.semantic.registry import SemanticRegistry

    store = CatalogStore()
    registry = SemanticRegistry(store=store)
    candidates = registry.search_candidates(["desempleo"], top_k=5)
    top_ids = [c[0] for c in candidates]
    # Primary unemployment indicators must be in top 3
    assert any(h_id in top_ids[:3] for h_id in (127, 2329, 3889, 5097))
