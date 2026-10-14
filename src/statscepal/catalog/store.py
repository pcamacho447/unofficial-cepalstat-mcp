"""CatalogStore for indexing and searching master indicators in SQLite."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any
import unicodedata
import pandas as pd
from statscepal.catalog.models import CatalogIndicator, CatalogStats
from statscepal.client import CepalStatClient
from statscepal.thematic_tree import ThematicTree

DEFAULT_DB_PATH = Path(".statscepal_cache.db")


def strip_accents(text: Any) -> str:
    """Normalize text by converting to lowercase and stripping diacritics."""
    if text is None:
        return ""
    s = str(text)
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()


class CatalogStore:
    """Manages downloading, persisting, and querying the master indicators catalog."""

    def __init__(
        self,
        db_path: Path | str = DEFAULT_DB_PATH,
        client: CepalStatClient | None = None,
    ):
        self.db_path = Path(db_path)
        self.client = client
        if self.db_path.parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield an active SQLite connection and ensure it is properly closed."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.create_function("unaccent", 1, strip_accents)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create master_indicators SQLite table and indexes if not already present."""
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
                row = cursor.fetchone()
                return int(row["total"]) if row else 0

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
                clean_path = [
                    p for p in path_parts
                    if "clasificación" not in p.lower() and "clasificacion" not in p.lower()
                ]
                theme = clean_path[0] if len(clean_path) > 0 else ""
                area = clean_path[1] if len(clean_path) > 1 else ""
                subarea = clean_path[2] if len(clean_path) > 2 else ""

                indicators_to_insert.append({
                    "indicator_id": int(node["indicator_id"]),
                    "name": name,
                    "order_num": node.get("order") if node.get("order") is not None else node.get("order_num"),
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

        if isinstance(root, dict):
            extract_indicators(root, [])

        with self._get_connection() as conn:
            conn.execute("DELETE FROM master_indicators")
            for item in indicators_to_insert:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO master_indicators
                    (indicator_id, name, order_num, theme, area, subarea, full_path, updated_at)
                    VALUES (:indicator_id, :name, :order_num, :theme, :area, :subarea, :full_path, :updated_at)
                    """,
                    item,
                )

        return len(indicators_to_insert)

    def search(
        self,
        query: str = "",
        theme: str | None = None,
        limit: int = 20,
    ) -> list[CatalogIndicator]:
        """Search master indicators with case-insensitive substring matching."""
        sql = "SELECT * FROM master_indicators WHERE 1=1"
        params: list[Any] = []

        if query:
            clean_q = strip_accents(query)
            sql += " AND (unaccent(name) LIKE ? OR unaccent(full_path) LIKE ? OR unaccent(area) LIKE ?)"
            wildcard = f"%{clean_q}%"
            params.extend([wildcard, wildcard, wildcard])

        if theme:
            clean_t = strip_accents(theme)
            sql += " AND unaccent(theme) LIKE ?"
            params.append(f"%{clean_t}%")

        sql += " ORDER BY order_num ASC LIMIT ?"
        params.append(limit)

        results: list[CatalogIndicator] = []
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            for row in cursor.fetchall():
                results.append(
                    CatalogIndicator(
                        indicator_id=row["indicator_id"],
                        name=row["name"],
                        order_num=row["order_num"],
                        theme=row["theme"],
                        area=row["area"],
                        subarea=row["subarea"] or "",
                        full_path=row["full_path"],
                        updated_at=row["updated_at"] or "",
                    )
                )

        return results

    def get_stats(self) -> CatalogStats:
        """Compute aggregated statistics of the master catalog."""
        with self._get_connection() as conn:
            c1 = conn.execute("SELECT COUNT(*) AS total FROM master_indicators")
            total = c1.fetchone()["total"]

            c2 = conn.execute(
                "SELECT COUNT(DISTINCT theme) AS cnt FROM master_indicators WHERE theme != '' AND theme IS NOT NULL"
            )
            themes_cnt = c2.fetchone()["cnt"]

            c3 = conn.execute(
                "SELECT COUNT(DISTINCT area) AS cnt FROM master_indicators WHERE area != '' AND area IS NOT NULL"
            )
            areas_cnt = c3.fetchone()["cnt"]

            by_theme: dict[str, int] = {}
            c4 = conn.execute(
                "SELECT theme, COUNT(*) AS count FROM master_indicators WHERE theme != '' AND theme IS NOT NULL GROUP BY theme ORDER BY count DESC"
            )
            for row in c4.fetchall():
                t = row["theme"]
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
        if out_path.parent:
            out_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM master_indicators ORDER BY indicator_id", conn)

        if format.lower() == "csv":
            df.to_csv(out_path, index=False, encoding="utf-8")
        else:
            df.to_json(out_path, orient="records", force_ascii=False, indent=2)

        return out_path
