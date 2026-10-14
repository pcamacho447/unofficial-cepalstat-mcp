# Suite de Análisis y Jupyter Notebooks de Desacople Crecimiento-Bienestar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar una suite analítica completa en `statscepal` para modelar y cuantificar el Desacople Crecimiento-Bienestar en América Latina, incluyendo modelos de datos, cálculo de elasticidades sociales, cuadrantes socioeconómicos, un nuevo subcomando CLI y un Jupyter Notebook interactivo de investigación (`notebooks/01_desacople_crecimiento_bienestar.ipynb`).

**Architecture:** Módulo modular `src/statscepal/analysis/` con modelos Pydantic (`models.py`), funciones matemáticas y econométricas (`metrics.py`) y servicio orquestador (`service.py`) que consume el `DataExtractor`. Se acompaña de un notebook reproducible en `notebooks/` y el subcomando `statscepal analyze desacople`.

**Tech Stack:** Python 3.12+, `pydantic`, `pandas`, `numpy`, `matplotlib`, `pytest`, `nbformat`, `ipykernel`.

**Spec:** [docs/superpowers/specs/2026-10-14-desacople-social-notebooks-design.md](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/superpowers/specs/2026-10-14-desacople-social-notebooks-design.md)

## Global Constraints

- Compatibilidad con API de CEPALSTAT: Utilizar indicadores `3894` (PIB pc), `3328` (Pobreza), `340` (Salario Real), `3289` (Gini) y `4788` (Población).
- Manejo estricto de áreas geográficas: Reconocer que Argentina utiliza `Total del área urbana` y los demás países `Nacional`.
- Salidas idempotentes y libres de división por cero al calcular elasticidades ($\Delta \text{PIB} = 0$).
- El Jupyter Notebook debe ser ejecutable de punta a punta sin errores de celda.

---

### Task 1: Pydantic Models for Analysis (`models.py`)

**Files:**
- Create: `src/statscepal/analysis/__init__.py`
- Create: `src/statscepal/analysis/models.py`
- Test: `tests/test_analysis_models.py`

**Interfaces:**
- Produces:
  - `CountryPeriodMetric`: `country`, `period_label`, `years_range`, `gdp_pc_growth_mean`, `poverty_total_change_pp`, `poverty_extreme_change_pp`, `real_min_wage_change_pct`, `gini_change`, `social_elasticity`, `quadrant`
  - `DecouplingDataset`: `records: list[CountryPeriodMetric]`, `metadata: dict[str, Any]`

- [ ] **Step 1: Write the failing test**

File: `tests/test_analysis_models.py`
```python
import pytest
from statscepal.analysis.models import CountryPeriodMetric, DecouplingDataset


def test_country_period_metric_creation():
    metric = CountryPeriodMetric(
        country="Argentina",
        period_label="P2: 2021-2023",
        years_range="2021-2023",
        gdp_pc_growth_mean=4.60,
        poverty_total_change_pp=1.8,
        poverty_extreme_change_pp=0.2,
        real_min_wage_change_pct=-10.7,
        gini_change=0.011,
        social_elasticity=0.39,
        quadrant="Crecimiento Excluyente",
    )
    assert metric.country == "Argentina"
    assert metric.gdp_pc_growth_mean == 4.60
    assert metric.quadrant == "Crecimiento Excluyente"


def test_decoupling_dataset_creation():
    metric = CountryPeriodMetric(
        country="Chile",
        period_label="P1: 2015-2019",
        years_range="2015-2017",
        gdp_pc_growth_mean=0.50,
        poverty_total_change_pp=-2.5,
        poverty_extreme_change_pp=-0.3,
        real_min_wage_change_pct=5.2,
        gini_change=-0.003,
        social_elasticity=-5.0,
        quadrant="Crecimiento Virtuoso",
    )
    dataset = DecouplingDataset(records=[metric], metadata={"total_countries": 1})
    assert len(dataset.records) == 1
    assert dataset.records[0].country == "Chile"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_analysis_models.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.analysis'`

- [ ] **Step 3: Implement `src/statscepal/analysis/models.py` and `__init__.py`**

File: `src/statscepal/analysis/__init__.py`
```python
"""Analysis and investigative module for statscepal."""

from statscepal.analysis.models import CountryPeriodMetric, DecouplingDataset

__all__ = ["CountryPeriodMetric", "DecouplingDataset"]
```

