# Bitácoras, Anti-Bias & Token Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a hybrid Bitácora (Codebook/Recipe) engine and automated Anti-Bias Data Quality Validator in `statscepal` that eliminates hallucinations, guarantees methodological rigor, and reduces LLM token consumption by 80-90% for economic/demographic analytics.

**Architecture:** A dual-backend Bitácora module (`src/statscepal/bitacora/`) containing typed Pydantic models (`models.py`), a statistical anti-bias auditor (`validator.py`), and a Markdown/YAML + SQLite storage manager (`store.py`). Extends the `statscepal` CLI with `bitacora` subcommands, seeds standard Chile recipes, and integrates the "Bitácora First" protocol into the Antigravity skill and subagent.

**Tech Stack:** Python 3.12+, `pandas`, `pydantic`, `sqlite3` (built-in), `pyyaml`, `pytest`, `respx`.

**Spec:** [docs/superpowers/specs/2026-10-14-bitacoras-antibias-design.md](file:///C:/papx/statscepal/docs/superpowers/specs/2026-10-14-bitacoras-antibias-design.md)

## Global Constraints

- Storage: Markdown files with YAML frontmatter in `bitacoras/` + local SQLite index in `.statscepal_cache.db`
- Anti-Bias: Mandatory unit of measurement, scale factor check, temporal gap detection, null ratio check, and projection cutoff flags
- Token Optimization: Local lookup takes 0 network calls and produces compact recipe cards (< 200 tokens)
- Python Dependencies: Add `pyyaml>=6.0.0` to `pyproject.toml`
- Test Quality: 100% mocked offline unit tests + integration tests

---

### Task 1: Add Dependencies and Pydantic Models for Bitácora

**Files:**
- Modify: `pyproject.toml`
- Create: `src/statscepal/bitacora/__init__.py`
- Create: `src/statscepal/bitacora/models.py`
- Test: `tests/test_bitacora_models.py`

**Interfaces:**
- Consumes: `pydantic`
- Produces:
  - `DataQualityReport`: `total_records`, `null_count`, `null_ratio`, `has_gaps`, `min_year`, `max_year`, `min_value`, `max_value`
  - `AntiBiasChecklist`: `unit_verified`, `scale_factor_note`, `is_projection`, `base_year_split`, `warnings`
  - `BitacoraRecipe`: `id`, `indicator_id`, `indicator_name`, `country`, `country_iso3`, `country_member_id`, `theme`, `unit`, `member_ids`, `python_code`, `status`, `date_certified`, `tags`, `quality_report`, `antibias`

- [ ] **Step 1: Write the failing test**

File: `tests/test_bitacora_models.py`
```python
import pytest
from statscepal.bitacora.models import BitacoraRecipe, DataQualityReport, AntiBiasChecklist


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
    assert recipe.country == "Chile"
    assert recipe.status == "certified"
    assert recipe.quality_report.null_count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_bitacora_models.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.bitacora'`

- [ ] **Step 3: Write minimal implementation**

File: `pyproject.toml` (Add `pyyaml>=6.0.0` under dependencies)
```toml
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.7.0",
    "pandas>=2.2.0",
    "pyyaml>=6.0.1",
]
```

File: `src/statscepal/bitacora/__init__.py`
```python
"""Bitácora module for verified recipes, anti-bias validation, and token optimization."""

from statscepal.bitacora.models import BitacoraRecipe, DataQualityReport, AntiBiasChecklist

__all__ = ["BitacoraRecipe", "DataQualityReport", "AntiBiasChecklist"]
```

File: `src/statscepal/bitacora/models.py`
```python
"""Pydantic data models for Bitácora recipes and anti-bias auditing."""

from typing import Any
from pydantic import BaseModel, Field


class DataQualityReport(BaseModel):
    """Statistical quality summary of the downloaded dataset."""

    total_records: int
    null_count: int = 0
    null_ratio: float = 0.0
    has_gaps: bool = False
    min_year: int | None = None
    max_year: int | None = None
    min_value: float | None = None
    max_value: float | None = None


class AntiBiasChecklist(BaseModel):
    """Methodological anti-bias checklist and warnings."""

    unit_verified: bool = True
    scale_factor_note: str = ""
    is_projection: bool = False
    base_year_split: int | None = None
    warnings: list[str] = Field(default_factory=list)


class BitacoraRecipe(BaseModel):
    """A verified, reusable query recipe in the Bitácora."""

    id: str
    indicator_id: int
    indicator_name: str
    country: str
    country_iso3: str = ""
    country_member_id: int | None = None
    theme: str = ""
    unit: str = ""
    member_ids: list[int] = Field(default_factory=list)
    python_code: str = ""
    status: str = "certified"  # certified | draft
    date_certified: str = ""
    tags: list[str] = Field(default_factory=list)
    quality_report: DataQualityReport | None = None
    antibias: AntiBiasChecklist | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv sync && uv run pytest tests/test_bitacora_models.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/statscepal/bitacora/ tests/test_bitacora_models.py
git commit -m "feat: add BitacoraRecipe, AntiBiasChecklist, and DataQualityReport models"
```

---

### Task 2: Implement Anti-Bias and Data Quality Validator (`AntiBiasValidator`)

**Files:**
- Create: `src/statscepal/bitacora/validator.py`
- Modify: `src/statscepal/bitacora/__init__.py`
- Test: `tests/test_validator.py`

**Interfaces:**
- Consumes: `pandas`, `DataQualityReport`, `AntiBiasChecklist`
- Produces: `AntiBiasValidator.audit(df, metadata) -> tuple[DataQualityReport, AntiBiasChecklist]`

- [ ] **Step 1: Write the failing test**

File: `tests/test_validator.py`
```python
import pandas as pd
import pytest
from statscepal.bitacora.validator import AntiBiasValidator


def test_validator_with_clean_data():
    df = pd.DataFrame({
        "value": [100.0, 105.0, 110.0],
        "Años__ESTANDAR": ["2018", "2019", "2020"],
    })
    meta = {
        "unit": "Miles de personas",
        "data_features": "Estimaciones 1950-2021 y proyecciones 2022-2100",
        "comments": "El año base de las proyecciones es 2021",
    }

    quality, antibias = AntiBiasValidator.audit(df, meta, year_column="Años__ESTANDAR")
    assert quality.total_records == 3
    assert quality.null_count == 0
    assert quality.has_gaps is False
    assert quality.min_year == 2018
    assert quality.max_year == 2020
    assert antibias.unit_verified is True
    assert "Miles de personas" in antibias.scale_factor_note
    assert antibias.base_year_split == 2021


def test_validator_detects_gaps_and_nulls():
    df = pd.DataFrame({
        "value": [10.0, None, 15.0],
        "Años__ESTANDAR": ["2015", "2016", "2018"],  # Missing 2017 -> Gap!
    })
    meta = {"unit": "Porcentaje del PIB"}

    quality, antibias = AntiBiasValidator.audit(df, meta, year_column="Años__ESTANDAR")
    assert quality.total_records == 3
    assert quality.null_count == 1
    assert quality.has_gaps is True
    assert any("faltantes" in w.lower() for w in antibias.warnings)
    assert any("discontinuidad" in w.lower() or "gap" in w.lower() for w in antibias.warnings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validator.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.bitacora.validator'`

- [ ] **Step 3: Write minimal implementation**

File: `src/statscepal/bitacora/validator.py`
```python
"""Statistical Anti-Bias and Data Quality Validator."""

import re
from typing import Any
import pandas as pd
from statscepal.bitacora.models import DataQualityReport, AntiBiasChecklist


class AntiBiasValidator:
    """Validates datasets against common statistical biases, temporal gaps, and metadata integrity."""

    @classmethod
    def audit(
        cls,
        df: pd.DataFrame,
        metadata: dict[str, Any] | None = None,
        year_column: str = "Años__ESTANDAR",
        value_column: str = "value",
    ) -> tuple[DataQualityReport, AntiBiasChecklist]:
        """Perform a statistical quality audit and generate an anti-bias checklist."""
        meta = metadata or {}
        warnings: list[str] = []

        total_records = len(df)
        if total_records == 0:
            return (
                DataQualityReport(total_records=0),
                AntiBiasChecklist(unit_verified=False, warnings=["DataFrame está vacío."]),
            )

        # 1. Null values check
        null_count = int(df[value_column].isna().sum()) if value_column in df.columns else 0
        null_ratio = float(null_count / total_records) if total_records > 0 else 0.0
        if null_count > 0:
            warnings.append(
                f"Se detectaron {null_count} valores nulos/faltantes ({null_ratio:.1%})."
            )

        # 2. Values statistics
        min_val = None
        max_val = None
        if value_column in df.columns:
            valid_vals = pd.to_numeric(df[value_column], errors="coerce").dropna()
            if not valid_vals.empty:
                min_val = float(valid_vals.min())
                max_val = float(valid_vals.max())

        # 3. Temporal gap analysis
        min_year = None
        max_year = None
        has_gaps = False

        # Attempt to find the year column dynamically if needed
        actual_year_col = None
        for col in [year_column, "year", "Años", "año", "Año"]:
            if col in df.columns:
                actual_year_col = col
                break

        if actual_year_col:
            years_series = pd.to_numeric(df[actual_year_col], errors="coerce").dropna().astype(int)
            if not years_series.empty:
                unique_years = sorted(years_series.unique())
                min_year = int(unique_years[0])
                max_year = int(unique_years[-1])
                expected_years = set(range(min_year, max_year + 1))
                if set(unique_years) != expected_years:
                    has_gaps = True
                    missing_years = sorted(expected_years - set(unique_years))
                    warnings.append(
                        f"Discontinuidad temporal detectada. Años faltantes en la serie: {missing_years[:5]}..."
                    )

        # 4. Scale factor and unit verification
        unit = meta.get("unit", "")
        scale_note = f"Unidad oficial: {unit}" if unit else "Unidad no especificada en metadatos."
        if not unit:
            warnings.append("Alerta de sesgo: La unidad de medida oficial no está definida.")
        elif any(k in unit.lower() for k in ["miles de", "millones", "porcentaje", "índice"]):
            scale_note += " (Atención al factor de escala al interpretar o modelar)."

        # 5. Projection cutoff detection
        base_year_split = None
        is_projection = False
        text_context = " ".join([
            meta.get("data_features", ""),
            meta.get("comments", ""),
            meta.get("calculation_methodology", ""),
        ])
        match_base = re.search(r"año base.*?(\d{4})", text_context, re.IGNORECASE)
        if match_base:
            base_year_split = int(match_base.group(1))
            if max_year and max_year > base_year_split:
                is_projection = True
                warnings.append(
                    f"Advertencia metodológica: Los datos posteriores al año base {base_year_split} son proyecciones."
                )

        quality = DataQualityReport(
            total_records=total_records,
            null_count=null_count,
            null_ratio=null_ratio,
            has_gaps=has_gaps,
            min_year=min_year,
            max_year=max_year,
            min_value=min_val,
            max_value=max_val,
        )

        antibias = AntiBiasChecklist(
            unit_verified=bool(unit),
            scale_factor_note=scale_note,
            is_projection=is_projection,
            base_year_split=base_year_split,
            warnings=warnings,
        )

        return quality, antibias
```

File: `src/statscepal/bitacora/__init__.py`
```python
"""Bitácora module for verified recipes, anti-bias validation, and token optimization."""

from statscepal.bitacora.models import BitacoraRecipe, DataQualityReport, AntiBiasChecklist
from statscepal.bitacora.validator import AntiBiasValidator

__all__ = [
    "BitacoraRecipe",
    "DataQualityReport",
    "AntiBiasChecklist",
    "AntiBiasValidator",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_validator.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/bitacora/validator.py src/statscepal/bitacora/__init__.py tests/test_validator.py
git commit -m "feat: implement AntiBiasValidator for statistical quality and scale checks"
```

---

### Task 3: Dual Store Manager (`BitacoraStore`) and SQLite Index

**Files:**
- Create: `src/statscepal/bitacora/store.py`
- Modify: `src/statscepal/bitacora/__init__.py`
- Test: `tests/test_bitacora_store.py`

**Interfaces:**
- Consumes: `BitacoraRecipe`, `pyyaml`, `sqlite3`
- Produces: `BitacoraStore(base_dir, db_path)`:
  - `save_recipe(recipe: BitacoraRecipe) -> Path`
  - `get_recipe(recipe_id: str) -> BitacoraRecipe | None`
  - `lookup(query: str, country: str | None = None, tag: str | None = None) -> list[BitacoraRecipe]`
  - `list_recipes() -> list[BitacoraRecipe]`
  - `sync() -> int`

- [ ] **Step 1: Write the failing test**

File: `tests/test_bitacora_store.py`
```python
from pathlib import Path
import pytest
from statscepal.bitacora.models import BitacoraRecipe, DataQualityReport, AntiBiasChecklist
from statscepal.bitacora.store import BitacoraStore


def test_bitacora_store_save_and_lookup(tmp_path: Path):
    bitacoras_dir = tmp_path / "bitacoras"
    db_file = tmp_path / ".cache.db"

    store = BitacoraStore(base_dir=bitacoras_dir, db_path=db_file)

    recipe = BitacoraRecipe(
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
        quality_report=DataQualityReport(total_records=1, null_count=0),
        antibias=AntiBiasChecklist(unit_verified=True, scale_factor_note="Miles de personas"),
    )

    filepath = store.save_recipe(recipe)
    assert filepath.exists()
    assert filepath.suffix == ".md"

    # Fast lookup from SQLite index
    results = store.lookup("poblacion", country="Chile")
    assert len(results) == 1
    assert results[0].id == "recipe-chl-4788-pob"
    assert results[0].country == "Chile"

    # Test sync re-indexing
    db_file.unlink()  # delete db
    store_reindex = BitacoraStore(base_dir=bitacoras_dir, db_path=db_file)
    count = store_reindex.sync()
    assert count == 1
    assert len(store_reindex.list_recipes()) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_bitacora_store.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscepal.bitacora.store'`

- [ ] **Step 3: Write minimal implementation**

File: `src/statscepal/bitacora/store.py`
```python
"""Dual Markdown and SQLite Storage Manager for Bitácoras."""

import json
from pathlib import Path
import sqlite3
from typing import Any
import yaml
from statscepal.bitacora.models import BitacoraRecipe, DataQualityReport, AntiBiasChecklist

DEFAULT_BITACORAS_DIR = Path("bitacoras")
DEFAULT_DB_PATH = Path(".statscepal_cache.db")


class BitacoraStore:
    """Manages saving, loading, indexing, and querying Bitácora recipes."""

    def __init__(
        self,
        base_dir: Path | str = DEFAULT_BITACORAS_DIR,
        db_path: Path | str = DEFAULT_DB_PATH,
    ):
        self.base_dir = Path(base_dir)
        self.db_path = Path(db_path)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id TEXT PRIMARY KEY,
                    indicator_id INTEGER,
                    indicator_name TEXT,
                    country TEXT,
                    country_iso3 TEXT,
                    theme TEXT,
                    unit TEXT,
                    status TEXT,
                    date_certified TEXT,
                    tags TEXT,
                    filepath TEXT,
                    full_json TEXT
                )
            """)
            conn.commit()

    def save_recipe(self, recipe: BitacoraRecipe) -> Path:
        """Save recipe as a Markdown file with YAML frontmatter and index it in SQLite."""
        country_slug = recipe.country.lower().replace(" ", "_") if recipe.country else "general"
        target_dir = self.base_dir / "paises" / country_slug
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{recipe.indicator_id}_{recipe.id}.md"
        filepath = target_dir / filename

        frontmatter_dict = recipe.model_dump()
        body_content = f"""---
{yaml.dump(frontmatter_dict, sort_keys=False, allow_unicode=True)}---

# Receta: {recipe.indicator_name} ({recipe.country})

## Alertas Anti-Sesgo y Calidad de Datos
- **Unidad**: {recipe.unit}
- **Nota de Escala**: {recipe.antibias.scale_factor_note if recipe.antibias else 'N/A'}
- **Proyección**: {'Sí (Post-' + str(recipe.antibias.base_year_split) + ')' if (recipe.antibias and recipe.antibias.is_projection) else 'No'}

## Código Reproducible en Python
```python
{recipe.python_code}
```
"""
        filepath.write_text(body_content, encoding="utf-8")

        # Index in SQLite
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO recipes
                (id, indicator_id, indicator_name, country, country_iso3, theme, unit, status, date_certified, tags, filepath, full_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    recipe.id,
                    recipe.indicator_id,
                    recipe.indicator_name,
                    recipe.country,
                    recipe.country_iso3,
                    recipe.theme,
                    recipe.unit,
                    recipe.status,
                    recipe.date_certified,
                    ",".join(recipe.tags),
                    str(filepath),
                    recipe.model_dump_json(),
                ),
            )
            conn.commit()

        return filepath

    def lookup(
        self,
        query: str,
        country: str | None = None,
        tag: str | None = None,
    ) -> list[BitacoraRecipe]:
        """Query indexed recipes using exact and partial filters."""
        sql = "SELECT full_json FROM recipes WHERE 1=1"
        params: list[Any] = []

        if query:
            sql += " AND (indicator_name LIKE ? OR theme LIKE ? OR tags LIKE ?)"
            wildcard = f"%{query}%"
            params.extend([wildcard, wildcard, wildcard])

        if country:
            sql += " AND (country LIKE ? OR country_iso3 LIKE ?)"
            params.extend([f"%{country}%", f"%{country}%"])

        if tag:
            sql += " AND tags LIKE ?"
            params.append(f"%{tag}%")

        recipes: list[BitacoraRecipe] = []
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            for row in cursor.fetchall():
                recipes.append(BitacoraRecipe.model_validate_json(row["full_json"]))

        return recipes

    def list_recipes(self) -> list[BitacoraRecipe]:
        """List all certified recipes currently stored."""
        return self.lookup(query="")

    def sync(self) -> int:
        """Scan all markdown files in base_dir and rebuild the SQLite index."""
        count = 0
        with self._get_connection() as conn:
            conn.execute("DELETE FROM recipes")
            for md_file in self.base_dir.rglob("*.md"):
                text = md_file.read_text(encoding="utf-8")
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    yaml_content = parts[1]
                    try:
                        data = yaml.safe_load(yaml_content)
                        recipe = BitacoraRecipe.model_validate(data)
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO recipes
                            (id, indicator_id, indicator_name, country, country_iso3, theme, unit, status, date_certified, tags, filepath, full_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                recipe.id,
                                recipe.indicator_id,
                                recipe.indicator_name,
                                recipe.country,
                                recipe.country_iso3,
                                recipe.theme,
                                recipe.unit,
                                recipe.status,
                                recipe.date_certified,
                                ",".join(recipe.tags),
                                str(md_file),
                                recipe.model_dump_json(),
                            ),
                        )
                        count += 1
                    except Exception:
                        continue
            conn.commit()
        return count
```

File: `src/statscepal/bitacora/__init__.py`
```python
"""Bitácora module for verified recipes, anti-bias validation, and token optimization."""

from statscepal.bitacora.models import BitacoraRecipe, DataQualityReport, AntiBiasChecklist
from statscepal.bitacora.validator import AntiBiasValidator
from statscepal.bitacora.store import BitacoraStore

__all__ = [
    "BitacoraRecipe",
    "DataQualityReport",
    "AntiBiasChecklist",
    "AntiBiasValidator",
    "BitacoraStore",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_bitacora_store.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/bitacora/store.py src/statscepal/bitacora/__init__.py tests/test_bitacora_store.py
git commit -m "feat: implement BitacoraStore for Markdown and SQLite index synchronization"
```

---

### Task 4: Extend CLI with `bitacora` Subcommands

**Files:**
- Modify: `src/statscepal/cli.py`
- Test: `tests/test_bitacora_cli.py`

**Interfaces:**
- Consumes: `BitacoraStore`, `AntiBiasValidator`, `DataExtractor`, `DimensionManager`
- Produces: CLI commands:
  - `statscepal bitacora lookup <query> [--country <c>]`
  - `statscepal bitacora add <indicator_id> --country <c> [--members M1,M2] [--tags t1,t2]`
  - `statscepal bitacora list`
  - `statscepal bitacora sync`

- [ ] **Step 1: Write the failing test**

File: `tests/test_bitacora_cli.py`
```python
from statscepal.cli import main


def test_cli_bitacora_help():
    assert main(["bitacora", "--help"]) == 0


def test_cli_bitacora_list_empty():
    assert main(["bitacora", "list"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_bitacora_cli.py`
Expected: FAIL with `unrecognized arguments: bitacora`

- [ ] **Step 3: Write minimal implementation**

Modify: `src/statscepal/cli.py` to add `bitacora` parser and subcommands (`lookup`, `add`, `list`, `sync`) connecting `BitacoraStore` and `AntiBiasValidator`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_bitacora_cli.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/statscepal/cli.py tests/test_bitacora_cli.py
git commit -m "feat: add bitacora lookup, add, list, and sync commands to statscepal CLI"
```

---

### Task 5: Seed Certified Chile Recipes & Run Anti-Bias Audit

**Files:**
- Create: `bitacoras/paises/chile/4788_recipe_chl_poblacion_total.md`
- Test: `tests/test_seed_recipes.py`

**Interfaces:**
- Consumes: `BitacoraStore`, live or mocked indicator data
- Produces: Fully certified, versioned recipe for Chile Total Population (`indicator_id=4788`, `country=Chile`, `member_id=224`)

- [ ] **Step 1: Write verification test for Chile recipe**

File: `tests/test_seed_recipes.py`
```python
from statscepal.bitacora.store import BitacoraStore


def test_chile_population_recipe_exists():
    store = BitacoraStore()
    store.sync()
    results = store.lookup("poblacion", country="Chile")
    assert len(results) >= 1
    recipe = results[0]
    assert recipe.country == "Chile"
    assert recipe.indicator_id == 4788
    assert recipe.country_member_id == 224
    assert recipe.antibias.unit_verified is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seed_recipes.py`
Expected: FAIL with `AssertionError: assert len(results) >= 1`

- [ ] **Step 3: Create certified recipe**

File: `bitacoras/paises/chile/4788_recipe_chl_poblacion_total.md`
```yaml
---
id: recipe-chl-4788-pob
indicator_id: 4788
indicator_name: "Población total, según sexo"
country: "Chile"
country_iso3: "CHL"
country_member_id: 224
theme: "Demográficos y sociales > Demográficos"
unit: "Miles de personas, a mitad del año"
member_ids: [224, 29190, 88623]
python_code: |
  from statscepal import CepalStatClient, DataExtractor
  with CepalStatClient() as client:
      extractor = DataExtractor(client)
      df = extractor.get_dataframe(4788, members=[224, 29190, 88623])
status: "certified"
date_certified: "2026-10-14"
tags: ["chile", "poblacion", "demografia", "celade"]
quality_report:
  total_records: 151
  null_count: 0
  null_ratio: 0.0
  has_gaps: false
  min_year: 1950
  max_year: 2100
antibias:
  unit_verified: true
  scale_factor_note: "Cifras expresadas en miles de personas. Multiplicar por 1,000 para personas individuales."
  is_projection: true
  base_year_split: 2021
  warnings:
    - "Cifras posteriores a 2021 son proyecciones demográficas basadas en el método de componentes por cohorte."
---

# Receta Certificada: Población total en Chile (CEPAL / CELADE)
...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_seed_recipes.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bitacoras/ tests/test_seed_recipes.py
git commit -m "feat: seed certified bitacora recipe for Chile total population"
```

---

### Task 6: Update Skill `cepalstat-api` with "Bitácora First" Protocol

**Files:**
- Modify: `.agents/skills/cepalstat-api/SKILL.md`
- Test: `tests/test_skill_structure.py`

**Interfaces:**
- Consumes: Bitácora protocol
- Produces: Updated Antigravity skill instructing agents to check `statscepal bitacora lookup` first

- [ ] **Step 1: Write test asserting "Bitácora First" is documented**

Modify `tests/test_skill_structure.py` to check that `bitacora` is prominently featured in the workflow.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_skill_structure.py`
Expected: FAIL

- [ ] **Step 3: Update `.agents/skills/cepalstat-api/SKILL.md`**

Add Step 0: "Bitácora First (Ahorro de Tokens y Anti-Sesgo)" explaining `statscepal bitacora lookup` and `statscepal bitacora add`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_skill_structure.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/cepalstat-api/SKILL.md tests/test_skill_structure.py
git commit -m "docs: update cepalstat-api skill with Bitacora First protocol"
```

---

### Task 7: Update Subagent `cepalstat_analyst` Prompt and Registration

**Files:**
- Modify: `.agents/subagents/cepalstat-analyst.md`
- Call `define_subagent` to update runtime system prompt

**Interfaces:**
- Produces: Enhanced `cepalstat_analyst` subagent that automatically consults bitácoras before external network calls.

- [ ] **Step 1: Update documentation in `.agents/subagents/cepalstat-analyst.md`**
- [ ] **Step 2: Update runtime agent via `define_subagent`**
- [ ] **Step 3: Commit**

```bash
git add .agents/subagents/cepalstat-analyst.md
git commit -m "feat: update cepalstat-analyst subagent with bitacora-first workflow"
```

---

### Task 8: Full Test Suite and Verification

**Files:**
- Test: All tests in `tests/`

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest`
Expected: All tests pass.

- [ ] **Step 2: Verify git status is clean**

Run: `git status`
Expected: clean working tree.
