"""Tests for AntiBiasValidator and data quality reporting."""

import pandas as pd
import pytest

from unofficial_cepalstat_mcp.bitacora.validator import AntiBiasValidator


def test_validator_with_clean_data():
    """Verify clean dataset produces an accurate quality report and valid checklist."""
    df = pd.DataFrame({
        "value": [100.0, 105.0, 110.0],
        "Años__ESTANDAR": ["2018", "2019", "2020"],
    })
    meta = {
        "unit": "Miles de personas",
        "data_features": "Estimaciones 1950-2021 y proyecciones 2022-2100",
        "comments": "El año base de las proyecciones es 2021",
    }

    quality, antibias = AntiBiasValidator.audit(df, meta, year_column="Años__ESTANDAR")

    assert quality.total_records == 3
    assert quality.null_count == 0
    assert quality.null_ratio == 0.0
    assert quality.has_gaps is False
    assert quality.min_year == 2018
    assert quality.max_year == 2020
    assert quality.min_value == 100.0
    assert quality.max_value == 110.0
    assert antibias.unit_verified is True
    assert "Miles de personas" in antibias.scale_factor_note
    assert antibias.base_year_split == 2021
    assert antibias.is_projection is False


def test_validator_detects_gaps_and_nulls():
    """Verify detection of missing/null values and temporal discontinuities."""
    df = pd.DataFrame({
        "value": [10.0, None, 15.0],
        "Años__ESTANDAR": ["2015", "2016", "2018"],  # Missing 2017 -> Gap
    })
    meta = {"unit": "Porcentaje del PIB"}

    quality, antibias = AntiBiasValidator.audit(df, meta, year_column="Años__ESTANDAR")

    assert quality.total_records == 3
    assert quality.null_count == 1
    assert quality.null_ratio == pytest.approx(1 / 3)
    assert quality.has_gaps is True
    assert any("nulos" in w.lower() or "faltantes" in w.lower() for w in antibias.warnings)
    assert any("discontinuidad" in w.lower() or "gap" in w.lower() for w in antibias.warnings)


def test_validator_empty_dataframe():
    """Verify handling of empty DataFrames."""
    df = pd.DataFrame()
    meta = {"unit": "Porcentaje"}

    quality, antibias = AntiBiasValidator.audit(df, meta)

    assert quality.total_records == 0
    assert quality.null_count == 0
    assert quality.null_ratio == 0.0
    assert quality.has_gaps is False
    assert quality.min_year is None
    assert quality.max_year is None
    assert quality.min_value is None
    assert quality.max_value is None
    assert antibias.unit_verified is False
    assert any("vacío" in w.lower() or "vacio" in w.lower() for w in antibias.warnings)


def test_validator_missing_unit_warning():
    """Verify warning when metadata lacks unit of measurement."""
    df = pd.DataFrame({
        "value": [5.0, 6.0],
        "Años__ESTANDAR": ["2019", "2020"],
    })
    meta = {}

    quality, antibias = AntiBiasValidator.audit(df, meta, year_column="Años__ESTANDAR")

    assert antibias.unit_verified is False
    assert any("unidad" in w.lower() for w in antibias.warnings)


def test_validator_detects_projections():
    """Verify projection detection when max_year exceeds base_year_split."""
    df = pd.DataFrame({
        "value": [100.0, 102.0, 104.0, 106.0],
        "Años__ESTANDAR": ["2020", "2021", "2022", "2023"],
    })
    meta = {
        "unit": "Miles de personas",
        "comments": "El año base de las estimaciones es 2021. Los años posteriores son proyecciones.",
    }

    quality, antibias = AntiBiasValidator.audit(df, meta, year_column="Años__ESTANDAR")

    assert antibias.base_year_split == 2021
    assert antibias.is_projection is True
    assert any("proyecciones" in w.lower() for w in antibias.warnings)
