from unofficial_cepalstat_mcp.semantic.engine import SemanticResolutionEngine
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus


def test_non_lac_countries_emit_explicit_geographic_abstention_reason() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    cases = [
        ("pib de alemania 2022", "UNSUPPORTED_COUNTRY_NON_LAC_DEU", "Alemania"),
        ("tasa de paro en espana 2022", "UNSUPPORTED_COUNTRY_NON_LAC_ESP", "España"),
        ("inflacion en francia 2021", "UNSUPPORTED_COUNTRY_NON_LAC_FRA", "Francia"),
        ("pobreza extrema en estados unidos 2020", "UNSUPPORTED_COUNTRY_NON_LAC_USA", "Estados Unidos"),
        ("poblacion de japon 2022", "UNSUPPORTED_COUNTRY_NON_LAC_JPN", "Japón"),
        ("balanza comercial de italia 2020", "UNSUPPORTED_COUNTRY_NON_LAC_ITA", "Italia"),
    ]
    for query, expected_reason, expected_country_hint in cases:
        resp = engine.resolve(query)
        assert resp.status == ResolutionStatus.ABSTAINED, f"Failed for '{query}': {resp.status}"
        assert resp.abstention_reason == expected_reason, f"Failed reason for '{query}': {resp.abstention_reason}"
        assert resp.unsupported_facet == expected_reason
        assert expected_country_hint.lower() in (resp.conversational_hint or "").lower()
        assert "fuera del ambito geografico" in (resp.conversational_hint or "").lower() or "fuera del ámbito geográfico" in (resp.conversational_hint or "").lower()


def test_daily_financial_queries_emit_informative_frequency_and_domain_hint() -> None:
    engine = SemanticResolutionEngine(catalog_profile="full_catalog")
    resp = engine.resolve("precio del dolar en peru hoy")
    assert resp.status == ResolutionStatus.ABSTAINED
    assert resp.abstention_reason in ("UNSUPPORTED_FREQUENCY", "OUT_OF_SCOPE_DAILY_FINANCIAL")
    assert "tiempo real" in (resp.conversational_hint or "").lower() or "diaria" in (resp.conversational_hint or "").lower() or "periodicidad" in (resp.conversational_hint or "").lower()