File: `src/statscepal/analysis/models.py`
```python
"""Data models for growth-wellbeing decoupling analysis."""

from typing import Any
from pydantic import BaseModel, Field


class CountryPeriodMetric(BaseModel):
    """Metrics for a single country across an analysis period."""

    country: str
    period_label: str
    years_range: str
    gdp_pc_growth_mean: float
    poverty_total_change_pp: float | None = None
    poverty_extreme_change_pp: float | None = None
    real_min_wage_change_pct: float | None = None
    gini_change: float | None = None
    social_elasticity: float | None = None
    quadrant: str = "Indeterminado"


class DecouplingDataset(BaseModel):
    """Consolidated dataset of decoupling analysis."""

    records: list[CountryPeriodMetric] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_analysis_models.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/analysis/__init__.py src/statscepal/analysis/models.py tests/test_analysis_models.py
git commit -m "feat(analysis): add data models for decoupling metrics"
```

---

### Task 2: Econometric & Elasticity Metrics Engine (`metrics.py`)

**Files:**
- Create: `src/statscepal/analysis/metrics.py`
- Test: `tests/test_analysis_metrics.py`

**Interfaces:**
- Produces:
  - `compute_elasticity(poverty_change_pp: float | None, gdp_growth_pct: float | None) -> float | None`
  - `classify_quadrant(gdp_growth: float | None, poverty_change_pp: float | None, gini_change: float | None) -> str`
  - `compute_decoupling_score(gdp_growth: float, poverty_change_pp: float, wage_change_pct: float | None) -> float`

- [ ] **Step 1: Write the failing test**

File: `tests/test_analysis_metrics.py`
```python
import pytest
from statscepal.analysis.metrics import (
    compute_elasticity,
    classify_quadrant,
    compute_decoupling_score,
)


def test_compute_elasticity_normal():
    # PIB creció 2%, pobreza cayó -4 pp -> elasticidad = -2.0
    el = compute_elasticity(poverty_change_pp=-4.0, gdp_growth_pct=2.0)
    assert el == -2.0


def test_compute_elasticity_zero_gdp():
    # Si PIB no creció (0.0), no debe haber ZeroDivisionError
    el = compute_elasticity(poverty_change_pp=-1.0, gdp_growth_pct=0.0)
    assert el is None


def test_classify_quadrant():
    # Crecimiento Virtuoso
    assert classify_quadrant(gdp_growth=3.0, poverty_change_pp=-2.0, gini_change=-0.01) == "Crecimiento Virtuoso"
    # Crecimiento Excluyente (PIB sube pero pobreza sube)
    assert classify_quadrant(gdp_growth=4.0, poverty_change_pp=1.5, gini_change=0.02) == "Crecimiento Excluyente"
    # Resiliencia Social (recesión pero pobreza baja)
    assert classify_quadrant(gdp_growth=-1.0, poverty_change_pp=-0.5, gini_change=0.0) == "Resiliencia Social"
    # Doble Vulnerabilidad (recesión y pobreza sube)
    assert classify_quadrant(gdp_growth=-2.0, poverty_change_pp=3.0, gini_change=0.01) == "Doble Vulnerabilidad"


def test_compute_decoupling_score():
    # Score 0 a 100: alto si PIB crece, pobreza baja y salario sube
    score_virtuoso = compute_decoupling_score(gdp_growth=3.0, poverty_change_pp=-3.0, wage_change_pct=10.0)
    score_excluyente = compute_decoupling_score(gdp_growth=4.0, poverty_change_pp=2.0, wage_change_pct=-10.0)
    assert score_virtuoso > score_excluyente
    assert 0.0 <= score_virtuoso <= 100.0
    assert 0.0 <= score_excluyente <= 100.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_analysis_metrics.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.analysis.metrics'`

- [ ] **Step 3: Implement `src/statscepal/analysis/metrics.py`**

