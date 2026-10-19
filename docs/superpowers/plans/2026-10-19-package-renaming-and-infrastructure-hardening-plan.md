# Package Renaming and Infrastructure Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the codebase from the internal prototype name `statscepal` to the production-ready, trademark-safe open-source package `unofficial-cepalstat-mcp` (Python module `unofficial_cepalstat_mcp`), adding cross-platform cache resolution (`platformdirs`), robust PyPI packaging metadata, and standard open-source governance documents (`LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`).

**Architecture:**
1. Migrate the Python import package from `src/statscepal` to `src/unofficial_cepalstat_mcp`, updating all 404+ import occurrences and tests while preserving 100% test pass rates and zero performance regressions.
2. Introduce a robust, hierarchical cache location manager (`platformdirs` + `UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH` / `STATSCEPAL_CACHE_PATH` + local repo fallback) so the MCP server and CLI function seamlessly when executed from any working directory (`CWD`) via `pip` or `uvx`.
3. Configure `pyproject.toml` with dual CLI entrypoints (`unofficial-cepalstat-mcp` and `cepalstat-mcp`), explicit MIT license, rich metadata, and strict build targets.
4. Establish legal and community artifacts, including explicit disclaimers clarifying no official affiliation with the United Nations Economic Commission for Latin America and the Caribbean (UN ECLAC / CEPAL).

**Tech Stack:** Python 3.10+, Hatchling, platformdirs, httpx, pydantic v2, pandas, pytest, respx.

**Spec:** `docs/superpowers/plans/2026-10-19-package-renaming-and-infrastructure-hardening-plan.md`

## Global Constraints

- Python 3.10+ modern typing syntax (`X | None`, `list[str]`, etc.).
- All 381+ non-integration tests must strictly pass after every task.
- False Substitution Rate (FSR) must strictly remain 0.00% across the 200-question benchmark.
- Adversarial benchmark (40 cases) must strictly remain 100.0% passing (40/40) with 0.00% FSR.
- Strict offline hermeticity: test suites must NEVER perform live network calls to CEPALSTAT.
- Local resolution latency over SQLite and in-memory thesaurus must maintain p50 < 0.5 ms.
- Safe UTF-8 encoding for Windows and POSIX console environments.

---

### Task 1: Package Directory and Import Namespace Migration

**Files:**
- Move: `src/statscepal` -> `src/unofficial_cepalstat_mcp`
- Modify: `pyproject.toml`
- Modify: All files in `tests/` referencing `statscepal`
- Modify: All internal files in `src/unofficial_cepalstat_mcp/` referencing `statscepal`

**Interfaces:**
- Consumes: Existing library code and test suites.
- Produces: Importable package `unofficial_cepalstat_mcp`.

- [ ] **Step 1: Move directory `src/statscepal` to `src/unofficial_cepalstat_mcp`**

Execute directory move:
```powershell
Move-Item -Path src/statscepal -Destination src/unofficial_cepalstat_mcp
```

- [ ] **Step 2: Update `pyproject.toml` package declaration**

Update wheel build target and script entrypoints in `pyproject.toml`:
```toml
[project]
name = "unofficial-cepalstat-mcp"
version = "0.1.0"
description = "Unofficial Python client, semantic resolution engine, and MCP server for UN CEPALSTAT Open Data API"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.7.0",
    "pandas>=2.2.0",
    "pyyaml>=6.0.1",
    "matplotlib>=3.8.0",
    "statsmodels>=0.14.0",
    "plotly>=5.20.0",
    "platformdirs>=4.2.0",
]

[project.scripts]
unofficial-cepalstat-mcp = "unofficial_cepalstat_mcp.cli:main"
cepalstat-mcp = "unofficial_cepalstat_mcp.cli:main"
statscepal = "unofficial_cepalstat_mcp.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/unofficial_cepalstat_mcp"]
```

- [ ] **Step 3: Refactor all import references from `statscepal` to `unofficial_cepalstat_mcp`**

Replace:
- `from statscepal` -> `from unofficial_cepalstat_mcp`
- `import statscepal` -> `import unofficial_cepalstat_mcp`
across all `.py` files in `src/` and `tests/`.

- [ ] **Step 4: Run tests to verify import migration passes cleanly**

Run: `uv run pytest -m "not integration"`
Expected: 381 passed, 3 deselected.

- [ ] **Step 5: Commit migration**

```bash
git add src/ pyproject.toml tests/
git commit -m "refactor(core): migrate package namespace from statscepal to unofficial_cepalstat_mcp"
```

---

### Task 2: Multi-Platform Cache Resolution & Auto-Bootstrap

