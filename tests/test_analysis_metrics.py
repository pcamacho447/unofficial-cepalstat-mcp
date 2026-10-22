from unofficial_cepalstat_mcp.analysis import (
    classify_quadrant,
    compute_decoupling_score,
    compute_elasticity,
    compute_food_wage_gap,
)
from unofficial_cepalstat_mcp.analysis.metrics import (
    classify_quadrant as classify_quadrant_direct,
)
from unofficial_cepalstat_mcp.analysis.metrics import (
    compute_decoupling_score as compute_decoupling_score_direct,
)
from unofficial_cepalstat_mcp.analysis.metrics import (
    compute_elasticity as compute_elasticity_direct,
)
from unofficial_cepalstat_mcp.analysis.metrics import (
    compute_food_wage_gap as compute_food_wage_gap_direct,
)


def test_compute_elasticity_normal():
    # PIB creció 2%, pobreza cayó -4 pp -> elasticidad = -2.0
    el = compute_elasticity(poverty_change_pp=-4.0, gdp_growth_pct=2.0)
    assert el == -2.0

    # PIB creció 4.6%, pobreza subió 1.8 pp -> elasticidad = 0.39
    el2 = compute_elasticity(poverty_change_pp=1.8, gdp_growth_pct=4.60)
    assert el2 == 0.39


def test_compute_elasticity_edge_cases():
    # Si PIB no creció (0.0), no debe haber ZeroDivisionError
    assert compute_elasticity(poverty_change_pp=-1.0, gdp_growth_pct=0.0) is None
    # Valor cercano a cero (< 1e-6)
    assert compute_elasticity(poverty_change_pp=-1.0, gdp_growth_pct=1e-7) is None
    # Valores None
    assert compute_elasticity(poverty_change_pp=None, gdp_growth_pct=2.0) is None
    assert compute_elasticity(poverty_change_pp=-1.0, gdp_growth_pct=None) is None
    assert compute_elasticity(poverty_change_pp=None, gdp_growth_pct=None) is None


def test_classify_quadrant():
    # None cases
    assert classify_quadrant(gdp_growth=None, poverty_change_pp=-2.0) == "Indeterminado"
    assert classify_quadrant(gdp_growth=3.0, poverty_change_pp=None) == "Indeterminado"
    assert classify_quadrant(gdp_growth=None, poverty_change_pp=None) == "Indeterminado"

    # Crecimiento Virtuoso (gdp > 0, poverty < 0)
    assert classify_quadrant(gdp_growth=3.0, poverty_change_pp=-2.0, gini_change=-0.01) == "Crecimiento Virtuoso"

    # Crecimiento Excluyente (gdp > 0, poverty >= 0)
    assert classify_quadrant(gdp_growth=4.0, poverty_change_pp=1.5, gini_change=0.02) == "Crecimiento Excluyente"
    assert classify_quadrant(gdp_growth=2.0, poverty_change_pp=0.0) == "Crecimiento Excluyente"

    # Resiliencia Social (gdp <= 0, poverty <= 0)
    assert classify_quadrant(gdp_growth=-1.0, poverty_change_pp=-0.5, gini_change=0.0) == "Resiliencia Social"
    assert classify_quadrant(gdp_growth=0.0, poverty_change_pp=0.0) == "Resiliencia Social"
    assert classify_quadrant(gdp_growth=0.0, poverty_change_pp=-1.0) == "Resiliencia Social"

    # Doble Vulnerabilidad (gdp <= 0, poverty > 0)
    assert classify_quadrant(gdp_growth=-2.0, poverty_change_pp=3.0, gini_change=0.01) == "Doble Vulnerabilidad"
    assert classify_quadrant(gdp_growth=0.0, poverty_change_pp=0.5) == "Doble Vulnerabilidad"


def test_compute_decoupling_score():
    # Virtuoso vs Excluyente
    score_virtuoso = compute_decoupling_score(gdp_growth=3.0, poverty_change_pp=-3.0, wage_change_pct=10.0)
    score_excluyente = compute_decoupling_score(gdp_growth=4.0, poverty_change_pp=2.0, wage_change_pct=-10.0)
    assert score_virtuoso > score_excluyente
    assert 0.0 <= score_virtuoso <= 100.0
    assert 0.0 <= score_excluyente <= 100.0

    # Calculation detail check:
    # base 50.0 - (-1.0 * 8) = 58.0 + min(2*4, 20) = 66.0 + min(max(4*0.5, -15), 15) = 68.0
    expected = 68.0
    assert compute_decoupling_score(gdp_growth=2.0, poverty_change_pp=-1.0, wage_change_pct=4.0) == expected

    # wage_change_pct is None
    assert compute_decoupling_score(gdp_growth=2.0, poverty_change_pp=-1.0, wage_change_pct=None) == 66.0

    # Upper and lower clamping
    extreme_high = compute_decoupling_score(gdp_growth=10.0, poverty_change_pp=-15.0, wage_change_pct=50.0)
    assert extreme_high == 100.0

    extreme_low = compute_decoupling_score(gdp_growth=10.0, poverty_change_pp=15.0, wage_change_pct=-50.0)
    assert extreme_low == 0.0


def test_compute_food_wage_gap():
    # Normal cases: wage growth - food inflation
    # Real wage grew 5.0%, food inflation 3.5% -> gap = +1.5 pp
    assert compute_food_wage_gap(wage_change_pct=5.0, food_inflation_pct=3.5) == 1.5

    # Real wage fell -10.7%, food inflation 15.4% -> gap = -26.1 pp
    assert compute_food_wage_gap(wage_change_pct=-10.7, food_inflation_pct=15.4) == -26.1

    # Real wage grew 12.0%, food inflation 15.0% -> gap = -3.0 pp
    assert compute_food_wage_gap(wage_change_pct=12.0, food_inflation_pct=15.0) == -3.0

    # None cases
    assert compute_food_wage_gap(wage_change_pct=None, food_inflation_pct=5.0) is None
    assert compute_food_wage_gap(wage_change_pct=5.0, food_inflation_pct=None) is None
    assert compute_food_wage_gap(wage_change_pct=None, food_inflation_pct=None) is None

    # Rounding check
    assert compute_food_wage_gap(wage_change_pct=5.234, food_inflation_pct=3.10) == 2.13


def test_exports_identical():
    assert compute_elasticity is compute_elasticity_direct
    assert classify_quadrant is classify_quadrant_direct
    assert compute_decoupling_score is compute_decoupling_score_direct
    assert compute_food_wage_gap is compute_food_wage_gap_direct