File: `src/statscepal/analysis/metrics.py`
```python
"""Econometric and analytical metrics for growth-wellbeing decoupling."""

from typing import Optional


def compute_elasticity(
    poverty_change_pp: Optional[float],
    gdp_growth_pct: Optional[float],
) -> Optional[float]:
    """Calculate social elasticity of growth: Δ% Poverty / Δ% GDP.

    Returns None if either value is None or if GDP growth is exactly 0.
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
    """Classify country performance into a 2x2 socioeconomic quadrant."""
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
    """Calculate synthetic decoupling index (0 = maximum decoupling, 100 = optimal shared growth)."""
    # Base score: 50
    score = 50.0

    # Poverty reduction adds points, increase subtracts points
    score -= poverty_change_pp * 8.0

    # GDP growth adds points if poverty decreased, penalized if poverty increased
    if poverty_change_pp <= 0:
        score += min(gdp_growth * 4.0, 20.0)
    else:
        score -= min(gdp_growth * 4.0, 20.0)

    # Real wage growth impact
    if wage_change_pct is not None:
        score += min(max(wage_change_pct * 0.5, -15.0), 15.0)

    return max(0.0, min(100.0, round(score, 1)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_analysis_metrics.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/analysis/metrics.py tests/test_analysis_metrics.py
git commit -m "feat(analysis): implement elasticity and quadrant classification metrics"
```

---

### Task 3: Decoupling Analysis Service (`service.py`)

**Files:**
- Create: `src/statscepal/analysis/service.py`
- Test: `tests/test_analysis_service.py`

**Interfaces:**
- Produces:
  - `DecouplingAnalyzer`: `analyze_countries(countries: list[str], periods: list[tuple[str, int, int]]) -> DecouplingDataset`

- [ ] **Step 1: Write the failing test**

File: `tests/test_analysis_service.py`
```python
import pytest
from unittest.mock import MagicMock
import pandas as pd
from statscepal.analysis.service import DecouplingAnalyzer


def test_analyzer_with_mocked_extractor():
    mock_extractor = MagicMock()
    # Mock data for PIB (3894)
    df_pib = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2016", "2017"],
        "value": [1.5, 2.0],
    })
    # Mock data for Pobreza (3328)
    df_pob = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Area geográfica_(EH)": ["Nacional", "Nacional"],
        "Pobreza extrema y pobreza": ["Pobreza", "Pobreza"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [13.2, 10.7],
    })
    # Mock data for Salario Real (340)
    df_sal = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [100.0, 105.0],
    })
    # Mock data for Gini (3289)
    df_gini = pd.DataFrame({
        "País__ESTANDAR": ["Chile", "Chile"],
        "Años__ESTANDAR": ["2015", "2017"],
        "value": [0.45, 0.44],
    })

    def mock_get_df(ind_id, members=None):
        if ind_id == 3894:
            return df_pib
        elif ind_id == 3328:
            return df_pob
        elif ind_id == 340:
            return df_sal
        elif ind_id == 3289:
            return df_gini
        return pd.DataFrame()

    mock_extractor.get_dataframe.side_effect = mock_get_df

    analyzer = DecouplingAnalyzer(extractor=mock_extractor)
    dataset = analyzer.analyze_countries(
        countries=["Chile"],
        periods=[("P1", 2015, 2017)],
    )

    assert len(dataset.records) == 1
    rec = dataset.records[0]
    assert rec.country == "Chile"
    assert rec.poverty_total_change_pp == -2.5
    assert rec.quadrant == "Crecimiento Virtuoso"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_analysis_service.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.analysis.service'`

- [ ] **Step 3: Implement `src/statscepal/analysis/service.py`**

