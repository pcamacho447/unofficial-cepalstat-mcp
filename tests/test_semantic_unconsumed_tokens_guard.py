"""Tests for Unconsumed Semantic Tokens Guard and currency/area collision fix."""

from statscepal.semantic.parser import QueryParser


def test_moneda_nacional_does_not_trigger_area_nacional_facet():
    """Verify currency expressions do not trigger geographic area facet NACIONAL."""
    parser = QueryParser()

    # Base query from brief: "ingresos tributarios del peru en moneda nacional en 2022"
    intent1 = parser.parse("ingresos tributarios del peru en moneda nacional en 2022")
    assert "area" not in intent1.facets, f"Expected no area facet, got {intent1.facets}"

    # Currency variants
    intent2 = parser.parse("recaudacion tributaria en chile en moneda nacional")
    assert "area" not in intent2.facets, f"Expected no area facet, got {intent2.facets}"

    intent3 = parser.parse("gasto publico en mexico en moneda local")
    assert "area" not in intent3.facets, f"Expected no area facet, got {intent3.facets}"

    intent4 = parser.parse("pib corriente de colombia en moneda nacional")
    assert "area" not in intent4.facets, f"Expected no area facet, got {intent4.facets}"


def test_explicit_area_nacional_triggers_area_facet():
    """Verify explicit area phrases still trigger area=NACIONAL even with currency terms."""
    parser = QueryParser()

    # Explicit national area phrases
    intent1 = parser.parse("pobreza a nivel nacional en colombia en 2020")
    assert intent1.facets.get("area") == "NACIONAL", f"Expected area=NACIONAL, got {intent1.facets}"

    intent2 = parser.parse("tasa de desocupacion en el total nacional en chile")
    assert intent2.facets.get("area") == "NACIONAL", f"Expected area=NACIONAL, got {intent2.facets}"

    intent3 = parser.parse("medicion en todo el pais para ecuador")
    assert intent3.facets.get("area") == "NACIONAL", f"Expected area=NACIONAL, got {intent3.facets}"

    # Query with currency expression AND explicit national area phrase
    intent4 = parser.parse("ingresos en moneda nacional a nivel nacional en peru")
    assert intent4.facets.get("area") == "NACIONAL", f"Expected area=NACIONAL, got {intent4.facets}"


def test_unconsumed_tokens_extraction_on_domain_modifiers():
    """Verify that unparsed domain-specific modifiers are extracted into unconsumed_tokens."""
    parser = QueryParser()

    # 1. Clean query with no modifiers
    intent1 = parser.parse("pib per capita de bolivia en 2020")
    assert intent1.unconsumed_tokens == [], f"Expected empty, got {intent1.unconsumed_tokens}"

    # 2. Poverty baseline
    intent2 = parser.parse("tasa de pobreza en colombia")
    assert intent2.unconsumed_tokens == [], f"Expected empty, got {intent2.unconsumed_tokens}"

    # 3. Manufacturing modifier
    intent3 = parser.parse("valor agregado manufacturero por habitante en mexico")
    assert "manufacturero" in intent3.unconsumed_tokens, f"Expected 'manufacturero' in {intent3.unconsumed_tokens}"

    # 4. Agricultural modifier
    intent4 = parser.parse("salario minimo agricola en guatemala")
    assert "agricola" in intent4.unconsumed_tokens, f"Expected 'agricola' in {intent4.unconsumed_tokens}"

    # 5. Expenditure component modifier
    intent5 = parser.parse("pib trimestral por componente del gasto en brasil")
    assert "componente" in intent5.unconsumed_tokens and "gasto" in intent5.unconsumed_tokens, (
        f"Expected expenditure tokens in {intent5.unconsumed_tokens}"
    )

    # 6. Currency expression clean query
    intent6 = parser.parse("ingresos tributarios del peru en moneda nacional en 2022")
    assert intent6.unconsumed_tokens == [], f"Expected empty, got {intent6.unconsumed_tokens}"


