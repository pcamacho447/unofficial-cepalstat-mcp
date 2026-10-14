from pathlib import Path
import pytest
from statscepal.bitacora.store import BitacoraStore


def test_seed_recipes_chile_discovery():
    store = BitacoraStore(base_dir="bitacoras")
    count = store.sync()
    assert count >= 2

    # Tests store.lookup("poblacion", country="Chile") returns indicator 4788
    # with country_member_id=224 and valid anti-bias notes.
    results_pob = store.lookup("poblacion", country="Chile")
    assert len(results_pob) >= 1
    pob_recipe = next((r for r in results_pob if r.indicator_id == 4788), None)
    assert pob_recipe is not None
    assert pob_recipe.id == "recipe-chl-4788-pob"
    assert pob_recipe.country == "Chile"
    assert pob_recipe.country_iso3 == "CHL"
    assert pob_recipe.country_member_id == 224
    assert pob_recipe.status == "certified"
    assert pob_recipe.member_ids == [224, 29190, 88623]
    assert pob_recipe.antibias is not None
    assert pob_recipe.antibias.unit_verified is True
    assert "miles de personas" in pob_recipe.antibias.scale_factor_note.lower()
    assert pob_recipe.antibias.is_projection is True
    assert pob_recipe.antibias.base_year_split == 2021
    assert len(pob_recipe.antibias.warnings) >= 1
    assert pob_recipe.quality_report is not None
    assert pob_recipe.quality_report.total_records == 151
    assert pob_recipe.quality_report.null_count == 0

    # Tests store.lookup("pib", country="Chile") returns Chile GDP recipe.
    results_pib = store.lookup("pib", country="Chile")
    assert len(results_pib) >= 1
    pib_recipe = next((r for r in results_pib if r.indicator_id == 415), None)
    assert pib_recipe is not None
    assert pib_recipe.id == "recipe-chl-415-pib"
    assert pib_recipe.indicator_id == 415
    assert pib_recipe.country == "Chile"
    assert pib_recipe.country_member_id == 224
    assert pib_recipe.status == "certified"
    assert pib_recipe.antibias is not None
    assert pib_recipe.antibias.unit_verified is True
    assert pib_recipe.antibias.is_projection is False
    assert pob_recipe.python_code != ""
    assert pib_recipe.python_code != ""
