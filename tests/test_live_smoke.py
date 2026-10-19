"""Live integration smoke tests for CEPALSTAT API and CLI."""

import subprocess
import sys
import pandas as pd
import pytest

from unofficial_cepalstat_mcp.cli import main
from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.dimensions import DimensionManager
from unofficial_cepalstat_mcp.extractor import DataExtractor
from unofficial_cepalstat_mcp.thematic_tree import ThematicTree


@pytest.mark.integration
def test_live_api_end_to_end():
    """Verify full Python API flow against live CEPALSTAT API."""
    with CepalStatClient() as client:
        # Search for indicator
        tree = ThematicTree(client)
        results = tree.search("Población total")
        indicator_ids = [item.indicator_id for item in results]
        assert 4788 in indicator_ids, "Expected indicator 4788 in search results"

        # Resolve dimensions and Chile ID (224)
        dm = DimensionManager(client)
        dimensions = dm.get_dimensions(4788)
        assert len(dimensions) > 0, "Expected at least one dimension for indicator 4788"

        # Resolve Chile member ID via find_member_id or direct lookup
        chile_id = dm.find_member_id(4788, "País", "Chile")
        if chile_id is None:
            # Fallback search across any dimension for 'Chile'
            for dim in dimensions:
                for member in dim.members:
                    if member.name.lower() == "chile":
                        chile_id = member.id
                        break
                if chile_id is not None:
                    break

        assert chile_id == 224, f"Expected Chile member ID 224, got {chile_id}"

        # Fetch DataFrame with members filter (Chile=224, 2020=29190)
        extractor = DataExtractor(client, dm)
        df = extractor.get_dataframe(4788, members=[224, 29190])

        assert not df.empty, "DataFrame should contain records"
        assert len(df) > 0, "DataFrame should have rows"
        # Verify decoded 'Chile' is in the DataFrame values
        assert (df == "Chile").any().any(), "DataFrame should contain decoded member 'Chile'"
        # Verify 'value' column is numeric/float
        assert "value" in df.columns, "DataFrame should contain 'value' column"
        assert pd.api.types.is_float_dtype(df["value"]), "'value' column should be float"
        assert not df["value"].isna().all(), "'value' column should have non-null numeric values"


@pytest.mark.integration
def test_live_cli_flow(capsys):
    """Verify live CLI flow with search, info, and fetch commands."""
    # 1. statscepal search poblacion --limit 3
    ret_search = main(["search", "poblacion", "--limit", "3"])
    assert ret_search == 0
    captured_search = capsys.readouterr()
    assert "Found" in captured_search.out

    # 2. statscepal info 4788
    ret_info = main(["info", "4788"])
    assert ret_info == 0
    captured_info = capsys.readouterr()
    assert "Indicator 4788" in captured_info.out or "4788" in captured_info.out
    assert "Name:" in captured_info.out
    assert "Area:" in captured_info.out

    # 3. statscepal fetch 4788 --members 224,29190
    ret_fetch = main(["fetch", "4788", "--members", "224,29190"])
    assert ret_fetch == 0
    captured_fetch = capsys.readouterr()
    assert "Chile" in captured_fetch.out
    assert "2020" in captured_fetch.out
