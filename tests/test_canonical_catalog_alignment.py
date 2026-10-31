from unofficial_cepalstat_mcp.semantic.registry import (
    EMPIRICAL_INDICATOR_ID_MAP,
    OFFICIAL_25_CANONICAL_DEFAULTS,
    VERTICAL_SLICE_INDICATORS,
    SemanticRegistry,
)

FORBIDDEN_SYNTHETIC_IDS = {128, 729, 730, 731, 1241, 1242, 1243, 1244, 1318, 2447, 2928, 2930, 3331, 3344, 4406}


def test_no_synthetic_ids_remain_in_registry_or_defaults() -> None:
    assert EMPIRICAL_INDICATOR_ID_MAP == {}
    assert FORBIDDEN_SYNTHETIC_IDS.isdisjoint(VERTICAL_SLICE_INDICATORS.keys())
    assert FORBIDDEN_SYNTHETIC_IDS.isdisjoint(OFFICIAL_25_CANONICAL_DEFAULTS.values())


def test_colliding_ids_carry_true_cepalstat_definitions() -> None:
    reg = SemanticRegistry()
    # 2203 = corrientes USD; 2204 = constantes USD; 2193 = corrientes MN
    assert "corrientes" in reg.get_indicator(2203).name.lower()
    assert "constantes" in reg.get_indicator(2204).name.lower()
    assert "moneda nacional" in reg.get_indicator(2193).name.lower()
    # 4405 = moneda nacional SOCX; 4410 = gasto publico por funcion % PIB
    assert "moneda nacional" in reg.get_indicator(4405).unit.lower() or "moneda nacional" in reg.get_indicator(4405).name.lower()
    assert reg.get_indicator(4410).unit == "%"
    # 28 = poblacion segun area geografica y sexo; 4992 = % poblacion indigena
    assert "indigena" not in reg.get_indicator(28).name.lower()
    assert "indígena" in reg.get_indicator(4992).name.lower()
    # Multi-rubric indicators declare mandatory_filters
    assert len(reg.get_indicator(1246).mandatory_filters) == 1
    assert "primario" in reg.get_indicator(1246).mandatory_filters[0].member_name.lower()
