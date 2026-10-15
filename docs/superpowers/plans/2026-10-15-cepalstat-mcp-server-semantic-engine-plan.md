# CEPALSTAT MCP Server & Semantic Resolution Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy the official Model Context Protocol (MCP) server for CEPALSTAT (`statscepal-mcp-server`), integrating the 5-stage Semantic Resolution Engine v2 with SQLite-backed typed relationship graphs, 4 canonical MCP tools, 3 canonical MCP resources, an analytical prompt template, and a `statscepal mcp run` CLI command validated against the 25-case empirical benchmark.

**Architecture:**
1. **Relational Metadata Store (`CatalogStore` / SQLite):** Expand SQLite caching in `src/statscepal/catalog/store.py` with tables for dimensions, members, typed indicator relationships (`breakdown_of`, `alternative_measure`), and empirical temporal availability calendars, enabling `SemanticRegistry` to query SQLite with zero-cost fallback.
2. **FastMCP Server Core (`src/statscepal/mcp/server.py`):** Expose 4 core tools:
   - `cepalstat_search_indicators`: Hybrid FTS5 text + concept search.
   - `cepalstat_get_indicator_metadata`: Definition, units, native dimensions, and active members.
   - `cepalstat_resolve_indicator`: Full 5-stage semantic pipeline (equivalencia conceptual, compatibilidad dimensional, disponibilidad empírica, indicator swap tipado, y auditoría de anclas temporales).
   - `cepalstat_query_data`: Validated data extraction with structured member filters.
3. **Canonical Resources & Prompts:** Expose `cepalstat://catalog/root-phenomena`, `cepalstat://catalog/facets-dictionary`, `cepalstat://metadata/timeliness-calendar`, and prompt `cepalstat_economic_brief`.
4. **CLI Integration:** Provide `statscepal mcp run [--transport {stdio,sse}] [--port PORT]`.

**Tech Stack:** Python 3.10+, `mcp>=1.2.0`, `pydantic>=2.7.0`, `sqlite3`, `httpx>=0.27.0`, `pytest>=8.0.0`, `statscepal`.

