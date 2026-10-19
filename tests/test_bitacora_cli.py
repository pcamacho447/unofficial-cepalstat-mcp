from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd
import pytest

from unofficial_cepalstat_mcp.bitacora.models import AntiBiasChecklist, BitacoraRecipe, DataQualityReport
from unofficial_cepalstat_mcp.cli import main


@pytest.fixture
def sample_recipe() -> BitacoraRecipe:
    return BitacoraRecipe(
        id="recipe-chile-4788",
        indicator_id=4788,
        indicator_name="Población total, según sexo",
        country="Chile",
        country_iso3="CHL",
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


def test_cli_bitacora_help(capsys):
    """Test statscepal bitacora --help exits with 0 and prints bitacora subcommands."""
    ret = main(["bitacora", "--help"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "lookup" in captured.out
    assert "list" in captured.out
    assert "sync" in captured.out
    assert "add" in captured.out


def test_cli_bitacora_no_subcommand(capsys):
    """Test statscepal bitacora without subcommands prints help and exits with 0."""
    ret = main(["bitacora"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "bitacora" in captured.out


def test_cli_bitacora_list(capsys, mocker, sample_recipe):
    """Test statscepal bitacora list displays recipes stored in BitacoraStore."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.BitacoraStore")
    mock_store_instance = MagicMock()
    mock_store_instance.list_recipes.return_value = [sample_recipe]
    mock_store_cls.return_value = mock_store_instance

    ret = main(["bitacora", "list"])
    assert ret == 0
    mock_store_instance.list_recipes.assert_called_once()

    captured = capsys.readouterr()
    assert "recipe-chile-4788" in captured.out
    assert "Población total, según sexo" in captured.out
    assert "Chile" in captured.out


def test_cli_bitacora_list_empty(capsys, mocker):
    """Test statscepal bitacora list when no recipes are found."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.BitacoraStore")
    mock_store_instance = MagicMock()
    mock_store_instance.list_recipes.return_value = []
    mock_store_cls.return_value = mock_store_instance

    ret = main(["bitacora", "list"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "No certified recipes found" in captured.out


def test_cli_bitacora_lookup(capsys, mocker, sample_recipe):
    """Test statscepal bitacora lookup searches by query, country, and tag."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.BitacoraStore")
    mock_store_instance = MagicMock()
    mock_store_instance.lookup.return_value = [sample_recipe]
    mock_store_cls.return_value = mock_store_instance

    ret = main(["bitacora", "lookup", "poblacion", "--country", "Chile", "--tag", "demografia"])
    assert ret == 0
    mock_store_instance.lookup.assert_called_once_with(
        query="poblacion",
        country="Chile",
        tag="demografia",
    )

    captured = capsys.readouterr()
    assert "Found 1 recipes" in captured.out or "recipe-chile-4788" in captured.out
    assert "recipe-chile-4788" in captured.out


def test_cli_bitacora_lookup_no_results(capsys, mocker):
    """Test statscepal bitacora lookup with no matching recipes."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.BitacoraStore")
    mock_store_instance = MagicMock()
    mock_store_instance.lookup.return_value = []
    mock_store_cls.return_value = mock_store_instance

    ret = main(["bitacora", "lookup", "nonexistent"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "No recipes found matching query." in captured.out


def test_cli_bitacora_sync(capsys, mocker):
    """Test statscepal bitacora sync triggers index rebuild."""
    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.BitacoraStore")
    mock_store_instance = MagicMock()
    mock_store_instance.sync.return_value = 7
    mock_store_cls.return_value = mock_store_instance

    ret = main(["bitacora", "sync"])
    assert ret == 0
    mock_store_instance.sync.assert_called_once()

    captured = capsys.readouterr()
    assert "7" in captured.out
    assert "synchronized" in captured.out.lower() or "indexed" in captured.out.lower()


def test_cli_bitacora_add(capsys, mocker):
    """Test statscepal bitacora add certifies and stores a recipe."""
    mock_client = mocker.patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
    mock_client_instance = MagicMock()
    mock_client.return_value.__enter__.return_value = mock_client_instance

    mock_extractor_cls = mocker.patch("unofficial_cepalstat_mcp.cli.DataExtractor")
    mock_extractor = MagicMock()
    mock_extractor.get_metadata.return_value = {
        "indicator_name": "Población total, según sexo",
        "area": "Demográficos",
        "unit": "Miles de personas",
    }
    mock_extractor.get_dataframe.return_value = pd.DataFrame([
        {"Años__ESTANDAR": 2020, "value": 19000.0},
        {"Años__ESTANDAR": 2021, "value": 19200.0},
    ])
    mock_extractor_cls.return_value = mock_extractor

    mock_audit = mocker.patch(
        "unofficial_cepalstat_mcp.cli.AntiBiasValidator.audit",
        return_value=(
            DataQualityReport(total_records=2, min_year=2020, max_year=2021),
            AntiBiasChecklist(unit_verified=True, scale_factor_note="Miles", warnings=[]),
        ),
    )

    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.BitacoraStore")
    mock_store_instance = MagicMock()
    mock_store_instance.save_recipe.return_value = Path("bitacoras/paises/chile/4788_recipe-chile-4788.md")
    mock_store_cls.return_value = mock_store_instance

    ret = main([
        "bitacora",
        "add",
        "4788",
        "--country",
        "Chile",
        "--members",
        "224, 29190",
        "--tags",
        "chile,poblacion",
    ])
    assert ret == 0
    mock_extractor.get_metadata.assert_called_once_with(4788)
    mock_extractor.get_dataframe.assert_called_once_with(4788, members=[224, 29190], decode_labels=True)
    mock_audit.assert_called_once()

    # Check save_recipe was called with a BitacoraRecipe
    mock_store_instance.save_recipe.assert_called_once()
    saved_recipe: BitacoraRecipe = mock_store_instance.save_recipe.call_args[0][0]
    assert saved_recipe.indicator_id == 4788
    assert saved_recipe.country == "Chile"
    assert saved_recipe.member_ids == [224, 29190]
    assert saved_recipe.tags == ["chile", "poblacion"]
    assert saved_recipe.status == "certified"
    assert "extractor.get_dataframe(4788" in saved_recipe.python_code

    captured = capsys.readouterr()
    assert "Certified recipe saved" in captured.out
    assert "recipe-chile-4788" in captured.out


def test_cli_bitacora_add_invalid_members(capsys):
    """Test statscepal bitacora add with non-integer members fails."""
    ret = main(["bitacora", "add", "4788", "--country", "Chile", "--members", "abc,xyz"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Error: Invalid member IDs" in captured.err


def test_cli_bitacora_add_indicator_not_found(capsys, mocker):
    """Test statscepal bitacora add when indicator metadata is empty."""
    mock_client = mocker.patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
    mock_client.return_value.__enter__.return_value = MagicMock()

    mock_extractor_cls = mocker.patch("unofficial_cepalstat_mcp.cli.DataExtractor")
    mock_extractor = MagicMock()
    mock_extractor.get_metadata.return_value = {}
    mock_extractor_cls.return_value = mock_extractor

    ret = main(["bitacora", "add", "99999", "--country", "Chile"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Indicator 99999 not found" in captured.err


def test_cli_bitacora_add_cepalstat_error(capsys, mocker):
    """Test statscepal bitacora add handles CepalStatError cleanly."""
    from unofficial_cepalstat_mcp.exceptions import CepalStatNetworkError

    mock_client = mocker.patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
    mock_client.return_value.__enter__.return_value = MagicMock()

    mock_extractor_cls = mocker.patch("unofficial_cepalstat_mcp.cli.DataExtractor")
    mock_extractor = MagicMock()
    mock_extractor.get_metadata.side_effect = CepalStatNetworkError("Network unreachable")
    mock_extractor_cls.return_value = mock_extractor

    ret = main(["bitacora", "add", "4788", "--country", "Chile"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "CEPALSTAT Error: Network unreachable" in captured.err


def test_cli_bitacora_add_with_warnings_and_custom_id(capsys, mocker):
    """Test statscepal bitacora add with custom id and printing anti-bias warnings."""
    mock_client = mocker.patch("unofficial_cepalstat_mcp.cli.CepalStatClient")
    mock_client.return_value.__enter__.return_value = MagicMock()

    mock_extractor_cls = mocker.patch("unofficial_cepalstat_mcp.cli.DataExtractor")
    mock_extractor = MagicMock()
    mock_extractor.get_metadata.return_value = {
        "indicator_name": "Proyecciones de población",
        "unit": "Personas",
    }
    mock_extractor.get_dataframe.return_value = pd.DataFrame([{"value": 100}])
    mock_extractor_cls.return_value = mock_extractor

    mocker.patch(
        "unofficial_cepalstat_mcp.cli.AntiBiasValidator.audit",
        return_value=(
            DataQualityReport(total_records=1),
            AntiBiasChecklist(
                unit_verified=True,
                warnings=["Cifras posteriores al 2020 son proyecciones."],
            ),
        ),
    )

    mock_store_cls = mocker.patch("unofficial_cepalstat_mcp.cli.BitacoraStore")
    mock_store = MagicMock()
    mock_store.save_recipe.return_value = Path("bitacoras/paises/custom/recipe-custom.md")
    mock_store_cls.return_value = mock_store

    ret = main([
        "bitacora",
        "add",
        "4788",
        "--country",
        "custom",
        "--id",
        "my-custom-recipe-id",
    ])
    assert ret == 0
    saved_recipe: BitacoraRecipe = mock_store.save_recipe.call_args[0][0]
    assert saved_recipe.id == "my-custom-recipe-id"

    captured = capsys.readouterr()
    assert "Warnings (1):" in captured.out
    assert "Cifras posteriores al 2020 son proyecciones." in captured.out