**Files:**
- Create: `src/unofficial_cepalstat_mcp/config.py`
- Modify: `src/unofficial_cepalstat_mcp/catalog/store.py`
- Modify: `src/unofficial_cepalstat_mcp/bitacora/store.py`
- Test: `tests/test_config_cache_resolution.py`

**Interfaces:**
- Consumes: `platformdirs.user_cache_dir`
- Produces: `get_cache_db_path() -> Path`

- [ ] **Step 1: Write failing test for hierarchical cache path resolution**

Create `tests/test_config_cache_resolution.py`:
```python
import os
from pathlib import Path
import pytest
from unofficial_cepalstat_mcp.config import get_cache_db_path

def test_cache_db_path_respects_env_var(monkeypatch, tmp_path):
    custom_db = tmp_path / "custom.db"
    monkeypatch.setenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", str(custom_db))
    assert get_cache_db_path() == custom_db

def test_cache_db_path_respects_legacy_env_var(monkeypatch, tmp_path):
    custom_db = tmp_path / "legacy.db"
    monkeypatch.delenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", raising=False)
    monkeypatch.setenv("STATSCEPAL_CACHE_PATH", str(custom_db))
    assert get_cache_db_path() == custom_db

def test_cache_db_path_falls_back_to_local_if_exists(monkeypatch, tmp_path):
    monkeypatch.delenv("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH", raising=False)
    monkeypatch.delenv("STATSCEPAL_CACHE_PATH", raising=False)
    # When local .statscepal_cache.db exists in CWD
    local_db = Path(".statscepal_cache.db")
    if local_db.exists():
        assert get_cache_db_path() == local_db
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config_cache_resolution.py -v`
Expected: FAIL (ModuleNotFoundError / ImportError).

- [ ] **Step 3: Implement `src/unofficial_cepalstat_mcp/config.py`**

```python
"""Configuration and path management for unofficial-cepalstat-mcp."""

import os
from pathlib import Path
import platformdirs

APP_NAME = "unofficial_cepalstat_mcp"
DEFAULT_DB_FILENAME = ".statscepal_cache.db"


def get_cache_db_path() -> Path:
    """Resolve database path in priority order:
    1. UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH environment variable.
    2. STATSCEPAL_CACHE_PATH environment variable (backward-compat).
    3. Local .statscepal_cache.db in current working directory (if present).
    4. OS user cache directory via platformdirs.
    """
    env_path = os.environ.get("UNOFFICIAL_CEPALSTAT_MCP_CACHE_PATH") or os.environ.get("STATSCEPAL_CACHE_PATH")
    if env_path:
        return Path(env_path)

    local_db = Path(DEFAULT_DB_FILENAME)
    if local_db.exists():
        return local_db

    cache_dir = Path(platformdirs.user_cache_dir(APP_NAME))
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / DEFAULT_DB_FILENAME
    except OSError:
        # Fallback to local path if user cache directory is unwritable
        return local_db
```

- [ ] **Step 4: Update `catalog/store.py` and `bitacora/store.py` to use `get_cache_db_path()`**

In `src/unofficial_cepalstat_mcp/catalog/store.py`:
```python
from unofficial_cepalstat_mcp.config import get_cache_db_path

class CatalogStore:
    def __init__(
        self,
        db_path: Path | str | None = None,
        client: CepalStatClient | None = None,
    ):
        self.db_path = Path(db_path) if db_path is not None else get_cache_db_path()
        self.client = client
        if self.db_path.parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
```
Apply equivalent update to `src/unofficial_cepalstat_mcp/bitacora/store.py`.

- [ ] **Step 5: Run tests to verify all tests pass**

Run: `uv run pytest tests/test_config_cache_resolution.py tests/test_catalog_store.py tests/test_bitacora_store.py -v`
Expected: PASS.
Run: `uv run pytest -m "not integration"`
Expected: 382+ passed.

- [ ] **Step 6: Commit cache resolution**

```bash
git add src/unofficial_cepalstat_mcp/config.py src/unofficial_cepalstat_mcp/catalog/store.py src/unofficial_cepalstat_mcp/bitacora/store.py tests/test_config_cache_resolution.py
git commit -m "feat(config): add platformdirs cache resolution and environment path overrides"
```

---

### Task 3: PyPI Packaging Metadata & CLI Entrypoints

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_packaging_metadata.py`

**Interfaces:**
- Consumes: `pyproject.toml`
- Produces: Valid metadata and script aliases.

- [ ] **Step 1: Write test verifying packaging metadata**

Create `tests/test_packaging_metadata.py`:
```python
import tomllib
from pathlib import Path

def test_pyproject_metadata_is_complete():
    pyproject_path = Path("pyproject.toml")
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    
    project = data["project"]
    assert project["name"] == "unofficial-cepalstat-mcp"
    assert "unofficial-cepalstat-mcp" in project["scripts"]
    assert "cepalstat-mcp" in project["scripts"]
    assert "license" in project or "classifiers" in project
    assert "urls" in project