def test_guard_prevents_false_substitution_on_manufacturing_gdp():
    """Verify that unconsumed 'manufacturero' prevents resolving as aggregate GDP per capita (730)."""
    from statscepal.semantic import ResolutionStatus, SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    resp = engine.resolve("valor agregado manufacturero por habitante en mexico")
    assert resp.status in (ResolutionStatus.ABSTAINED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    assert resp.selected_candidate is None or resp.selected_candidate.relevance_score <= 0.70
    assert "manufacturero" in (resp.conversational_hint or "") or "manufacturero" in (resp.abstention_reason or "")


def test_guard_downgrades_on_agricultural_minimum_wage():
    """Verify that unconsumed 'agricola' downgrades minimum wage candidate from 1.0 to ALTERNATIVE_PROPOSED."""
    from statscepal.semantic import ResolutionStatus, SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    resp = engine.resolve("salario minimo agricola en guatemala")
    assert resp.status in (ResolutionStatus.ALTERNATIVE_PROPOSED, ResolutionStatus.ABSTAINED)
    if resp.status == ResolutionStatus.ALTERNATIVE_PROPOSED:
        assert resp.selected_candidate is not None
        assert resp.selected_candidate.relevance_score <= 0.70
        assert "agricola" in (resp.conversational_hint or "").lower()


def test_guard_prevents_false_substitution_on_quarterly_gdp_expenditure():
    """Verify that unconsumed expenditure tokens prevent false 1.0 resolution on quarterly GDP."""
    from statscepal.semantic import ResolutionStatus, SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    resp = engine.resolve("pib trimestral por componente del gasto en brasil")
    assert resp.status in (ResolutionStatus.ABSTAINED, ResolutionStatus.ALTERNATIVE_PROPOSED)
    assert resp.selected_candidate is None or resp.selected_candidate.indicator_id != 731 or resp.selected_candidate.relevance_score < 1.0


def test_guard_preserves_canonical_queries():
    """Verify that canonical queries with no unconsumed modifiers resolve cleanly with score 1.0."""
    from statscepal.semantic import ResolutionStatus, SemanticResolutionEngine

    engine = SemanticResolutionEngine()

    resp1 = engine.resolve("pib per capita de bolivia en 2020")
    assert resp1.status == ResolutionStatus.RESOLVED
    assert resp1.selected_candidate is not None
    assert resp1.selected_candidate.indicator_id == 730
    assert resp1.selected_candidate.relevance_score == 1.0

    resp2 = engine.resolve("tasa de pobreza en colombia")
    assert resp2.status == ResolutionStatus.RESOLVED
    assert resp2.selected_candidate is not None
    assert resp2.selected_candidate.indicator_id == 3328
    assert resp2.selected_candidate.relevance_score == 1.0


def test_token_coverage_does_not_falsely_match_substrings():
    """Verify that short tokens like 'iva' do not match inside words like 'privada'."""
    from statscepal.semantic.engine import _is_token_covered_by_indicator
    from statscepal.semantic.registry import IndicatorMetadata

    mock_meta = IndicatorMetadata(
        indicator_id=9999,
        name="Inversion privada y actividad productiva",
        concept="INVERSION",
        measure_type="PORCENTAJE",
        unit="%",
        supported_facets=set(),
    )
    # 'iva' is a substring of privada and productiva, but as a word it is NOT covered
    assert not _is_token_covered_by_indicator("iva", mock_meta, None)


def test_token_coverage_matches_spanish_gender_inflections():
    """Verify that Spanish gender inflections (agropecuario/agropecuaria) match properly."""
    from statscepal.semantic.engine import _is_token_covered_by_indicator
    from statscepal.semantic.registry import IndicatorMetadata

    mock_meta = IndicatorMetadata(
        indicator_id=9999,
        name="Produccion del sector agropecuario",
        concept="PRODUCCION",
        measure_type="INDICE",
        unit="indice",
        supported_facets=set(),
    )
    assert _is_token_covered_by_indicator("agropecuaria", mock_meta, None)
    assert _is_token_covered_by_indicator("agropecuarios", mock_meta, None)
    assert _is_token_covered_by_indicator("agropecuarias", mock_meta, None)


def test_government_consumption_triggers_unresolved_specificity():
    """Verify that ADV_B09 (consumo final del gobierno) resolves to UNRESOLVED_SPECIFICITY and forbids 729."""
    from statscepal.semantic import ResolutionStatus, SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    resp = engine.resolve("gasto en consumo final del gobierno en bolivia")
    assert resp.status == ResolutionStatus.ABSTAINED
    assert resp.selected_candidate is None
    assert "UNRESOLVED_SPECIFICITY" in str(resp.abstention_reason)


def test_medication_and_health_expenditure_proposes_alternative_4405():
    """Verify that ADV_A09 proposes aggregate social expenditure 4405 with score 0.65."""
    from statscepal.semantic import ResolutionStatus, SemanticResolutionEngine

    engine = SemanticResolutionEngine()
    resp = engine.resolve("gasto publico en medicamentos y salud en argentina")
    assert resp.status == ResolutionStatus.ALTERNATIVE_PROPOSED
    assert resp.selected_candidate is not None
    assert resp.selected_candidate.indicator_id == 4405
    assert resp.selected_candidate.relevance_score == 0.65
    assert "medicamentos" in str(resp.conversational_hint)


