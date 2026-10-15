"""Econometric and analytical metrics for growth-wellbeing decoupling."""

from typing import Optional


def compute_elasticity(
    poverty_change_pp: Optional[float],
    gdp_growth_pct: Optional[float],
) -> Optional[float]:
    """Calculate social elasticity of growth: Δ% Poverty / Δ% GDP.

    Returns None if either value is None or if GDP growth is zero (abs(gdp_growth_pct) < 1e-6).
    Returns rounded float to 2 decimal places.
    """
    if poverty_change_pp is None or gdp_growth_pct is None:
        return None
    if abs(gdp_growth_pct) < 1e-6:
        return None
    return round(poverty_change_pp / gdp_growth_pct, 2)


def classify_quadrant(
    gdp_growth: Optional[float],
    poverty_change_pp: Optional[float],
    gini_change: Optional[float] = None,
) -> str:
    """Classify country performance into a 2x2 socioeconomic quadrant.

    - If either gdp_growth or poverty_change_pp is None: returns "Indeterminado"
    - gdp_growth > 0 and poverty_change_pp < 0: "Crecimiento Virtuoso"
    - gdp_growth > 0 and poverty_change_pp >= 0: "Crecimiento Excluyente"
    - gdp_growth <= 0 and poverty_change_pp <= 0: "Resiliencia Social"
    - gdp_growth <= 0 and poverty_change_pp > 0: "Doble Vulnerabilidad"
    """
    if gdp_growth is None or poverty_change_pp is None:
        return "Indeterminado"

    if gdp_growth > 0:
        if poverty_change_pp < 0:
            return "Crecimiento Virtuoso"
        else:
            return "Crecimiento Excluyente"
    else:
        if poverty_change_pp <= 0:
            return "Resiliencia Social"
        else:
            return "Doble Vulnerabilidad"


def compute_decoupling_score(
    gdp_growth: float,
    poverty_change_pp: float,
    wage_change_pct: Optional[float] = None,
) -> float:
    """Calculate synthetic decoupling index on a scale from 0 to 100.

    - Base score: 50.0
    - Score adjustment: score -= poverty_change_pp * 8.0
    - If poverty_change_pp <= 0: score += min(gdp_growth * 4.0, 20.0)
    - Else: score -= min(gdp_growth * 4.0, 20.0)
    - If wage_change_pct is not None: score += min(max(wage_change_pct * 0.5, -15.0), 15.0)
    - Return max(0.0, min(100.0, round(score, 1)))
    """
    score = 50.0

    score -= poverty_change_pp * 8.0

    if poverty_change_pp <= 0:
        score += min(gdp_growth * 4.0, 20.0)
    else:
        score -= min(gdp_growth * 4.0, 20.0)

    if wage_change_pct is not None:
        score += min(max(wage_change_pct * 0.5, -15.0), 15.0)

    return max(0.0, min(100.0, round(score, 1)))


def compute_food_wage_gap(
    wage_change_pct: Optional[float],
    food_inflation_pct: Optional[float],
) -> Optional[float]:
    """Calculate purchasing power wage-food gap: Δ% Wage - % Food Inflation.

    Returns None if either value is None.
    Returns float rounded to 2 decimal places.
    """
    if wage_change_pct is None or food_inflation_pct is None:
        return None
    return round(float(round(wage_change_pct, 2)) - float(food_inflation_pct), 2)

