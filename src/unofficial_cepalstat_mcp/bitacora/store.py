"""Dual Markdown and SQLite Storage Manager for Bitácoras."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml

from unofficial_cepalstat_mcp.bitacora.models import BitacoraRecipe
from unofficial_cepalstat_mcp.config import get_cache_db_path

DEFAULT_BITACORAS_DIR = Path("bitacoras")
DEFAULT_DB_PATH = get_cache_db_path()


class BitacoraStore:
    """Manages saving, loading, indexing, and querying Bitácora recipes."""

    def __init__(
        self,
        base_dir: Path | str = DEFAULT_BITACORAS_DIR,
        db_path: Path | str | None = None,
    ):
        self.base_dir = Path(base_dir)
        self.db_path = Path(db_path) if db_path is not None else get_cache_db_path()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if self.db_path.parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield an active SQLite connection and ensure it is properly closed."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000;")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create recipes SQLite table if it does not already exist."""
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

    def save_recipe(self, recipe: BitacoraRecipe) -> Path:
        """Save recipe as a Markdown file with YAML frontmatter and index it in SQLite."""
        country_slug = recipe.country.lower().replace(" ", "_") if recipe.country else "general"
        target_dir = self.base_dir / "paises" / country_slug
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{recipe.indicator_id}_{recipe.id}.md"
        filepath = target_dir / filename

        frontmatter_dict = recipe.model_dump()
        frontmatter_yaml = yaml.dump(frontmatter_dict, sort_keys=False, allow_unicode=True)

        scale_note = recipe.antibias.scale_factor_note if recipe.antibias else "N/A"
        projection_note = (
            f"Sí (Post-{recipe.antibias.base_year_split})"
            if (recipe.antibias and recipe.antibias.is_projection and recipe.antibias.base_year_split)
            else ("Sí" if (recipe.antibias and recipe.antibias.is_projection) else "No")
        )

        body_content = f"""---
{frontmatter_yaml}---

# Receta: {recipe.indicator_name} ({recipe.country})

## Alertas Anti-Sesgo y Calidad de Datos
- **Unidad**: {recipe.unit}
- **Nota de Escala**: {scale_note}
- **Proyección**: {projection_note}

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

        return filepath

    def get_recipe(self, recipe_id: str) -> BitacoraRecipe | None:
        """Retrieve a recipe by its unique ID from the SQLite index."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT full_json FROM recipes WHERE id = ?", (recipe_id,))
            row = cursor.fetchone()
            if row:
                return BitacoraRecipe.model_validate_json(row["full_json"])
        return None

    def lookup(
        self,
        query: str = "",
        country: str | None = None,
        tag: str | None = None,
    ) -> list[BitacoraRecipe]:
        """Query indexed recipes using exact and partial filters."""
        sql = "SELECT full_json FROM recipes WHERE 1=1"
        params: list[Any] = []

        if query:
            sql += " AND (id LIKE ? OR indicator_name LIKE ? OR theme LIKE ? OR tags LIKE ?)"
            wildcard = f"%{query}%"
            params.extend([wildcard, wildcard, wildcard, wildcard])

        if country:
            sql += " AND (country LIKE ? OR country_iso3 LIKE ?)"
            wildcard_country = f"%{country}%"
            params.extend([wildcard_country, wildcard_country])

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
                try:
                    text = md_file.read_text(encoding="utf-8")
                except Exception:
                    continue
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    yaml_content = parts[1]
                    try:
                        data = yaml.safe_load(yaml_content)
                        if not isinstance(data, dict):
                            continue
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
        return count
