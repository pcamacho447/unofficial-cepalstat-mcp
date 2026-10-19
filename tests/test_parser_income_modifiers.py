"""Unit and integration tests for income modifiers, regionalisms, and composite precedence."""

import pytest
from unofficial_cepalstat_mcp.semantic import (
    QueryParser,
    ResolutionStatus,
    SemanticResolutionEngine,
)
from unofficial_cepalstat_mcp.semantic.matcher import DynamicMemberMatcher


@pytest.fixture
def parser() -> QueryParser:
    return QueryParser()


@pytest.fixture
def engine() -> SemanticResolutionEngine:
    return SemanticResolutionEngine()


# ---------------------------------------------------------------------------
# 1. Income Modifier Deconstruction
# ---------------------------------------------------------------------------


def test_income_modifier_minimum_wage(parser: QueryParser, engine: SemanticResolutionEngine):
    """Context modifier 'minima/minimo/por ley/sueldo basico' -> SALARIO_MINIMO -> Indicator 3337."""
    queries = [
        "Cuál fue la guita mínima por ley en Chile en 2022",
        "Salario mínimo real en Brasil en 2022",
        "Salario básico de ley en Uruguay en 2022",
        "Sueldo básico por ley en Argentina en 2021",
    ]
    for q in queries:
        intent = parser.parse(q)
        assert intent.root_concept == "SALARIO_MINIMO", f"Failed for query: {q}"
        assert not intent.is_ambiguous_measure

        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id == 3337


def test_income_modifier_average_real_wage(parser: QueryParser, engine: SemanticResolutionEngine):
    """Context modifier 'laburantes/trabajadores/medio/remuneraciones/promedio' -> SALARIO_REAL/SALARIO_MEDIO -> Indicator 128."""
    queries = [
        ("La guita de los laburantes en Argentina en 2021", 2021, "ARG"),
        ("La lana de los trabajadores en México en 2021", 2021, "MEX"),
        ("Salario promedio real en Perú en 2020", 2020, "PER"),
        ("Salario medio real en Chile en 2021", 2021, "CHL"),
        ("Índice del salario medio real en Argentina en 2021", 2021, "ARG"),
        ("Remuneraciones medias reales en Brasil en 2022", 2022, "BRA"),
    ]
    for q, year, ccode in queries:
        intent = parser.parse(q)
        assert intent.root_concept in {"SALARIO_REAL", "SALARIO_MEDIO"}, f"Failed root_concept for query: {q}"
        assert not intent.is_ambiguous_measure
        assert intent.year == year
        assert intent.country_code == ccode

        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id == 128


def test_income_modifier_household_per_capita(parser: QueryParser, engine: SemanticResolutionEngine):
    """Context modifier 'hogares/familias/por cabeza/per capita' -> INGRESO_HOGAR_PER_CAPITA / INGRESO_HOGARES -> Indicator 3345."""
    queries = [
        "Cuál es la plata de los hogares por cabeza en Colombia en 2020",
        "Ingreso medio per cápita de los hogares en Colombia en 2021",
        "Ingreso per cápita de las familias en Costa Rica en 2021",
        "La plata de las familias en Chile en 2022",
    ]
    for q in queries:
        intent = parser.parse(q)
        assert intent.root_concept in {"INGRESO_HOGAR_PER_CAPITA", "INGRESO_HOGARES"}, f"Failed root_concept for query: {q}"
        assert not intent.is_ambiguous_measure

        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id == 3345


def test_income_modifier_labor_income_breakdown(parser: QueryParser, engine: SemanticResolutionEngine):
    """Dimensional breakdown 'campo/rural' or 'mujeres/hombres' with labor income -> Indicator 3339."""
    queries = [
        ("Ingreso laboral medio en México en 2020", {}),
        ("Ingreso laboral medio de las mujeres en México en 2020", {"sexo": "FEMENINO"}),
        ("Ingreso laboral medio en el campo en Brasil en 2021", {"area": "RURAL"}),
        ("Ingreso laboral de hombres rurales en Colombia en 2021", {"sexo": "MASCULINO", "area": "RURAL"}),
        ("Ingreso laboral medio de hombres en zona rural de México en 2020", {"sexo": "MASCULINO", "area": "RURAL"}),
    ]
    for q, expected_facets in queries:
        intent = parser.parse(q)
        assert intent.root_concept == "INGRESO_LABORAL", f"Failed root_concept for: {q}"
        for f_k, f_v in expected_facets.items():
            assert intent.facets.get(f_k) == f_v, f"Facet {f_k} mismatch for {q}"

        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id == 3339