File: `src/statscepal/analysis/service.py`
```python
"""Service orchestrator for growth-wellbeing decoupling analysis."""

from typing import Any, Optional
import pandas as pd
import numpy as np
from statscepal.extractor import DataExtractor
from statscepal.analysis.models import CountryPeriodMetric, DecouplingDataset
from statscepal.analysis.metrics import (
    compute_elasticity,
    classify_quadrant,
)

# Mapeo de IDs de países oficiales en series económicas y sociales de CEPALSTAT
COUNTRY_MEMBER_MAP = {
    "argentina": 216,
    "chile": 224,
    "colombia": 225,
    "méxico": 233,
    "mexico": 233,
    "perú": 244,
    "peru": 244,
    "uruguay": 258,
}


class DecouplingAnalyzer:
    """Orchestrates indicator fetching, temporal alignment, and metrics computation."""

    def __init__(self, extractor: DataExtractor) -> None:
        self.extractor = extractor

    def analyze_countries(
        self,
        countries: list[str],
        periods: list[tuple[str, int, int]],
    ) -> DecouplingDataset:
        """Analyze a list of countries across defined time periods."""
        member_ids = [
            COUNTRY_MEMBER_MAP[c.lower()]
            for c in countries
            if c.lower() in COUNTRY_MEMBER_MAP
        ]

        # Descarga de los 4 indicadores clave
        df_pib = self.extractor.get_dataframe(3894, members=member_ids)
        df_pob = self.extractor.get_dataframe(3328, members=member_ids)
        df_sal = self.extractor.get_dataframe(340, members=member_ids)
        df_gini = self.extractor.get_dataframe(3289, members=member_ids)

        for df in [df_pib, df_pob, df_sal, df_gini]:
            if not df.empty and "Años__ESTANDAR" in df.columns:
                df["Años__ESTANDAR"] = pd.to_numeric(df["Años__ESTANDAR"], errors="coerce")

        records: list[CountryPeriodMetric] = []

        for country_name in countries:
            # Determinación de área geográfica (Argentina usa Total del área urbana)
            area = "Total del área urbana" if country_name.lower() in ["argentina"] else "Nacional"

            for period_label, start_year, end_year in periods:
                sub_pib = df_pib[
                    (df_pib["País__ESTANDAR"].str.lower() == country_name.lower())
                    & (df_pib["Años__ESTANDAR"].between(start_year, end_year))
                ]
                sub_pob = df_pob[
                    (df_pob["País__ESTANDAR"].str.lower() == country_name.lower())
                    & (df_pob["Area geográfica_(EH)"] == area)
                    & (df_pob["Años__ESTANDAR"].between(start_year, end_year))
                ]
                sub_sal = df_sal[
                    (df_sal["País__ESTANDAR"].str.lower() == country_name.lower())
                    & (df_sal["Años__ESTANDAR"].between(start_year, end_year))
                ]
                sub_gini = df_gini[
                    (df_gini["País__ESTANDAR"].str.lower() == country_name.lower())
                    & (df_gini["Años__ESTANDAR"].between(start_year, end_year))
                ]

                pib_mean = float(sub_pib["value"].mean()) if not sub_pib.empty else 0.0

                pob_tot = sub_pob[sub_pob["Pobreza extrema y pobreza"] == "Pobreza"].sort_values("Años__ESTANDAR")
                pob_ext = sub_pob[sub_pob["Pobreza extrema y pobreza"] == "Pobreza extrema"].sort_values("Años__ESTANDAR")

                pob_tot_chg = (
                    float(pob_tot.iloc[-1]["value"] - pob_tot.iloc[0]["value"])
                    if len(pob_tot) >= 2
                    else None
                )
                pob_ext_chg = (
                    float(pob_ext.iloc[-1]["value"] - pob_ext.iloc[0]["value"])
                    if len(pob_ext) >= 2
                    else None
                )

                sal_sorted = sub_sal.sort_values("Años__ESTANDAR")
                sal_chg = (
                    float(((sal_sorted.iloc[-1]["value"] / sal_sorted.iloc[0]["value"]) - 1.0) * 100.0)
                    if len(sal_sorted) >= 2 and sal_sorted.iloc[0]["value"] > 0
                    else None
                )

                gini_sorted = sub_gini.sort_values("Años__ESTANDAR")
                gini_chg = (
                    float(gini_sorted.iloc[-1]["value"] - gini_sorted.iloc[0]["value"])
                    if len(gini_sorted) >= 2
                    else None
                )

                years_range = (
                    f"{int(pob_tot.iloc[0]['Años__ESTANDAR'])}-{int(pob_tot.iloc[-1]['Años__ESTANDAR'])}"
                    if len(pob_tot) >= 2
                    else f"{start_year}-{end_year}"
                )

                elasticity = compute_elasticity(pob_tot_chg, pib_mean)
                quadrant = classify_quadrant(pib_mean, pob_tot_chg, gini_chg)

                records.append(
                    CountryPeriodMetric(
                        country=country_name,
                        period_label=period_label,
                        years_range=years_range,
                        gdp_pc_growth_mean=round(pib_mean, 2),
                        poverty_total_change_pp=round(pob_tot_chg, 2) if pob_tot_chg is not None else None,
                        poverty_extreme_change_pp=round(pob_ext_chg, 2) if pob_ext_chg is not None else None,
                        real_min_wage_change_pct=round(sal_chg, 2) if sal_chg is not None else None,
                        gini_change=round(gini_chg, 4) if gini_chg is not None else None,
                        social_elasticity=elasticity,
                        quadrant=quadrant,
                    )
                )

        return DecouplingDataset(
            records=records,
            metadata={"countries": countries, "total_records": len(records)},
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_analysis_service.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/analysis/service.py tests/test_analysis_service.py
git commit -m "feat(analysis): implement DecouplingAnalyzer orchestrator"
```

