import pytest
from pydantic import ValidationError
from statscepal.bitacora.models import AntiBiasChecklist, BitacoraRecipe, DataQualityReport


def test_bitacora_recipe_creation():
    quality = DataQualityReport(
        total_records=50,
        null_count=0,
        null_ratio=0.0,
        has_gaps=False,
        min_year=1970,
        max_year=2020,
        min_value=100.0,
        max_value=500.0,
    )
    antibias = AntiBiasChecklist(
        unit_verified=True,
        scale_factor_note="Cifras en miles de personas",
        is_projection=False,
        base_year_split=2021,
        warnings=[],
    )
    recipe = BitacoraRecipe(
        id="recipe-chl-4788-pob",
        indicator_id=4788,
        indicator_name="Población total",
        country="Chile",
        country_iso3="CHL",
        country_member_id=224,
        theme="Demográficos",
        unit="Miles de personas",
        member_ids=[224, 29190],
        python_code="extractor.get_dataframe(4788, members=[224, 29190])",
        status="certified",
        date_certified="2026-10-14",
        tags=["chile", "poblacion"],
        quality_report=quality,
        antibias=antibias,
    )
    assert recipe.id == "recipe-chl-4788-pob"
    assert recipe.country == "Chile"
    assert recipe.status == "certified"
    assert recipe.quality_report is not None
    assert recipe.quality_report.null_count == 0
    assert recipe.antibias is not None
    assert recipe.antibias.unit_verified is True


def test_data_quality_report_defaults():
    report = DataQualityReport(total_records=10)
    assert report.total_records == 10
    assert report.null_count == 0
    assert report.null_ratio == 0.0
    assert report.has_gaps is False
    assert report.min_year is None
    assert report.max_year is None
    assert report.min_value is None
    assert report.max_value is None


def test_antibias_checklist_defaults():
    checklist = AntiBiasChecklist()
    assert checklist.unit_verified is True
    assert checklist.scale_factor_note == ""
    assert checklist.is_projection is False
    assert checklist.base_year_split is None
    assert checklist.warnings == []


def test_bitacora_recipe_defaults():
    recipe = BitacoraRecipe(
        id="recipe-test-1",
        indicator_id=123,
        indicator_name="Test Indicator",
        country="Chile",
    )
    assert recipe.country_iso3 == ""
    assert recipe.country_member_id is None
    assert recipe.theme == ""
    assert recipe.unit == ""
    assert recipe.member_ids == []
    assert recipe.python_code == ""
    assert recipe.status == "certified"
    assert recipe.date_certified == ""
    assert recipe.tags == []
    assert recipe.quality_report is None
    assert recipe.antibias is None


def test_bitacora_recipe_validation_failure():
    with pytest.raises(ValidationError):
        BitacoraRecipe()  # type: ignore[call-arg]
