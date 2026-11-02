"""Tests for typo suggestions ("Did you mean?") on abstained queries without auto-substitution."""

from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus
from unofficial_cepalstat_mcp.semantic.thesaurus import get_default_thesaurus


def test_thesaurus_suggests_close_matches() -> None:
    thesaurus = get_default_thesaurus()
    assert thesaurus.suggest_correction("pobresa") == "pobreza"
    assert thesaurus.suggest_correction("desocupasion") == "desocupacion"
    assert thesaurus.suggest_correction("inflasion") in ("inflacion", "inflación")
    assert thesaurus.suggest_correction("xyzqwk") is None


def test_engine_abstains_with_did_you_mean_hint_on_typos() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    cases = [
        ("pobresa en guatemala 2020", "pobreza"),
        ("desocupasion en peru 2021", "desocupacion"),
        ("inflasion en colombia 2022", "inflacion"),
    ]
    for query, expected_suggestion in cases:
        resp = engine.resolve(query)
        # Invariant: Must remain ABSTAINED (0.00% FSR)
        assert resp.status == ResolutionStatus.ABSTAINED
        assert resp.abstention_reason == "LOW_CONCEPTUAL_RELEVANCE"
        assert resp.selected_candidate is None
        # Must offer helpful suggestion
        assert "¿quisiste decir" in (resp.conversational_hint or "").lower()
        assert expected_suggestion in (resp.conversational_hint or "").lower()


def test_engine_does_not_suggest_for_hopeless_gibberish() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    resp = engine.resolve("blarghxyz 2022")
    assert resp.status == ResolutionStatus.ABSTAINED
    assert "¿quisiste decir" not in (resp.conversational_hint or "").lower()
