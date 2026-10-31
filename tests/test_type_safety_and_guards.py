import subprocess
import sys

import pandas as pd

from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY
from unofficial_cepalstat_mcp.semantic.fetcher import SemanticDataFetcher
from unofficial_cepalstat_mcp.semantic.graph_builder import GraphBuilder
from unofficial_cepalstat_mcp.semantic.models import ResolutionStatus, SemanticResolutionResponse


def test_classify_dimension_accepts_none_dim_id() -> None:
    assert DEFAULT_FACET_ONTOLOGY.classify_dimension(None, "Area geográfica_(EH)") == "area"
    assert DEFAULT_FACET_ONTOLOGY.classify_dimension(None, "País__ESTANDAR") == "__structural__"


def test_format_payload_handles_none_selected_candidate_without_crash() -> None:
    fetcher = SemanticDataFetcher.__new__(SemanticDataFetcher)
    resp = SemanticResolutionResponse(status=ResolutionStatus.ABSTAINED, query="test")
    payload = fetcher._format_payload(
        df=pd.DataFrame(),
        response=resp,
        empirical_id=3328,
        year_col=None,
        country_col=None,
        is_multi_country=False,
        is_multi_year=False,
        has_breakdown=False,
        has_rescued_anchors=False,
        country_anchor_map={},
        requested_year_set={2022},
        code_by_name={},
        target_year=2022,
    )
    assert payload["observation_exists"] is False
    assert payload["indicator_name"] == ""
    assert payload["unit"] == ""


def test_graph_builder_does_not_flag_child_to_parent_curated_breakdown_as_false(tmp_path) -> None:
    store = CatalogStore(db_path=tmp_path / "g.db")
    builder = GraphBuilder(store=store)
    report = builder.build_breakdown_graph(persist=False, seed_curated=True)
    assert report.false_curated_edges == 0


def test_mypy_passes_with_zero_errors() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", "src/unofficial_cepalstat_mcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"mypy failed:\n{proc.stdout}\n{proc.stderr}"