```

- [ ] **Step 2: Run test to verify failure or missing fields**

Run: `uv run pytest tests/test_packaging_metadata.py -v`

- [ ] **Step 3: Enrich `pyproject.toml`**

Add authors, license, classifiers, keywords, and URLs:
```toml
[project]
name = "unofficial-cepalstat-mcp"
version = "0.1.0"
description = "Unofficial Python client, semantic resolution engine, and MCP server for UN CEPALSTAT Open Data API"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [
    { name = "Patricio Camacho" }
]
keywords = [
    "cepal",
    "cepalstat",
    "eclac",
    "mcp",
    "model-context-protocol",
    "latin-america",
    "economics",
    "statistics",
    "semantic-search"
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Information Analysis",
]
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.7.0",
    "pandas>=2.2.0",
    "pyyaml>=6.0.1",
    "matplotlib>=3.8.0",
    "statsmodels>=0.14.0",
    "plotly>=5.20.0",
    "platformdirs>=4.2.0",
]

[project.urls]
Homepage = "https://github.com/pcamacho447/unofficial-cepalstat-mcp"
Repository = "https://github.com/pcamacho447/unofficial-cepalstat-mcp"
Issues = "https://github.com/pcamacho447/unofficial-cepalstat-mcp/issues"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_packaging_metadata.py -v`
Expected: PASS.

- [ ] **Step 5: Commit packaging metadata**

```bash
git add pyproject.toml tests/test_packaging_metadata.py
git commit -m "chore(packaging): complete PyPI metadata, licenses, classifiers, and script aliases"
```

---

### Task 4: Open Source Governance, Legal Disclaimers & Cleanliness

**Files:**
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`
- Delete: `statscepal.db` (orphan 0-byte file)
- Modify: `README.md` (add disclaimer, update command instructions)

**Interfaces:**
- Produces: Standard community and legal files.

- [ ] **Step 1: Create `LICENSE` (MIT with ECLAC / UN Non-Affiliation Disclaimer)**

Create `LICENSE`:
```text
MIT License

Copyright (c) 2026 Patricio Camacho

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---
DISCLAIMER: This project is an independent open-source tool and is NOT an
official product of, sponsored by, or affiliated with the United Nations
Economic Commission for Latin America and the Caribbean (UN ECLAC / CEPAL).
All data provided through this tool is sourced from the public UN CEPALSTAT
Open Data API.
```

- [ ] **Step 2: Create `CHANGELOG.md`**

Create `CHANGELOG.md` documenting v0.1.0 release highlights:
- Semantic Resolution Engine with 4-stage pipeline.
- 0.00% False Substitution Rate across 200 benchmark questions.
- 40/40 Adversarial Benchmark coverage.
- Unconsumed Semantic Tokens Guard preventing category distortion.
- Decoupling Analyzer and Bitacora Anti-Bias System.

- [ ] **Step 3: Create `CONTRIBUTING.md`**

Create `CONTRIBUTING.md` with:
- Code of Conduct / Development instructions.
- Strict Testing Protocol: `uv run pytest -m "not integration"`.
- Invariant: Zero tolerance for regressions on False Substitution Rate (0.00% FSR required).

- [ ] **Step 4: Remove orphan file `statscepal.db` and update `README.md`**

Execute:
```powershell
Remove-Item statscepal.db -ErrorAction SilentlyContinue
```
Update `README.md` to display package name `unofficial-cepalstat-mcp`, import `unofficial_cepalstat_mcp`, and the official disclaimer banner.

- [ ] **Step 5: Commit governance files**

```bash
git add LICENSE CONTRIBUTING.md CHANGELOG.md README.md
git rm statscepal.db
git commit -m "docs(governance): add LICENSE with non-affiliation disclaimer, CONTRIBUTING, and CHANGELOG"
```

---

### Task 5: End-to-End Regression & Benchmark Verification

**Files:**
- Execute verification across whole repo.

**Interfaces:**
- Consumes: Full test and benchmark suites.
- Produces: Verified green pass report.

- [ ] **Step 1: Execute full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: All tests pass (383+ tests, 0 failures).

- [ ] **Step 2: Execute 40-question Adversarial Benchmark**

Run: `uv run pytest tests/test_adversarial_benchmark_40.py -v`
Expected: 41 passed, 0.00% False Substitution Rate.

- [ ] **Step 3: Execute 200-question Benchmark Suite**

Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`
Expected: 11/11 passed, 100.0% Top-1 Accuracy, 0.00% False Substitution Rate.

- [ ] **Step 4: Commit any final test cleanups and push to remote master**

```bash
git push origin master
```
