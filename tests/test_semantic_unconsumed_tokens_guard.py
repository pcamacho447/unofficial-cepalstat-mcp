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

