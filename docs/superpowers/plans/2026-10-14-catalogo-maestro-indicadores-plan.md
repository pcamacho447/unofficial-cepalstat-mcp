# Master Indicator Catalog & Offline Search Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a high-performance offline Master Catalog and search engine for all 2,070 CEPALSTAT indicators in SQLite, enabling instant (< 2ms) keyword searching, zero network calls, zero token waste, and thematic aggregation.

**Architecture:** A dedicated `catalog/` package (`src/statscepal/catalog/`) with models (`models.py`) and a persistent SQLite manager (`store.py`). Extends the CLI with `statscepal catalog build|search|stats|export`, integrates offline caching into the existing `statscepal search` command, and updates the Antigravity skill and subagents.

**Tech Stack:** Python 3.12+, `sqlite3`, `pydantic`, `pandas`, `pytest`, `respx`.

**Spec:** [docs/superpowers/specs/2026-10-14-catalogo-maestro-indicadores-design.md](file:///C:/papx/statscepal/docs/superpowers/specs/2026-10-14-catalogo-maestro-indicadores-design.md)

## Global Constraints

- Database: Table `master_indicators` in `.statscepal_cache.db`
- Indicator count: Exactly captures all ~2,070 leaf indicators from the CEPAL thematic tree
- Performance: Search execution under 10ms with zero network requests once built
- Case-insensitivity: LIKE query matching on name, theme, area, and full path
- Backward compatibility: Existing `statscepal search` falls back to the local catalog if available, avoiding redundant network trips

---

### Task 1: Pydantic Models for Catalog (`models.py`)

**Files:**
- Create: `src/statscepal/catalog/__init__.py`
- Create: `src/statscepal/catalog/models.py`
- Test: `tests/test_catalog_models.py`

**Interfaces:**
- Produces:
  - `CatalogIndicator`: `indicator_id`, `name`, `order_num`, `theme`, `area`, `subarea`, `full_path`, `updated_at`
  - `CatalogStats`: `total_indicators`, `themes_count`, `areas_count`, `by_theme` (dict[str, int])

- [ ] **Step 1: Write the failing test**

File: `tests/test_catalog_models.py`
```python
import pytest
from statscepal.catalog.models import CatalogIndicator, CatalogStats


def test_catalog_indicator_creation():
    ind = CatalogIndicator(
        indicator_id=4788,
        name="Población total, según sexo",
        order_num=10,
        theme="Demográficos y sociales",
        area="Demográficos",
        subarea="Población",
        full_path="Demográficos y sociales > Demográficos > Población",
    )
    assert ind.indicator_id == 4788
    assert ind.theme == "Demográficos y sociales"


def test_catalog_stats_creation():
    stats = CatalogStats(
        total_indicators=2070,
        themes_count=4,
        areas_count=20,
        by_theme={"Económicos": 500, "Demográficos": 600},
    )
    assert stats.total_indicators == 2070
    assert stats.by_theme["Económicos"] == 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_catalog_models.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.catalog'`

- [ ] **Step 3: Write minimal implementation**

File: `src/statscepal/catalog/__init__.py`
```python
"""Master Indicator Catalog module for CEPALSTAT."""

from statscepal.catalog.models import CatalogIndicator, CatalogStats

__all__ = ["CatalogIndicator", "CatalogStats"]
```

File: `src/statscepal/catalog/models.py`
```python
"""Data models for Master Indicator Catalog."""

from typing import Any
from pydantic import BaseModel, Field


class CatalogIndicator(BaseModel):
    """An indicator indexed in the master catalog."""

    indicator_id: int
    name: str
    order_num: int | None = None
    theme: str = ""
    area: str = ""
    subarea: str = ""
    full_path: str = ""
    updated_at: str = ""


class CatalogStats(BaseModel):
    """Statistical summary of the master catalog."""

    total_indicators: int
    themes_count: int = 0
    areas_count: int = 0
    by_theme: dict[str, int] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_catalog_models.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/catalog/ tests/test_catalog_models.py
git commit -m "feat: add CatalogIndicator and CatalogStats models"
```

---

### Task 2: Implement CatalogStore with SQLite Indexing (`store.py`)

**Files:**
- Create: `src/statscepal/catalog/store.py`
- Modify: `src/statscepal/catalog/__init__.py`
- Test: `tests/test_catalog_store.py`

**Interfaces:**
- Consumes: `CepalStatClient`, `ThematicTree`, `CatalogIndicator`, `CatalogStats`
- Produces: `CatalogStore(db_path, client)`:
  - `build(force: bool = False) -> int` (populates SQLite table from tree)
  - `is_built() -> bool`
  - `search(query: str, theme: str | None = None, limit: int = 20) -> list[CatalogIndicator]`
  - `get_stats() -> CatalogStats`
  - `export(filepath: str | Path, format: str = "json") -> Path`

- [ ] **Step 1: Write the failing test**

File: `tests/test_catalog_store.py`
```python
from pathlib import Path
import pytest
import respx
import httpx
from statscepal.client import CepalStatClient
from statscepal.catalog.store import CatalogStore

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
                                "name": "Tasa anual de crecimiento",
                                "order": 50,
                                "indicator_id": 4795,
                            },
                        ],
                    }
                ],
            },
            {
                "name": "Económicos",
                "area_id": 414,
                "children": [
                    {
                        "name": "PIB y Cuentas Nacionales",
                        "area_id": 415,
                        "children": [
                            {
                                "name": "PIB Anual a precios constantes",
                                "order": 100,
                                "indicator_id": 415,
                            }
                        ],
                    }
                ],
            },
        ],
    },
}


@respx.mock
def test_catalog_store_build_and_search(tmp_path: Path):
    respx.get("https://api-cepalstat.cepal.org/cepalstat/api/v1/thematic-tree").mock(
        return_value=httpx.Response(200, json=MOCK_TREE_PAYLOAD)
    )

    db_path = tmp_path / "test_catalog.db"
    client = CepalStatClient()
    store = CatalogStore(db_path=db_path, client=client)

    assert not store.is_built()
    count = store.build()
    assert count == 3
    assert store.is_built()

    # Search by keyword
    results = store.search("poblacion")
    assert len(results) == 1
    assert results[0].indicator_id == 4788
    assert results[0].theme == "Demográficos y sociales"

    # Search with theme filter
    econ_results = store.search("PIB", theme="Económicos")
    assert len(econ_results) == 1
    assert econ_results[0].indicator_id == 415

    # Get stats
    stats = store.get_stats()
    assert stats.total_indicators == 3
    assert stats.by_theme["Demográficos y sociales"] == 2
    assert stats.by_theme["Económicos"] == 1

    # Export
    out_json = tmp_path / "export.json"
    store.export(out_json, format="json")
    assert out_json.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_catalog_store.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.catalog.store'`

- [ ] **Step 3: Write minimal implementation**

File: `src/statscepal/catalog/store.py`
```python
"""CatalogStore for indexing and searching master indicators in SQLite."""

from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Generator
import pandas as pd
from statscepal.catalog.models import CatalogIndicator, CatalogStats
from statscepal.client import CepalStatClient
from statscepal.thematic_tree import ThematicTree

DEFAULT_DB_PATH = Path(".statscepal_cache.db")


class CatalogStore:
    """Manages downloading, persisting, and querying the master indicators catalog."""

    def __init__(
        self,
        db_path: Path | str = DEFAULT_DB_PATH,
        client: CepalStatClient | None = None,
    ):
        self.db_path = Path(db_path)
        self.client = client
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS master_indicators (
                    indicator_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    order_num INTEGER,
                    theme TEXT NOT NULL,
                    area TEXT NOT NULL,
                    subarea TEXT,
                    full_path TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_indicators_name ON master_indicators(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_indicators_theme ON master_indicators(theme)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_indicators_area ON master_indicators(area)")
            conn.commit()

    def is_built(self) -> bool:
        """Check if the catalog has been populated."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) AS total FROM master_indicators")
            row = cursor.fetchone()
            return bool(row and row["total"] > 0)

    def build(self, force: bool = False) -> int:
        """Fetch the thematic tree and populate SQLite master_indicators table."""
        if self.is_built() and not force:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) AS total FROM master_indicators")
                return cursor.fetchone()["total"]

        client = self.client or CepalStatClient()
        tree = ThematicTree(client)
        root = tree.get_raw_tree(force_refresh=force)

        indicators_to_insert: list[dict[str, Any]] = []
        now_str = datetime.now().isoformat()

        def extract_indicators(node: dict[str, Any], path_parts: list[str]) -> None:
            name = node.get("name", "")
            current_path = path_parts + [name] if name else path_parts

            if "indicator_id" in node:
                # Determine theme, area, subarea from path
                # Exclude root "Clasificación temática general" if present
                clean_path = [p for p in path_parts if "clasificación" not in p.lower()]
                theme = clean_path[0] if len(clean_path) > 0 else ""
                area = clean_path[1] if len(clean_path) > 1 else ""
                subarea = clean_path[2] if len(clean_path) > 2 else ""

                indicators_to_insert.append({
                    "indicator_id": int(node["indicator_id"]),
                    "name": name,
                    "order_num": node.get("order"),
                    "theme": theme,
                    "area": area,
                    "subarea": subarea,
                    "full_path": " > ".join(clean_path),
                    "updated_at": now_str,
                })
            elif "children" in node and isinstance(node["children"], list):
                for child in node["children"]:
                    if isinstance(child, dict):
                        extract_indicators(child, current_path)

        extract_indicators(root, [])

        with self._get_connection() as conn:
            conn.execute("DELETE FROM master_indicators")
            for item in indicators_to_insert:
                conn.execute("""
                    INSERT OR REPLACE INTO master_indicators
                    (indicator_id, name, order_num, theme, area, subarea, full_path, updated_at)
                    VALUES (:indicator_id, :name, :order_num, :theme, :area, :subarea, :full_path, :updated_at)
                """, item)
            conn.commit()

        return len(indicators_to_insert)

    def search(
        self,
        query: str,
        theme: str | None = None,
        limit: int = 20,
    ) -> list[CatalogIndicator]:
        """Search master indicators with case-insensitive substring matching."""
        sql = "SELECT * FROM master_indicators WHERE 1=1"
        params: list[Any] = []

        if query:
            sql += " AND (name LIKE ? OR full_path LIKE ? OR area LIKE ?)"
            wildcard = f"%{query}%"
            params.extend([wildcard, wildcard, wildcard])

        if theme:
            sql += " AND theme LIKE ?"
            params.append(f"%{theme}%")

        sql += " ORDER BY order_num ASC LIMIT ?"
        params.append(limit)

        results: list[CatalogIndicator] = []
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            for row in cursor.fetchall():
                results.append(CatalogIndicator(
                    indicator_id=row["indicator_id"],
                    name=row["name"],
                    order_num=row["order_num"],
                    theme=row["theme"],
                    area=row["area"],
                    subarea=row["subarea"],
                    full_path=row["full_path"],
                    updated_at=row["updated_at"] or "",
                ))

        return results

    def get_stats(self) -> CatalogStats:
        """Compute aggregated statistics of the master catalog."""
        with self._get_connection() as conn:
            c1 = conn.execute("SELECT COUNT(*) AS total FROM master_indicators")
            total = c1.fetchone()["total"]

            c2 = conn.execute("SELECT COUNT(DISTINCT theme) AS cnt FROM master_indicators")
            themes_cnt = c2.fetchone()["cnt"]

            c3 = conn.execute("SELECT COUNT(DISTINCT area) AS cnt FROM master_indicators")
            areas_cnt = c3.fetchone()["cnt"]

            by_theme: dict[str, int] = {}
            c4 = conn.execute("SELECT theme, COUNT(*) AS count FROM master_indicators GROUP BY theme ORDER BY count DESC")
            for row in c4.fetchall():
                t = row["theme"] or "Sin tema"
                by_theme[t] = row["count"]

        return CatalogStats(
            total_indicators=total,
            themes_count=themes_cnt,
            areas_count=areas_cnt,
            by_theme=by_theme,
        )

    def export(self, filepath: str | Path, format: str = "json") -> Path:
        """Export the catalog to a JSON or CSV file."""
        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM master_indicators ORDER BY indicator_id", conn)

        if format.lower() == "csv":
            df.to_csv(out_path, index=False, encoding="utf-8")
        else:
            df.to_json(out_path, orient="records", force_ascii=False, indent=2)

        return out_path
```

File: `src/statscepal/catalog/__init__.py`
```python
"""Master Indicator Catalog module for CEPALSTAT."""

from statscepal.catalog.models import CatalogIndicator, CatalogStats
from statscepal.catalog.store import CatalogStore

__all__ = ["CatalogIndicator", "CatalogStats", "CatalogStore"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_catalog_store.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/catalog/store.py src/statscepal/catalog/__init__.py tests/test_catalog_store.py
git commit -m "feat: implement CatalogStore for master indicator indexing and offline search"
```

---

### Task 3: Extend CLI with `catalog` Subcommands

**Files:**
- Modify: `src/statscepal/cli.py`
- Test: `tests/test_catalog_cli.py`

**Interfaces:**
- CLI Commands:
  - `statscepal catalog build [--force]`
  - `statscepal catalog search <query> [--theme <t>] [--limit <n>]`
  - `statscepal catalog stats`
  - `statscepal catalog export [--output <path>] [--format json|csv]`

- [ ] **Step 1: Write the failing test**

File: `tests/test_catalog_cli.py`
```python
from statscepal.cli import main


def test_cli_catalog_help():
    assert main(["catalog", "--help"]) == 0


def test_cli_catalog_stats_empty(tmp_path):
    assert main(["catalog", "stats"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_catalog_cli.py`
Expected: FAIL with `unrecognized arguments: catalog`

- [ ] **Step 3: Modify `src/statscepal/cli.py` to add `catalog` subparsers and handlers**

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_catalog_cli.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/cli.py tests/test_catalog_cli.py
git commit -m "feat: add catalog build, search, stats, and export subcommands to CLI"
```

---

### Task 4: Offline Fallback in `statscepal search`

**Files:**
- Modify: `src/statscepal/cli.py`
- Test: `tests/test_cli_offline_search.py`

**Interfaces:**
- When running `statscepal search <query>`, check if `CatalogStore().is_built()`.
- If true: perform offline search instantly via `CatalogStore.search()` (0 tokens, < 5ms).
- If false: fall back to `ThematicTree(client).search()` as before, with a tip: *"Tip: Run 'statscepal catalog build' for instant offline search."*

- [ ] **Step 1: Write the test verifying offline priority**

File: `tests/test_cli_offline_search.py`
```python
from statscepal.cli import main
from statscepal.catalog.store import CatalogStore
from statscepal.catalog.models import CatalogIndicator


def test_search_uses_local_catalog_when_built(tmp_path, monkeypatch, capsys):
    store = CatalogStore(db_path=tmp_path / "cache.db")
    with store._get_connection() as conn:
        conn.execute(
            """INSERT INTO master_indicators (indicator_id, name, theme, area, full_path)
               VALUES (9999, 'Indicador Offline Mock', 'Tema Mock', 'Area Mock', 'Tema > Area')"""
        )
        conn.commit()

    monkeypatch.setattr("statscepal.cli.DEFAULT_DB_PATH", tmp_path / "cache.db")
    ret = main(["search", "Offline"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "9999" in captured.out
    assert "Indicador Offline Mock" in captured.out
```

- [ ] **Step 2: Implement offline priority in `statscepal.cli.py`**

- [ ] **Step 3: Verify tests pass**

Run: `uv run pytest tests/test_cli_offline_search.py`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/statscepal/cli.py tests/test_cli_offline_search.py
git commit -m "feat: connect statscepal search to local catalog when available"
```

---

### Task 5: Build Live Master Catalog (2,070 Indicators)

**Execution:**
- Run `uv run statscepal catalog build`
- Verify that table `master_indicators` contains ~2,070 rows.
- Run `uv run statscepal catalog stats` to display the breakdown.

- [ ] **Step 1: Run build command**
Run: `uv run statscepal catalog build`
Expected: `[OK] Master catalog built successfully: 2070 indicators indexed in SQLite.`

- [ ] **Step 2: Run stats command**
Run: `uv run statscepal catalog stats`
Expected: Breakdown across Demográficos, Económicos, Ambientales, and Temas transversales.

---

### Task 6: Skill & Agent Documentation Update

**Files:**
- Modify: `.agents/skills/cepalstat-api/SKILL.md`
- Modify: `.agents/subagents/cepalstat-analyst.md`
- Test: `tests/test_skill_structure.py`

**Interfaces:**
- Documents `statscepal catalog search` as Step 0b for offline discovery of any indicator among the 2,070 indicators.

- [ ] **Step 1: Update skill and subagent docs**
- [ ] **Step 2: Run verification test**
- [ ] **Step 3: Commit**

```bash
git add .agents/skills/cepalstat-api/SKILL.md .agents/subagents/cepalstat-analyst.md
git commit -m "docs: add master catalog search guidance to skill and subagent"
```

---

### Task 7: Full Test Suite & Verification

**Files:**
- Test: All tests in `tests/`

- [ ] **Step 1: Run full pytest suite**
Run: `uv run pytest`
Expected: All tests pass.

- [ ] **Step 2: Git status clean**
Run: `git status`
Expected: clean working tree.