**Specs:**
- Master MCP Spec: [`docs/specs/2026-10-15-cepalstat-mcp-server-spec.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/specs/2026-10-15-cepalstat-mcp-server-spec.md)
- Architecture v2 Normativa: [`docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/specs/2026-10-15-cepalstat-semantic-engine-architecture-v2.md)
- Benchmark & Vertical Slice Spec: [`docs/specs/2026-10-15-benchmark-y-corte-vertical-spec.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/specs/2026-10-15-benchmark-y-corte-vertical-spec.md)

## Global Constraints
- Python 3.10+ modern typing syntax (`int | None`).
- Strict Test-Driven Development (TDD) for every task: write test -> see RED -> minimal implementation -> see GREEN -> commit.
- All 142 existing non-integration tests must remain passing without regression.
- False Substitution Rate must strictly equal 0.0% (no untyped indicator swaps).
- Local resolution latency over SQLite must maintain p50 < 2.0 ms.
- Safe UTF-8 encoding for Windows console environments (`cp1252` protection).

---

### Task 1: MCP Dependency & SQLite Relational Metadata Expansion

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/statscepal/catalog/store.py`
- Modify: `src/statscepal/semantic/registry.py`
- Test: `tests/test_semantic_registry_db.py`

**Interfaces:**
- Consumes:
  - `CatalogStore._get_connection()`
  - `VERTICAL_SLICE_INDICATORS` from `src/statscepal/semantic/registry.py`
- Produces:
  - `CatalogStore.init_semantic_tables() -> None`
  - `CatalogStore.record_relationship(indicator_a: int, indicator_b: int, rel: str) -> None`
  - `CatalogStore.record_temporal_availability(indicator_id: int, country: str, year: int, status: str, prev: int | None, next: int | None) -> None`
  - `SemanticRegistry(store: CatalogStore | None = None)` reading dynamically from SQLite with static fallback.

- [ ] **Step 1: Write failing test in `tests/test_semantic_registry_db.py`**

```python
import sqlite3
from pathlib import Path
import pytest
from statscepal.catalog.store import CatalogStore
from statscepal.semantic.registry import SemanticRegistry
from statscepal.semantic.models import RelationshipType, TemporalAvailabilityStatus


def test_catalog_store_semantic_tables_and_registry(tmp_path: Path):
    db_path = tmp_path / "test_semantic.db"
    store = CatalogStore(db_path=db_path)
    store.init_semantic_tables()

    # Verify tables created
    with store._get_connection() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "indicator_relationships" in tables
        assert "temporal_availability" in tables

    # Insert a relationship and query through SemanticRegistry
    store.record_relationship(3341, 3328, "breakdown_of")
    registry = SemanticRegistry(store=store)
    rel = registry.check_relationship(3341, 3328)
    assert rel == RelationshipType.BREAKDOWN_OF
```

- [ ] **Step 2: Run test to confirm failure (RED)**

Run: `uv run pytest tests/test_semantic_registry_db.py`  
Expected: FAIL with `AttributeError: 'CatalogStore' object has no attribute 'init_semantic_tables'`

- [ ] **Step 3: Update `pyproject.toml`, `catalog/store.py`, and `semantic/registry.py`**
- Add `"mcp>=1.2.0"` to dependencies in `pyproject.toml`.
- Run: `uv sync --extra dev`.
- Implement `init_semantic_tables()`, `record_relationship()`, and `record_temporal_availability()` in `src/statscepal/catalog/store.py`.
- Update `SemanticRegistry` in `src/statscepal/semantic/registry.py` to query `CatalogStore` if provided.

- [ ] **Step 4: Run test to confirm pass (GREEN)**

Run: `uv run pytest tests/test_semantic_registry_db.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/statscepal/catalog/store.py src/statscepal/semantic/registry.py tests/test_semantic_registry_db.py
git commit -m "feat(semantic): add mcp dependency and SQLite relational metadata store"
```

---

### Task 2: FastMCP Server Core & Statistical Resolution Tools

**Files:**
- Create: `src/statscepal/mcp/__init__.py`
- Create: `src/statscepal/mcp/server.py`
- Test: `tests/test_mcp_server_tools.py`

**Interfaces:**
- Consumes:
  - `from mcp.server.fastmcp import FastMCP`
  - `SemanticResolutionEngine` from `statscepal.semantic`
  - `CatalogStore` from `statscepal.catalog.store`
  - `DataExtractor` from `statscepal.extractor`
- Produces:
  - `create_mcp_server() -> FastMCP`
  - Tools registered on server:
    - `cepalstat_search_indicators(query: str, theme: str | None = None, limit: int = 10) -> str`
    - `cepalstat_get_indicator_metadata(indicator_id: int) -> str`
    - `cepalstat_resolve_indicator(query: str, preferred_source: str = "armonizada_cepal") -> str`
    - `cepalstat_query_data(indicator_id: int, country_code: str, year: int | None = None, dimensions: dict | None = None) -> str`

- [ ] **Step 1: Write failing test in `tests/test_mcp_server_tools.py`**

```python
import json
import pytest
from statscepal.mcp.server import create_mcp_server


@pytest.mark.anyio
async def test_mcp_server_tools_registered():
    mcp = create_mcp_server()
    assert mcp.name == "statscepal-mcp-server"

    # Call cepalstat_resolve_indicator tool directly
    tool_fn = mcp.get_tool("cepalstat_resolve_indicator")
    assert tool_fn is not None
    
    result_json = await tool_fn.run({"query": "Pobreza total en Brasil en 2021"})
    data = json.loads(result_json)
    assert data["status"] == "RESOLVED"
    assert data["selected_candidate"]["indicator_id"] == 3328
```

- [ ] **Step 2: Run test to confirm failure (RED)**

Run: `uv run pytest tests/test_mcp_server_tools.py`  
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.mcp'`

- [ ] **Step 3: Implement `src/statscepal/mcp/server.py` and `__init__.py`**
- Create `src/statscepal/mcp/__init__.py` exporting `create_mcp_server`.
- Create `src/statscepal/mcp/server.py` defining `create_mcp_server()` with `FastMCP("statscepal-mcp-server")` and decorating the 4 tools with `@mcp.tool()`.

- [ ] **Step 4: Run test to confirm pass (GREEN)**

Run: `uv run pytest tests/test_mcp_server_tools.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/mcp/ tests/test_mcp_server_tools.py
git commit -m "feat(mcp): implement FastMCP server core with statistical resolution tools"
```

---

### Task 3: MCP Canonical Resources & Analytical Prompts

**Files:**
- Modify: `src/statscepal/mcp/server.py`
- Test: `tests/test_mcp_resources.py`

**Interfaces:**
- Consumes:
  - `@mcp.resource(uri)`
  - `@mcp.prompt(name)`
  - `VERTICAL_SLICE_INDICATORS`, `CONCEPT_CANONICAL_DEFAULTS` from `statscepal.semantic.registry`
- Produces:
  - Resource `cepalstat://catalog/root-phenomena` -> JSON
  - Resource `cepalstat://catalog/facets-dictionary` -> JSON
  - Resource `cepalstat://metadata/timeliness-calendar` -> JSON
  - Prompt `cepalstat_economic_brief(country: str, year: int)` -> Message prompts

- [ ] **Step 1: Write failing test in `tests/test_mcp_resources.py`**

```python
import json
import pytest
from statscepal.mcp.server import create_mcp_server


@pytest.mark.anyio
async def test_mcp_resources_and_prompts():
    mcp = create_mcp_server()

    # Verify resource root-phenomena
    resource_fn = mcp.get_resource("cepalstat://catalog/root-phenomena")
    assert resource_fn is not None
    content = await resource_fn.read()
    data = json.loads(content)
    assert "POBREZA" in data
    assert data["POBREZA"]["canonical_id"] == 3328

    # Verify prompt economic brief
    prompt_fn = mcp.get_prompt("cepalstat_economic_brief")
    assert prompt_fn is not None
    messages = await prompt_fn.render({"country": "Chile", "year": "2022"})
    assert len(messages) >= 1
    assert "Chile" in messages[0].content.text
```

- [ ] **Step 2: Run test to confirm failure (RED)**

Run: `uv run pytest tests/test_mcp_resources.py`  
Expected: FAIL with resource not found.

- [ ] **Step 3: Implement resources and prompts in `src/statscepal/mcp/server.py`**
- Add `@mcp.resource("cepalstat://catalog/root-phenomena")`.
- Add `@mcp.resource("cepalstat://catalog/facets-dictionary")`.
- Add `@mcp.resource("cepalstat://metadata/timeliness-calendar")`.
- Add `@mcp.prompt("cepalstat_economic_brief")`.

- [ ] **Step 4: Run test to confirm pass (GREEN)**

Run: `uv run pytest tests/test_mcp_resources.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/mcp/server.py tests/test_mcp_resources.py
git commit -m "feat(mcp): add canonical MCP resources and economic brief prompt template"
```

---

### Task 4: CLI Subcommand Integration (`statscepal mcp run`)

**Files:**
- Modify: `src/statscepal/cli.py`
- Test: `tests/test_cli_mcp.py`

**Interfaces:**
- Consumes:
  - `create_mcp_server` from `statscepal.mcp`
- Produces:
  - Subcommand `statscepal mcp run` supporting `--transport {stdio,sse}` and `--port PORT` flags.

- [ ] **Step 1: Write failing test in `tests/test_cli_mcp.py`**

```python
from unittest.mock import patch, MagicMock
from statscepal.cli import main


def test_cli_mcp_subcommand_parser():
    with patch("statscepal.mcp.server.create_mcp_server") as mock_server_factory:
        mock_server = MagicMock()
        mock_server_factory.return_value = mock_server

        # Test help output for mcp command
        exit_code = main(["mcp", "run", "--transport", "stdio"])
        assert exit_code == 0
        mock_server.run.assert_called_once_with(transport="stdio")
```

- [ ] **Step 2: Run test to confirm failure (RED)**

Run: `uv run pytest tests/test_cli_mcp.py`  
Expected: FAIL with `invalid choice: 'mcp'`.

- [ ] **Step 3: Modify `src/statscepal/cli.py`**
- Add `mcp` subparser to `argparse` hierarchy.
- Add `run` command with `--transport` (`stdio` default, `sse`) and `--port` (`8000` default).
- Implement execution handler calling `create_mcp_server().run(transport=args.transport)`.

- [ ] **Step 4: Run test to confirm pass (GREEN)**

Run: `uv run pytest tests/test_cli_mcp.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/cli.py tests/test_cli_mcp.py
git commit -m "feat(cli): add statscepal mcp run subcommand for stdio and sse transports"
```

---

### Task 5: End-to-End Benchmark & Live Integration Verification

**Files:**
- Create: `tests/test_mcp_e2e_benchmark.py`

**Interfaces:**
- Consumes:
  - `create_mcp_server` from `statscepal.mcp`
  - `BenchmarkEvaluator` from `statscepal.semantic`
  - `tests/benchmark/semantic_benchmark_cases.json`
- Produces:
  - E2E verification executing the 25 benchmark cases through the registered MCP tool `cepalstat_resolve_indicator`.

- [ ] **Step 1: Write E2E test in `tests/test_mcp_e2e_benchmark.py`**

```python
import json
from pathlib import Path
import pytest
from statscepal.mcp.server import create_mcp_server
from statscepal.semantic import BenchmarkEvaluator


@pytest.mark.anyio
async def test_full_benchmark_through_mcp_tool():
    mcp = create_mcp_server()
    resolve_tool = mcp.get_tool("cepalstat_resolve_indicator")
    assert resolve_tool is not None

    cases_path = Path(__file__).parent / "benchmark" / "semantic_benchmark_cases.json"
    evaluator = BenchmarkEvaluator(cases_path=cases_path)
    cases = evaluator.load_cases()
    assert len(cases) == 25

    passed = 0
    for case in cases:
        raw_res = await resolve_tool.run({"query": case.query})
        data = json.loads(raw_res)
        assert data["status"] == case.expected_status.value
        if case.expected_indicator_id:
            assert data["selected_candidate"]["indicator_id"] == case.expected_indicator_id
        passed += 1

    assert passed == 25
```

- [ ] **Step 2: Run test to verify pass (GREEN)**

Run: `uv run pytest tests/test_mcp_e2e_benchmark.py`  
Expected: PASS (25 out of 25 passed)

- [ ] **Step 3: Run full regression test suite**

Run: `uv run pytest -m "not integration"`  
Expected: All 145+ tests pass with zero regressions.

- [ ] **Step 4: Commit**

```bash
git add tests/test_mcp_e2e_benchmark.py
git commit -m "test(mcp): verify full 25-case semantic benchmark through MCP JSON-RPC tool"
```
