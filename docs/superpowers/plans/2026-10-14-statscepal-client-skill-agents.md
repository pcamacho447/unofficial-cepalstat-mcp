# CEPALSTAT Python Client, Skill, and Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a robust Python client (`statscepal`) for the UN CEPALSTAT Open Data REST API, an Antigravity custom skill (`cepalstat-api`), and a specialized AI agent (`cepalstat_analyst`) for statistical research across Latin America and the Caribbean.

**Architecture:** A layered architecture with a typed low-level HTTP client (`cepalstat_client.py`), domain modules for thematic tree navigation (`thematic_tree.py`), dimension resolution (`dimensions.py`), and DataFrame extraction (`extractor.py`). This is complemented by a CLI interface (`cli.py`), an Antigravity skill specification (`SKILL.md`), and an Antigravity subagent definition.

**Tech Stack:** Python 3.12+, `uv`, `httpx`, `pandas`, `pydantic`, `typer` (or `argparse`), `pytest`, `pytest-mock`, Antigravity Customizations.

**Spec:** [docs/specs/2026-10-14-statscepal-spec.md](file:///C:/papx/statscepal/docs/specs/2026-10-14-statscepal-spec.md)

## Global Constraints

- Base API URL: `https://api-cepalstat.cepal.org`
- Authentication: None (Public Open Data)
- Python Version: >= 3.10 (Targeting 3.12)
- Formats: JSON for parsing, optional CSV/Excel export
- Package Management: `uv` with `pyproject.toml`
- Test framework: `pytest` with 100% mocked offline tests for unit suites and isolated smoke integration tests
- Code style: Typed Python, Google-style docstrings, PEP 8 compliant

---

### Task 1: Project Setup and Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/statscepal/__init__.py`
- Create: `tests/__init__.py`
- Test: `tests/test_version.py`

**Interfaces:**
- Consumes: None
- Produces: `statscepal.__version__ = "0.1.0"`

- [ ] **Step 1: Write the failing test**

File: `tests/test_version.py`
```python
import statscepal


def test_package_version():
    assert statscepal.__version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_version.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal'`

- [ ] **Step 3: Write minimal implementation**

File: `pyproject.toml`
```toml
[project]
name = "statscepal"
version = "0.1.0"
description = "Python client and tools for UN CEPALSTAT Open Data API"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.7.0",
    "pandas>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.14.0",
    "respx>=0.21.0",
]

[project.scripts]
statscepal = "statscepal.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/statscepal"]
```

File: `.gitignore`
```gitignore
__pycache__/
*.py[cod]
*$py.class
.venv/
dist/
build/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
```

File: `README.md`
```markdown
# statscepal

Python client and AI agent toolset for UN CEPALSTAT Open Data API.
```

File: `src/statscepal/__init__.py`
```python
"""statscepal: Python client for UN CEPALSTAT Open Data API."""

__version__ = "0.1.0"

from statscepal.client import CepalStatClient

__all__ = ["__version__", "CepalStatClient"]
```

File: `tests/__init__.py`
```python
"""Tests for statscepal."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_version.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore README.md src/ tests/
git commit -m "chore: initialize project scaffolding with uv and pytest"
```

---

### Task 2: Core HTTP API Client (`CepalStatClient`)

**Files:**
- Create: `src/statscepal/client.py`
- Create: `src/statscepal/exceptions.py`
- Test: `tests/test_client.py`

**Interfaces:**
- Consumes: `httpx`
- Produces: `CepalStatClient(base_url, timeout, lang)` with methods:
  - `get(endpoint, params=None) -> dict`
  - `get_raw(endpoint, params=None) -> bytes`

- [ ] **Step 1: Write the failing test**

File: `tests/test_client.py`
```python
import pytest
import respx
import httpx
from statscepal.client import CepalStatClient
from statscepal.exceptions import CepalStatAPIError, CepalStatNetworkError


@respx.mock
def test_client_get_json_success():
    mock_route = respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/test").mock(
        return_value=httpx.Response(
            200,
            json={
                "header": {"success": True, "code": 200},
                "body": {"message": "ok"},
                "footer": {"records": 1},
            },
        )
    )

    client = CepalStatClient()
    response = client.get("/cepalstat/api/v1/test")

    assert mock_route.called
    assert response["body"]["message"] == "ok"


@respx.mock
def test_client_api_error_raised_on_404():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/bad").mock(
        return_value=httpx.Response(404, json={"message": "Not found"})
    )

    client = CepalStatClient()
    with pytest.raises(CepalStatAPIError) as exc_info:
        client.get("/cepalstat/api/v1/bad")

    assert exc_info.value.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.client'`

- [ ] **Step 3: Write minimal implementation**

File: `src/statscepal/exceptions.py`
```python
"""Exceptions for statscepal."""


class CepalStatError(Exception):
    """Base exception for all statscepal errors."""


class CepalStatNetworkError(CepalStatError):
    """Raised when network transport fails."""


class CepalStatAPIError(CepalStatError):
    """Raised when the CEPALSTAT API returns an error status code."""

    def __init__(self, message: str, status_code: int = 500, response_data: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
```

File: `src/statscepal/client.py`
```python
"""HTTP client for the CEPALSTAT API."""

from typing import Any
import httpx

from statscepal.exceptions import CepalStatAPIError, CepalStatNetworkError

DEFAULT_BASE_URL = "https://api-cepalstat.cepal.org"
DEFAULT_TIMEOUT = 30.0


class CepalStatClient:
    """Core HTTP client for interacting with the CEPALSTAT REST API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        lang: str = "es",
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.lang = lang
        self.timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        self._client.close()

    def __enter__(self) -> "CepalStatClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request expecting JSON."""
        clean_endpoint = "/" + endpoint.lstrip("/")
        query_params: dict[str, Any] = {"lang": self.lang, "format": "json"}
        if params:
            query_params.update(params)

        try:
            response = self._client.get(clean_endpoint, params=query_params)
        except httpx.RequestError as exc:
            raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc

        if response.status_code >= 400:
            raise CepalStatAPIError(
                f"CEPALSTAT API error {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except Exception as exc:
            raise CepalStatAPIError(f"Invalid JSON returned: {response.text}") from exc

    def get_raw(
        self, endpoint: str, params: dict[str, Any] | None = None, response_format: str = "csv"
    ) -> bytes:
        """Make a GET request expecting raw bytes (CSV, Excel, etc.)."""
        clean_endpoint = "/" + endpoint.lstrip("/")
        query_params: dict[str, Any] = {"lang": self.lang, "format": response_format}
        if params:
            query_params.update(params)

        try:
            response = self._client.get(clean_endpoint, params=query_params)
        except httpx.RequestError as exc:
            raise CepalStatNetworkError(f"Network error querying {clean_endpoint}: {exc}") from exc

        if response.status_code >= 400:
            raise CepalStatAPIError(
                f"CEPALSTAT API error {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        return response.content
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/exceptions.py src/statscepal/client.py tests/test_client.py
git commit -m "feat: implement CepalStatClient with robust error handling"
```

---

### Task 3: Thematic Tree Navigation and Indicator Search

**Files:**
- Create: `src/statscepal/thematic_tree.py`
- Test: `tests/test_thematic_tree.py`

**Interfaces:**
- Consumes: `CepalStatClient`
- Produces:
  - `ThematicTree(client)`
  - `IndicatorItem(id: int, name: str, path: str)`
  - `search_indicators(keyword: str) -> list[IndicatorItem]`
  - `get_tree() -> dict`

- [ ] **Step 1: Write the failing test**

File: `tests/test_thematic_tree.py`
```python
import pytest
import respx
import httpx
from statscepal.client import CepalStatClient
from statscepal.thematic_tree import ThematicTree


MOCK_TREE_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "name": "Clasificación temática general",
        "theme_id": 27,
        "children": [
            {
                "name": "Demográficos y sociales",
                "area_id": 394,
                "children": [
                    {
                        "name": "Demográficos",
                        "area_id": 395,
                        "children": [
                            {
                                "name": "Población total, según sexo",
                                "order": 10,
                                "indicator_id": 4788,
                            },
                            {
                                "name": "Tasa de crecimiento anual",
                                "order": 50,
                                "indicator_id": 4795,
                            },
                        ],
                    }
                ],
            }
        ],
    },
    "footer": {"records": 1},
}


@respx.mock
def test_search_indicators():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree").mock(
        return_value=httpx.Response(200, json=MOCK_TREE_PAYLOAD)
    )

    client = CepalStatClient()
    tree = ThematicTree(client)

    results = tree.search("población")
    assert len(results) == 1
    assert results[0].indicator_id == 4788
    assert "Población total" in results[0].name
    assert "Demográficos y sociales" in results[0].path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_thematic_tree.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.thematic_tree'`

- [ ] **Step 3: Write minimal implementation**

File: `src/statscepal/thematic_tree.py`
```python
"""CEPALSTAT Thematic Tree navigation and indicator search."""

from typing import Any
from pydantic import BaseModel
from statscepal.client import CepalStatClient


class IndicatorItem(BaseModel):
    """An indicator discovered in the thematic tree."""

    indicator_id: int
    name: str
    order: int | None = None
    path: str = ""


class ThematicTree:
    """Manages downloading, traversing, and searching the thematic tree."""

    def __init__(self, client: CepalStatClient):
        self.client = client
        self._raw_tree: dict[str, Any] | None = None
        self._indicators: list[IndicatorItem] | None = None

    def get_raw_tree(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch the raw thematic tree JSON."""
        if self._raw_tree is None or force_refresh:
            data = self.client.get("/cepalstat/api/v1/thematic-tree")
            self._raw_tree = data.get("body", {})
        return self._raw_tree

    def list_all_indicators(self, force_refresh: bool = False) -> list[IndicatorItem]:
        """Recursively collect all indicators present in the tree."""
        if self._indicators is not None and not force_refresh:
            return self._indicators

        root = self.get_raw_tree(force_refresh=force_refresh)
        items: list[IndicatorItem] = []

        def traverse(node: dict[str, Any], current_path: list[str]) -> None:
            name = node.get("name", "")
            new_path = current_path + [name] if name else current_path

            if "indicator_id" in node:
                items.append(
                    IndicatorItem(
                        indicator_id=int(node["indicator_id"]),
                        name=name,
                        order=node.get("order"),
                        path=" > ".join(current_path),
                    )
                )
            elif "children" in node and isinstance(node["children"], list):
                for child in node["children"]:
                    if isinstance(child, dict):
                        traverse(child, new_path)

        traverse(root, [])
        self._indicators = items
        return self._indicators

    def search(self, query: str) -> list[IndicatorItem]:
        """Search indicators by name or topic path (case-insensitive)."""
        q = query.lower()
        all_inds = self.list_all_indicators()
        return [ind for ind in all_inds if q in ind.name.lower() or q in ind.path.lower()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_thematic_tree.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/thematic_tree.py tests/test_thematic_tree.py
git commit -m "feat: implement ThematicTree search and indicator traversal"
```

---

### Task 4: Dimension and Member Resolution

**Files:**
- Create: `src/statscepal/dimensions.py`
- Test: `tests/test_dimensions.py`

**Interfaces:**
- Consumes: `CepalStatClient`
- Produces:
  - `Dimension(id: int, name: str, members: list[Member])`
  - `Member(id: int, name: str, order: int)`
  - `DimensionManager(client)` with:
    - `get_dimensions(indicator_id: int) -> list[Dimension]`
    - `find_member_id(indicator_id: int, dimension_name_or_id: str | int, member_name: str) -> int | None`

- [ ] **Step 1: Write the failing test**

File: `tests/test_dimensions.py`
```python
import pytest
import respx
import httpx
from statscepal.client import CepalStatClient
from statscepal.dimensions import DimensionManager


MOCK_DIMENSIONS_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "dimensions": [
            {
                "id": 208,
                "name": "País__ESTANDAR",
                "members": [
                    {"id": 224, "name": "Chile", "order": 110},
                    {"id": 218, "name": "Argentina", "order": 10},
                ],
            },
            {
                "id": 29117,
                "name": "Años__ESTANDAR",
                "members": [
                    {"id": 29190, "name": "2020", "order": 2020},
                    {"id": 29191, "name": "2021", "order": 2021},
                ],
            },
        ]
    },
    "footer": {"records": 2},
}


@respx.mock
def test_dimension_manager():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/dimensions").mock(
        return_value=httpx.Response(200, json=MOCK_DIMENSIONS_PAYLOAD)
    )

    client = CepalStatClient()
    manager = DimensionManager(client)

    dims = manager.get_dimensions(4788)
    assert len(dims) == 2
    assert dims[0].name == "País__ESTANDAR"

    # Find member ID for Chile
    chile_id = manager.find_member_id(4788, "País", "Chile")
    assert chile_id == 224

    # Find member ID for year 2020
    year_id = manager.find_member_id(4788, 29117, "2020")
    assert year_id == 29190
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dimensions.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.dimensions'`

- [ ] **Step 3: Write minimal implementation**

File: `src/statscepal/dimensions.py`
```python
"""Dimension and Member resolution for CEPALSTAT indicators."""

from typing import Any
from pydantic import BaseModel
from statscepal.client import CepalStatClient


class Member(BaseModel):
    """A member element inside a dimension (e.g. Chile, 2020, Ambos sexos)."""

    id: int
    name: str
    order: int | None = None
    parent: int | None = None
    selected: int | None = None


class Dimension(BaseModel):
    """A dimension of an indicator (e.g. País, Años, Sexo)."""

    id: int
    name: str
    members: list[Member] = []


class DimensionManager:
    """Retrieves and searches dimensions and member IDs for indicators."""

    def __init__(self, client: CepalStatClient):
        self.client = client
        self._cache: dict[int, list[Dimension]] = {}

    def get_dimensions(self, indicator_id: int, force_refresh: bool = False) -> list[Dimension]:
        """Fetch all dimensions and members for an indicator."""
        if indicator_id in self._cache and not force_refresh:
            return self._cache[indicator_id]

        response = self.client.get(f"/cepalstat/api/v1/indicator/{indicator_id}/dimensions")
        raw_dims = response.get("body", {}).get("dimensions", [])

        dimensions: list[Dimension] = []
        for raw_dim in raw_dims:
            members = [
                Member(
                    id=m["id"],
                    name=m["name"],
                    order=m.get("order"),
                    parent=m.get("parent"),
                    selected=m.get("selected"),
                )
                for m in raw_dim.get("members", [])
            ]
            dimensions.append(
                Dimension(
                    id=raw_dim["id"],
                    name=raw_dim["name"],
                    members=members,
                )
            )

        self._cache[indicator_id] = dimensions
        return dimensions

    def find_member_id(
        self,
        indicator_id: int,
        dimension_name_or_id: str | int,
        member_name: str,
    ) -> int | None:
        """Find the numeric member ID by partial or exact matching."""
        dims = self.get_dimensions(indicator_id)
        target_dim: Dimension | None = None

        if isinstance(dimension_name_or_id, int):
            for d in dims:
                if d.id == dimension_name_or_id:
                    target_dim = d
                    break
        else:
            dim_q = dimension_name_or_id.lower()
            for d in dims:
                if dim_q in d.name.lower():
                    target_dim = d
                    break

        if not target_dim:
            return None

        mem_q = member_name.lower().strip()
        for m in target_dim.members:
            if m.name.lower().strip() == mem_q:
                return m.id

        # Fallback to substring matching
        for m in target_dim.members:
            if mem_q in m.name.lower():
                return m.id

        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dimensions.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/dimensions.py tests/test_dimensions.py
git commit -m "feat: implement DimensionManager and Member resolution"
```

---

### Task 5: Data and Record Extractor (`DataExtractor`)

**Files:**
- Create: `src/statscepal/extractor.py`
- Modify: `src/statscepal/__init__.py`
- Test: `tests/test_extractor.py`

**Interfaces:**
- Consumes: `CepalStatClient`, `DimensionManager`
- Produces:
  - `DataExtractor(client, dimension_manager)`
  - `get_records(indicator_id: int, members: list[int] | None = None) -> list[dict]`
  - `get_dataframe(indicator_id: int, members: list[int] | None = None, decode_labels: bool = True) -> pd.DataFrame`
  - `get_metadata(indicator_id: int) -> dict`

- [ ] **Step 1: Write the failing test**

File: `tests/test_extractor.py`
```python
import pytest
import respx
import httpx
import pandas as pd
from statscepal.client import CepalStatClient
from statscepal.dimensions import DimensionManager
from statscepal.extractor import DataExtractor


MOCK_METADATA_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "metadata": {
            "indicator_id": 4788,
            "indicator_name": "Población total, según sexo",
            "unit": "Miles de personas",
        }
    },
}

MOCK_RECORDS_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "data": [
            {
                "value": "19370.6",
                "iso3": "CHL",
                "dim_208": 224,
                "dim_29117": 29190,
            }
        ]
    },
    "footer": {"records": 1},
}

MOCK_DIMENSIONS_PAYLOAD = {
    "header": {"success": True, "code": 200},
    "body": {
        "dimensions": [
            {
                "id": 208,
                "name": "País__ESTANDAR",
                "members": [{"id": 224, "name": "Chile"}],
            },
            {
                "id": 29117,
                "name": "Años__ESTANDAR",
                "members": [{"id": 29190, "name": "2020"}],
            },
        ]
    },
}


@respx.mock
def test_get_dataframe_decoded():
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/metadata").mock(
        return_value=httpx.Response(200, json=MOCK_METADATA_PAYLOAD)
    )
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/records").mock(
        return_value=httpx.Response(200, json=MOCK_RECORDS_PAYLOAD)
    )
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/4788/dimensions").mock(
        return_value=httpx.Response(200, json=MOCK_DIMENSIONS_PAYLOAD)
    )

    client = CepalStatClient()
    extractor = DataExtractor(client)

    df = extractor.get_dataframe(4788, members=[224, 29190], decode_labels=True)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.loc[0, "value"] == 19370.6
    assert df.loc[0, "iso3"] == "CHL"
    assert df.loc[0, "País__ESTANDAR"] == "Chile"
    assert df.loc[0, "Años__ESTANDAR"] == "2020"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_extractor.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.extractor'`

- [ ] **Step 3: Write minimal implementation**

File: `src/statscepal/extractor.py`
```python
"""Data and records extractor for CEPALSTAT indicators."""

from typing import Any
import pandas as pd
from statscepal.client import CepalStatClient
from statscepal.dimensions import DimensionManager


class DataExtractor:
    """Extracts indicator metadata and records as dictionaries or DataFrames."""

    def __init__(
        self,
        client: CepalStatClient,
        dimension_manager: DimensionManager | None = None,
    ):
        self.client = client
        self.dimension_manager = dimension_manager or DimensionManager(client)

    def get_metadata(self, indicator_id: int) -> dict[str, Any]:
        """Fetch metadata for an indicator."""
        response = self.client.get(f"/cepalstat/api/v1/indicator/{indicator_id}/metadata")
        return response.get("body", {}).get("metadata", {})

    def get_records(
        self, indicator_id: int, members: list[int] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch raw records for an indicator."""
        params: dict[str, Any] = {}
        if members:
            params["members"] = ",".join(str(m) for m in members)

        response = self.client.get(f"/cepalstat/api/v1/indicator/{indicator_id}/records", params=params)
        return response.get("body", {}).get("data", [])

    def get_dataframe(
        self,
        indicator_id: int,
        members: list[int] | None = None,
        decode_labels: bool = True,
    ) -> pd.DataFrame:
        """Fetch indicator records converted into a clean Pandas DataFrame."""
        records = self.get_records(indicator_id, members=members)
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        # Convert numeric values to float where possible
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

        if decode_labels:
            dimensions = self.dimension_manager.get_dimensions(indicator_id)
            for dim in dimensions:
                dim_col = f"dim_{dim.id}"
                if dim_col in df.columns:
                    member_map = {m.id: m.name for m in dim.members}
                    df[dim.name] = df[dim_col].map(member_map).fillna(df[dim_col])
                    df.drop(columns=[dim_col], inplace=True)

        return df
```

File: `src/statscepal/__init__.py`
```python
"""statscepal: Python client for UN CEPALSTAT Open Data API."""

__version__ = "0.1.0"

from statscepal.client import CepalStatClient
from statscepal.thematic_tree import ThematicTree
from statscepal.dimensions import DimensionManager
from statscepal.extractor import DataExtractor

__all__ = [
    "__version__",
    "CepalStatClient",
    "ThematicTree",
    "DimensionManager",
    "DataExtractor",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_extractor.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/extractor.py src/statscepal/__init__.py tests/test_extractor.py
git commit -m "feat: implement DataExtractor with DataFrame conversion and label decoding"
```

---

### Task 6: CLI Interface (`statscepal`)

**Files:**
- Create: `src/statscepal/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `ThematicTree`, `DataExtractor`, `DimensionManager`
- Produces: Command line commands:
  - `statscepal search <keyword>`
  - `statscepal info <indicator_id>`
  - `statscepal fetch <indicator_id> [--output file.csv]`

- [ ] **Step 1: Write the failing test**

File: `tests/test_cli.py`
```python
import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "statscepal.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "CEPALSTAT" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py`
Expected: FAIL with `No module named statscepal.cli`

- [ ] **Step 3: Write minimal implementation**

File: `src/statscepal/cli.py`
```python
"""Command Line Interface for CEPALSTAT."""

import argparse
import sys
from statscepal.client import CepalStatClient
from statscepal.thematic_tree import ThematicTree
from statscepal.extractor import DataExtractor


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="statscepal",
        description="CEPALSTAT Open Data CLI tool for Latin America and Caribbean statistics.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # search
    search_parser = subparsers.add_parser("search", help="Search indicators by keyword")
    search_parser.add_argument("query", help="Keyword to search for")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results to display")

    # info
    info_parser = subparsers.add_parser("info", help="Get metadata of an indicator")
    info_parser.add_argument("indicator_id", type=int, help="Indicator ID")

    # fetch
    fetch_parser = subparsers.add_parser("fetch", help="Fetch records and output as table or CSV")
    fetch_parser.add_argument("indicator_id", type=int, help="Indicator ID")
    fetch_parser.add_argument("--members", help="Comma-separated member IDs")
    fetch_parser.add_argument("--csv", help="Save output to CSV file")

    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 0

    with CepalStatClient() as client:
        if parsed.command == "search":
            tree = ThematicTree(client)
            results = tree.search(parsed.query)
            if not results:
                print(f"No indicators found matching '{parsed.query}'.")
                return 0
            print(f"Found {len(results)} indicators (showing top {min(len(results), parsed.limit)}):")
            for item in results[: parsed.limit]:
                print(f"  [{item.indicator_id}] {item.name}")
                if item.path:
                    print(f"      Path: {item.path}")

        elif parsed.command == "info":
            extractor = DataExtractor(client)
            meta = extractor.get_metadata(parsed.indicator_id)
            if not meta:
                print(f"Indicator {parsed.indicator_id} not found.")
                return 1
            print(f"=== Indicator {parsed.indicator_id} ===")
            print(f"Name: {meta.get('indicator_name')}")
            print(f"Area: {meta.get('area')}")
            print(f"Unit: {meta.get('unit')}")
            print(f"Definition: {meta.get('definition')}")

        elif parsed.command == "fetch":
            extractor = DataExtractor(client)
            member_ids = [int(m.strip()) for m in parsed.members.split(",")] if parsed.members else None
            df = extractor.get_dataframe(parsed.indicator_id, members=member_ids, decode_labels=True)
            if df.empty:
                print("No data records returned.")
                return 0
            if parsed.csv:
                df.to_csv(parsed.csv, index=False)
                print(f"Saved {len(df)} rows to {parsed.csv}")
            else:
                print(df.to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/cli.py tests/test_cli.py
git commit -m "feat: implement statscepal CLI for searching, inspecting, and exporting data"
```

---

### Task 7: Antigravity Custom Skill (`cepalstat-api`)

**Files:**
- Create: `.agents/skills/cepalstat-api/SKILL.md`
- Create: `.agents/skills/cepalstat-api/references/dimensions-reference.md`
- Test: Verification check that YAML frontmatter and documentation follow `writing-skills` standards

**Interfaces:**
- Consumes: CEPALSTAT API OpenAPI documentation
- Produces: Antigravity Skill discovered by agent runtimes

- [ ] **Step 1: Write the skill reference documentation**

File: `.agents/skills/cepalstat-api/references/dimensions-reference.md`
```markdown
# CEPALSTAT Dimensions Reference

## Common Country Member IDs (dim_208: País__ESTANDAR)
- Latin America and Caribbean (Total): `208`
- Argentina: `218`
- Bolivia: `221`
- Brasil: `222`
- Chile: `224`
- Colombia: `225`
- Costa Rica: `226`
- Cuba: `227`
- Ecuador: `229`
- El Salvador: `230`
- Guatemala: `233`
- Honduras: `235`
- México: `238`
- Nicaragua: `239`
- Panamá: `240`
- Paraguay: `241`
- Perú: `242`
- República Dominicana: `244`
- Uruguay: `248`
- Venezuela: `249`

## Year Dimension ID (dim_29117: Años__ESTANDAR)
- 2018: `29188`
- 2019: `29189`
- 2020: `29190`
- 2021: `29191`
- 2022: `29192`
- 2023: `29193`
- 2024: `29194`
```

- [ ] **Step 2: Write the SKILL.md file**

File: `.agents/skills/cepalstat-api/SKILL.md`
```markdown
---
name: cepalstat-api
description: Use when the user asks to query, analyze, search, or visualize socioeconomic, demographic, or environmental statistics for Latin America and the Caribbean from UN CEPAL / ECLAC CEPALSTAT Open Data API.
---

# CEPALSTAT Open Data API Skill

Use this skill to retrieve verified statistics from the United Nations Economic Commission for Latin America and the Caribbean (UN CEPAL / ECLAC).

## API Overview
- **Base URL:** `https://api-cepalstat.cepal.org`
- **Auth:** No authentication required (Public Open Data)
- **Formats:** JSON, CSV, Excel

## Standard 3-Step Query Workflow

### Step 1: Find the Indicator
Search indicator by topic using `statscepal` CLI or HTTP call:
```bash
statscepal search "pobreza"
# or via API
GET https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree?lang=es&format=json
```

### Step 2: Resolve Dimensions and Member IDs
Before requesting data records, fetch the dimension members (Country, Year, Sex, etc.):
```bash
GET https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/{indicator_id}/dimensions?lang=es&format=json
```
Refer to `references/dimensions-reference.md` for fast lookup of standard countries and years.

### Step 3: Fetch Records or Data
Query records with selected dimension member IDs:
```bash
# Python
from statscepal import CepalStatClient, DataExtractor

client = CepalStatClient()
extractor = DataExtractor(client)
df = extractor.get_dataframe(4788, members=[224, 29190])  # Chile, 2020
```
Or via HTTP:
```bash
GET https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/{indicator_id}/records?members={member_ids}&format=json
```
```

- [ ] **Step 3: Verify skill structure**

Check that `.agents/skills/cepalstat-api/SKILL.md` has valid YAML frontmatter, `name` without forbidden characters, and `description` in third person starting with "Use when...".

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/cepalstat-api/
git commit -m "feat: add cepalstat-api Antigravity skill and dimension reference"
```

---

### Task 8: Subagent Definition (`cepalstat_analyst`)

**Files:**
- Create: `.agents/subagents/cepalstat-analyst.md`
- Register runtime subagent using `define_subagent` tool

**Interfaces:**
- Consumes: `statscepal` CLI and Python client
- Produces: Specialized autonomous research agent for ECLAC / CEPAL statistics

- [ ] **Step 1: Create agent profile documentation**

File: `.agents/subagents/cepalstat-analyst.md`
```markdown
# CEPALSTAT Analyst Subagent

**Name:** `cepalstat_analyst`  
**Role:** Latin America & Caribbean Statistical Analyst  
**Capabilities:**
- Searches CEPALSTAT thematic trees for indicators.
- Resolves geographical (ISO3, ECLAC country codes) and temporal dimensions.
- Downloads data directly via `statscepal` client and extracts tabular insights.
- Generates comparative regional analyses (e.g., poverty, GDP growth, inflation, demographic trends).
```

- [ ] **Step 2: Register agent via `define_subagent`**

Call `define_subagent` with name `cepalstat_analyst`, write tools enabled, and detailed prompt.

- [ ] **Step 3: Commit**

```bash
git add .agents/subagents/
git commit -m "feat: add cepalstat-analyst subagent definition"
```

---

### Task 9: End-to-End Verification and Live Smoke Test

**Files:**
- Test: `tests/test_live_smoke.py`

**Interfaces:**
- Consumes: Live `https://api-cepalstat.cepal.org` API
- Produces: Verified end-to-end integration

- [ ] **Step 1: Write the live smoke test**

File: `tests/test_live_smoke.py`
```python
import pytest
from statscepal import CepalStatClient, ThematicTree, DimensionManager, DataExtractor


@pytest.mark.integration
def test_live_cepalstat_smoke():
    with CepalStatClient() as client:
        # 1. Thematic Tree
        tree = ThematicTree(client)
        results = tree.search("Población total")
        assert len(results) > 0

        # Indicator 4788 (Población total, según sexo)
        indicator_id = 4788

        # 2. Dimensions
        dim_mgr = DimensionManager(client)
        dims = dim_mgr.get_dimensions(indicator_id)
        assert len(dims) >= 2

        chile_id = dim_mgr.find_member_id(indicator_id, "País", "Chile")
        assert chile_id == 224

        # 3. Data Extraction
        extractor = DataExtractor(client, dim_mgr)
        df = extractor.get_dataframe(indicator_id, members=[chile_id, 29190])
        assert not df.empty
        assert "Chile" in df.to_string()
```

- [ ] **Step 2: Run all tests (unit + integration)**

Run: `uv run pytest -m "not integration"`
Run: `uv run pytest tests/test_live_smoke.py`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_live_smoke.py
git commit -m "test: add live integration smoke test for CEPALSTAT"
```