---

### Task 4: CLI Integration (`statscepal analyze desacople`)

**Files:**
- Modify: `src/statscepal/cli.py`
- Test: `tests/test_cli_analyze.py`

- [ ] **Step 1: Write the failing test**

File: `tests/test_cli_analyze.py`
```python
import pytest
from unittest.mock import patch, MagicMock
from statscepal.cli import main
from statscepal.analysis.models import CountryPeriodMetric, DecouplingDataset


@patch("statscepal.cli.DecouplingAnalyzer")
@patch("statscepal.cli.DataExtractor")
@patch("statscepal.cli.CepalStatClient")
def test_cli_analyze_desacople(mock_client, mock_extractor, mock_analyzer, capsys):
    mock_instance = MagicMock()
    mock_instance.analyze_countries.return_value = DecouplingDataset(
        records=[
            CountryPeriodMetric(
                country="Chile",
                period_label="P1",
                years_range="2015-2017",
                gdp_pc_growth_mean=0.5,
                poverty_total_change_pp=-2.5,
                quadrant="Crecimiento Virtuoso",
            )
        ]
    )
    mock_analyzer.return_value = mock_instance

    exit_code = main(["analyze", "desacople", "--countries", "Chile"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Chile" in captured.out
    assert "Crecimiento Virtuoso" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_analyze.py`
Expected: FAIL with `statscepal: error: argument command: invalid choice: 'analyze'`

- [ ] **Step 3: Update `src/statscepal/cli.py` to register `analyze` subcommand**

Add `analyze` command parser and `handle_analyze` function supporting `--countries` and `--output`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_analyze.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/cli.py tests/test_cli_analyze.py
git commit -m "feat(cli): add statscepal analyze desacople subcommand"
```

---

### Task 5: Creation of Guided Jupyter Notebook (`notebooks/01_desacople_crecimiento_bienestar.ipynb`)

**Files:**
- Create: `notebooks/01_desacople_crecimiento_bienestar.ipynb`
- Test: `tests/test_notebook_syntax.py`

**Notebook Requirements:**
- Total 5 sections:
  1. Header, context & import of `statscepal`.
  2. Data fetching for the 6 countries (`Argentina`, `Chile`, `Colombia`, `México`, `Perú`, `Uruguay`) across 2015-2019 and 2021-2023.
  3. Transformation, elasticities computation and comparison tables.
  4. Scatter plot visualization of Quadrants using `matplotlib` (Eje X: $\Delta$ PIB pc, Eje Y: $\Delta$ Pobreza).
  5. Executive conclusions on the Salario Mínimo Real mechanism.

- [ ] **Step 1: Write test to verify notebook file exists and is valid JSON/ipynb**

File: `tests/test_notebook_syntax.py`
```python
import json
import pytest
from pathlib import Path


def test_notebook_structure_valid():
    nb_path = Path("notebooks/01_desacople_crecimiento_bienestar.ipynb")
    assert nb_path.exists(), "Notebook file must exist"

    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    assert "cells" in nb
    assert len(nb["cells"]) >= 5
    assert nb["metadata"]["language_info"]["name"] == "python"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_notebook_syntax.py`
Expected: FAIL with `AssertionError: Notebook file must exist`

- [ ] **Step 3: Generate the notebook programmatically with clean cells**

Create `notebooks/01_desacople_crecimiento_bienestar.ipynb` with code and markdown cells executing `DecouplingAnalyzer` and plotting the quadrants.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_notebook_syntax.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add notebooks/01_desacople_crecimiento_bienestar.ipynb tests/test_notebook_syntax.py
git commit -m "feat(notebooks): add interactive 01_desacople_crecimiento_bienestar.ipynb"
```

---

### Task 6: Full Integration Test & Verification

- [ ] **Step 1: Run complete test suite**

Run: `uv run pytest`
Expected: All tests pass (models, metrics, service, cli, notebook).

- [ ] **Step 2: Execute CLI command end-to-end**

Run: `uv run statscepal analyze desacople --countries Chile,Colombia,Peru`
Expected: Formatted table output with correct quadrants and elasticities.

- [ ] **Step 3: Final Commit**

```bash
git add .
git commit -m "feat(analysis): complete decoupling analysis suite with Jupyter notebook"
```