def test_income_modifier_household_rural_breakdown(parser: QueryParser, engine: SemanticResolutionEngine):
    """Household income with rural breakdown -> Indicator 3345 with area=RURAL."""
    q = "Ingreso de las familias en el área rural en Chile en 2022"
    intent = parser.parse(q)
    assert intent.root_concept in {"INGRESO_HOGAR_PER_CAPITA", "INGRESO_HOGARES"}
    assert intent.facets.get("area") == "RURAL"

    res = engine.resolve(q)
    assert res.status == ResolutionStatus.RESOLVED
    assert res.selected_candidate is not None
    assert res.selected_candidate.indicator_id == 3345
    assert res.applied_filters.facets.get("area") == "RURAL"


def test_unmodified_slang_income_ambiguity(parser: QueryParser, engine: SemanticResolutionEngine):
    """Unmodified slang ('guita en Chile en 2021', 'cuanta plata en Colombia 2020', 'ingreso en Mexico 2022')

    -> is_ambiguous_measure = True, ambiguous_candidate = 'INCOME_MEASURES',
    status ALTERNATIVE_PROPOSED, primary candidate 128, proposing alternatives [3337, 3345].
    """
    queries = [
        "Cómo estuvo la guita en Chile en 2021",
        "Cuánta plata en Colombia en 2020",
        "Cuál fue el ingreso en México en 2022",
        "Ingreso en México 2022",
    ]
    for q in queries:
        intent = parser.parse(q)
        assert intent.is_ambiguous_measure is True, f"Failed ambiguity flag for {q}"
        assert intent.ambiguous_candidate == "INCOME_MEASURES", f"Failed candidate for {q}"

        res = engine.resolve(q)
        assert res.status == ResolutionStatus.ALTERNATIVE_PROPOSED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id == 128
        alt_ids = [alt.indicator_id for alt in res.alternatives]
        assert 3337 in alt_ids, f"3337 missing in alternatives {alt_ids} for {q}"
        assert 3345 in alt_ids, f"3345 missing in alternatives {alt_ids} for {q}"


# ---------------------------------------------------------------------------
# 2. Expanded Regionalisms
# ---------------------------------------------------------------------------


def test_regionalisms_chilean(parser: QueryParser, engine: SemanticResolutionEngine):
    """Chilean slang: pega (empleo), lucas (ingreso), cabros (edad=JUVENTUD)."""
    # 1. cabros + sin pega -> youth unemployment -> 3331
    q1 = "Cuántos cabros están sin pega en Chile en 2022"
    intent1 = parser.parse(q1)
    assert intent1.facets.get("edad") == "JUVENTUD"
    res1 = engine.resolve(q1)
    assert res1.status == ResolutionStatus.RESOLVED
    assert res1.selected_candidate is not None
    assert res1.selected_candidate.indicator_id == 3331

    # 2. lucas de los laburantes -> 128
    q2 = "Las lucas de los trabajadores en Chile en 2021"
    intent2 = parser.parse(q2)
    assert intent2.root_concept in {"SALARIO_REAL", "SALARIO_MEDIO"}
    res2 = engine.resolve(q2)
    assert res2.status == ResolutionStatus.RESOLVED
    assert res2.selected_candidate is not None
    assert res2.selected_candidate.indicator_id == 128

    # 3. lucas unmodified -> ambiguous
    q3 = "Cómo estuvieron las lucas en Chile en 2021"
    intent3 = parser.parse(q3)
    assert intent3.is_ambiguous_measure is True
    assert intent3.ambiguous_candidate == "INCOME_MEASURES"
    res3 = engine.resolve(q3)
    assert res3.status == ResolutionStatus.ALTERNATIVE_PROPOSED
    assert res3.selected_candidate.indicator_id == 128


