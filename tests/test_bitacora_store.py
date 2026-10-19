from pathlib import Path
import pytest
import yaml

from unofficial_cepalstat_mcp.bitacora.models import AntiBiasChecklist, BitacoraRecipe, DataQualityReport
from unofficial_cepalstat_mcp.bitacora.store import BitacoraStore


@pytest.fixture
def sample_recipe() -> BitacoraRecipe:
    return BitacoraRecipe(
        id="recipe-chl-4788-pob",
        indicator_id=4788,
        indicator_name="Población total, según sexo",
        country="Chile",
        country_iso3="CHL",
        country_member_id=224,
        theme="Demográficos",
        unit="Miles de personas",
        member_ids=[224, 29190],
        python_code="extractor.get_dataframe(4788, members=[224, 29190])",
        status="certified",
        date_certified="2026-10-14",
        tags=["chile", "poblacion", "demografia"],
        quality_report=DataQualityReport(
            total_records=100,
            null_count=0,
            null_ratio=0.0,
            has_gaps=False,
            min_year=1950,
            max_year=2050,
            min_value=5000.0,
            max_value=20000.0,
        ),
        antibias=AntiBiasChecklist(
            unit_verified=True,
            scale_factor_note="Cifras en miles de personas.",
            is_projection=True,
            base_year_split=2021,
            warnings=["Cifras posteriores a 2021 son proyecciones."],
        ),
    )


def test_save_recipe_creates_valid_markdown_and_frontmatter(tmp_path: Path, sample_recipe: BitacoraRecipe):
    base_dir = tmp_path / "bitacoras"
    db_path = tmp_path / "cache.db"
    store = BitacoraStore(base_dir=base_dir, db_path=db_path)

    saved_path = store.save_recipe(sample_recipe)

    assert saved_path.exists()
    assert saved_path.suffix == ".md"
    assert "paises" in saved_path.parts
    assert "chile" in saved_path.parts
    assert saved_path.name == f"{sample_recipe.indicator_id}_{sample_recipe.id}.md"

    # Verify frontmatter is valid YAML
    content = saved_path.read_text(encoding="utf-8")
    assert content.startswith("---")
    parts = content.split("---", 2)
    assert len(parts) >= 3
    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["id"] == sample_recipe.id
    assert frontmatter["indicator_id"] == 4788
    assert frontmatter["country"] == "Chile"
    assert frontmatter["antibias"]["is_projection"] is True

    # Verify markdown body
    assert "# Receta:" in parts[2]
    assert sample_recipe.python_code in parts[2]


def test_lookup_and_filtering(tmp_path: Path, sample_recipe: BitacoraRecipe):
    base_dir = tmp_path / "bitacoras"
    db_path = tmp_path / "cache.db"
    store = BitacoraStore(base_dir=base_dir, db_path=db_path)

    recipe_arg = BitacoraRecipe(
        id="recipe-arg-737-pib",
        indicator_id=737,
        indicator_name="PIB per cápita anual",
        country="Argentina",
        country_iso3="ARG",
        theme="Económicos",
        unit="Dólares",
        tags=["argentina", "pib", "economia"],
    )

    store.save_recipe(sample_recipe)
    store.save_recipe(recipe_arg)

    # Search by indicator name query
    results = store.lookup("poblacion")
    assert len(results) == 1
    assert results[0].id == sample_recipe.id

    # Search by country
    results_chl = store.lookup("", country="Chile")
    assert len(results_chl) == 1
    assert results_chl[0].id == sample_recipe.id

    results_arg = store.lookup("", country="ARG")
    assert len(results_arg) == 1
    assert results_arg[0].id == recipe_arg.id

    # Search by tag
    results_tag = store.lookup("", tag="economia")
    assert len(results_tag) == 1
    assert results_tag[0].id == recipe_arg.id

    # Search with no match
    assert store.lookup("no_such_term") == []


def test_get_recipe(tmp_path: Path, sample_recipe: BitacoraRecipe):
    base_dir = tmp_path / "bitacoras"
    db_path = tmp_path / "cache.db"
    store = BitacoraStore(base_dir=base_dir, db_path=db_path)

    store.save_recipe(sample_recipe)

    fetched = store.get_recipe(sample_recipe.id)
    assert fetched is not None
    assert fetched.id == sample_recipe.id
    assert fetched.indicator_id == sample_recipe.indicator_id
    assert fetched.quality_report is not None
    assert fetched.quality_report.min_year == 1950
    assert fetched.antibias is not None
    assert fetched.antibias.base_year_split == 2021

    # Non-existent recipe
    assert store.get_recipe("non-existent-id") is None


def test_list_recipes(tmp_path: Path, sample_recipe: BitacoraRecipe):
    base_dir = tmp_path / "bitacoras"
    db_path = tmp_path / "cache.db"
    store = BitacoraStore(base_dir=base_dir, db_path=db_path)

    assert store.list_recipes() == []

    store.save_recipe(sample_recipe)
    recipes = store.list_recipes()
    assert len(recipes) == 1
    assert recipes[0].id == sample_recipe.id


def test_sync_rebuilds_index_from_scratch(tmp_path: Path, sample_recipe: BitacoraRecipe):
    base_dir = tmp_path / "bitacoras"
    db_path = tmp_path / "cache.db"
    store = BitacoraStore(base_dir=base_dir, db_path=db_path)

    store.save_recipe(sample_recipe)

    # Delete SQLite DB file completely
    db_path.unlink()
    assert not db_path.exists()

    # Re-instantiate store and run sync
    fresh_store = BitacoraStore(base_dir=base_dir, db_path=db_path)
    # Immediately after init, DB table exists but is empty
    assert fresh_store.list_recipes() == []

    synced_count = fresh_store.sync()
    assert synced_count == 1
    assert len(fresh_store.list_recipes()) == 1
    reindexed = fresh_store.get_recipe(sample_recipe.id)
    assert reindexed is not None
    assert reindexed.country == "Chile"


def test_sync_skips_invalid_markdown_files(tmp_path: Path):
    base_dir = tmp_path / "bitacoras"
    db_path = tmp_path / "cache.db"
    store = BitacoraStore(base_dir=base_dir, db_path=db_path)

    # Create invalid markdown file
    invalid_file = base_dir / "paises" / "chile" / "broken.md"
    invalid_file.parent.mkdir(parents=True, exist_ok=True)
    invalid_file.write_text("This is not a frontmatter recipe file.", encoding="utf-8")

    # Create file with broken YAML
    broken_yaml = base_dir / "paises" / "chile" / "broken_yaml.md"
    broken_yaml.write_text("---\n: invalid : yaml : [unclosed\n---\nBody", encoding="utf-8")

    count = store.sync()
    assert count == 0
    assert store.list_recipes() == []