def test_regionalisms_rioplatense(parser: QueryParser, engine: SemanticResolutionEngine):
    """Rioplatense slang: guita (ingreso), laburantes/laburo (salario/trabajo), pibes/pibas (edad=JUVENTUD, sexo)."""
    # 1. pibas en pobreza
    q1 = "Pobreza de las pibas en México en 2020"
    intent1 = parser.parse(q1)
    assert intent1.facets.get("sexo") == "FEMENINO"
    assert intent1.facets.get("edad") == "JUVENTUD"
    res1 = engine.resolve(q1)
    assert res1.status == ResolutionStatus.RESOLVED
    assert res1.selected_candidate.indicator_id == 3341

    # 2. desocupación de los pibes -> 3331
    q2 = "Desocupación de los pibes en Argentina en 2021"
    intent2 = parser.parse(q2)
    assert intent2.facets.get("edad") == "JUVENTUD"
    res2 = engine.resolve(q2)
    assert res2.status == ResolutionStatus.RESOLVED
    assert res2.selected_candidate.indicator_id == 3331

    # 3. laburo sin empleo -> 127
    q3 = "Gente sin laburo en Argentina en 2021"
    intent3 = parser.parse(q3)
    assert intent3.root_concept == "EMPLEO"
    res3 = engine.resolve(q3)
    assert res3.status == ResolutionStatus.RESOLVED
    assert res3.selected_candidate.indicator_id == 127


def test_regionalisms_mexican(parser: QueryParser, engine: SemanticResolutionEngine):
    """Mexican slang: chamba (empleo), lana (ingreso), chavos/chavas (edad=JUVENTUD, sexo)."""
    # 1. falta de chamba -> 127
    q1 = "Falta de chamba en México en 2022"
    intent1 = parser.parse(q1)
    assert intent1.root_concept == "EMPLEO"
    res1 = engine.resolve(q1)
    assert res1.status == ResolutionStatus.RESOLVED
    assert res1.selected_candidate.indicator_id == 127

    # 2. cuánta raza no tiene chamba ni jale
    q2 = "Cuánta raza no tiene chamba ni jale en México en 2022"
    intent2 = parser.parse(q2)
    assert intent2.root_concept == "EMPLEO"
    res2 = engine.resolve(q2)
    assert res2.status == ResolutionStatus.RESOLVED
    assert res2.selected_candidate.indicator_id == 127

    # 3. chavos sin chamba -> 3331
    q3 = "Chavos sin chamba en México en 2020"
    intent3 = parser.parse(q3)
    assert intent3.facets.get("edad") == "JUVENTUD"
    res3 = engine.resolve(q3)
    assert res3.status == ResolutionStatus.RESOLVED
    assert res3.selected_candidate.indicator_id == 3331


def test_regionalisms_colombian_andean(parser: QueryParser, engine: SemanticResolutionEngine):
    """Colombian/Andean slang: camello (empleo), corrientazo (alimentos/IPC), plata (ingreso)."""
    # 1. camello -> empleo 127
    q1 = "Gente sin camello en Colombia en 2021"
    intent1 = parser.parse(q1)
    assert intent1.root_concept == "EMPLEO"
    res1 = engine.resolve(q1)
    assert res1.status == ResolutionStatus.RESOLVED
    assert res1.selected_candidate.indicator_id == 127

    # 2. corrientazo -> IPC alimentos 2929
    q2 = "Inflación del corrientazo en Colombia en 2022"
    intent2 = parser.parse(q2)
    assert intent2.root_concept in {"IPC_ALIMENTOS", "INFLACION_ALIMENTOS"}
    res2 = engine.resolve(q2)
    assert res2.status == ResolutionStatus.RESOLVED
    assert res2.selected_candidate.indicator_id in {2929, 1684}


# ---------------------------------------------------------------------------
# 3. Composite Precedence Safeguards
# ---------------------------------------------------------------------------


def test_composite_precedence_debt(parser: QueryParser, engine: SemanticResolutionEngine):
    """Debt as % of GDP must not be shadowed by PIB (729)."""
    queries = [
        "Saldo de la deuda pública en porcentaje del PIB en Brasil en 2021",
        "Deuda del gobierno central en porcentaje del PIB en Colombia en 2021",
        "Deuda pública sobre el PIB en Uruguay en 2021",
        "Saldo de la deuda pública sobre el PIB en Argentina en 2020",
        "Endeudamiento soberano como porcentaje del PIB en México en 2021",
    ]
    for q in queries:
        intent = parser.parse(q)
        assert intent.root_concept == "DEUDA_PUBLICA", f"Shadowed by PIB for query: {q}"
        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id == 1240


def test_composite_precedence_primary_balance(parser: QueryParser, engine: SemanticResolutionEngine):
    """Primary balance as % of GDP must not be shadowed by PIB (729)."""
    queries = [
        "Balance primario del gobierno central en porcentaje del PIB en México en 2020",
        "Balance primario fiscal en Costa Rica en 2022",
    ]
    for q in queries:
        intent = parser.parse(q)
        assert intent.root_concept == "BALANCE_PRIMARIO", f"Shadowed by PIB for query: {q}"
        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id == 1241


def test_composite_precedence_tax_revenues(parser: QueryParser, engine: SemanticResolutionEngine):
    """Tax revenues as % of GDP must not be shadowed by PIB (729)."""
    queries = [
        "Ingresos tributarios como porcentaje del PIB en Chile en 2022",
        "Recaudación tributaria sobre el PIB en Perú en 2022",
        "La plata que le entra a la DIAN como porcentaje del PIB en Colombia en 2022",
        "Carga tributaria del gobierno central en Brasil en 2021",
        "Presión fiscal tributaria en Colombia en 2020",
    ]
    for q in queries:
        intent = parser.parse(q)
        assert intent.root_concept == "INGRESOS_TRIBUTARIOS", f"Shadowed by PIB for query: {q}"
        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id == 1242


def test_composite_precedence_current_account(parser: QueryParser, engine: SemanticResolutionEngine):
    """Current account as % of GDP must not be shadowed by PIB (729)."""
    queries = [
        "Saldo en cuenta corriente de la balanza de pagos en porcentaje del PIB en Brasil en 2021",
        "Cuenta corriente sobre el PIB en Chile en 2022",
        "Balanza en cuenta corriente como porcentaje del PIB en Argentina en 2020",
        "Superávit o déficit de cuenta corriente sobre el PIB en Perú en 2021",
        "Saldo de transacciones corrientes frente al PIB en Chile en 2020",
    ]
    for q in queries:
        intent = parser.parse(q)
        assert intent.root_concept in {"CUENTA_CORRIENTE", "CUENTA_CORRIENTE_PIB"}, f"Shadowed by PIB for query: {q}"
        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate is not None
        assert res.selected_candidate.indicator_id in {1243, 740}


def test_composite_precedence_emissions(parser: QueryParser, engine: SemanticResolutionEngine):
    """Emissions with or without LULUCF/UTCUTS."""
    # Sin LULUCF / sin UTCUTS -> 5682
    queries_sin = [
        "Emisiones de GEI sin LULUCF en México en 2020",
        "Emisiones netas excluyendo UTCUTS en Perú en 2020",
        "Emisiones excluyendo sector UTCUTS en Colombia en 2021",
    ]
    for q in queries_sin:
        intent = parser.parse(q)
        assert intent.root_concept == "EMISIONES_GEI_SIN_LULUCF", f"Failed for {q}"
        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate.indicator_id == 5682

    # Con LULUCF / con UTCUTS -> 5681
    queries_con = [
        "Emisiones totales de GEI con LULUCF en Brasil en 2020",
        "Emisiones de gases de efecto invernadero incluyendo UTCUTS en Colombia en 2019",
        "Emisiones brutas con LULUCF en Costa Rica en 2020",
    ]
    for q in queries_con:
        intent = parser.parse(q)
        assert intent.root_concept == "EMISIONES_GEI_LULUCF", f"Failed for {q}"
        res = engine.resolve(q)
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_candidate.indicator_id == 5681


def test_dynamic_member_matcher_slang_handling():
    """Verify DynamicMemberMatcher supports slang/normalized values properly."""
    matcher = DynamicMemberMatcher()
    from unofficial_cepalstat_mcp.dimensions import Dimension, Member

    dims = [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=146, name="Ambos sexos"), Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=330, name="Urbano"), Member(id=331, name="Rural")],
        ),
    ]

    ok, applied, unhandled = matcher.match_facets_to_dimensions(
        indicator_id=3339,
        dimensions=dims,
        facets={"sexo": "AMBOS", "area": "RURAL"},
    )
    assert ok is True
    assert len(applied) == 2
    assert applied[0].member_name == "Ambos sexos"
    assert applied[1].member_name == "Rural"
