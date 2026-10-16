"""CatalogStore for indexing and searching master indicators in SQLite."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any
import unicodedata
import pandas as pd
from statscepal.catalog.models import CatalogIndicator, CatalogStats
from statscepal.client import CepalStatClient
from statscepal.dimensions import Dimension, Member
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
        self.init_semantic_tables()

    def init_tables(self) -> None:
        """Initialize all catalog and semantic database tables."""
        self._init_db()
        self.init_semantic_tables()

    def init_semantic_tables(self) -> None:
        """Create relational semantic metadata tables in SQLite."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indicator_dimensions (
                    indicator_id INTEGER,
                    dim_id INTEGER,
                    dim_name TEXT,
                    pos INTEGER,
                    harvested_at TEXT,
                    content_hash TEXT,
                    PRIMARY KEY (indicator_id, dim_id)
                )
            """)
            cur = conn.execute("PRAGMA table_info(indicator_dimensions)")
            existing_cols = {row["name"] for row in cur.fetchall()}
            if "harvested_at" not in existing_cols:
                conn.execute("ALTER TABLE indicator_dimensions ADD COLUMN harvested_at TEXT")
            if "content_hash" not in existing_cols:
                conn.execute("ALTER TABLE indicator_dimensions ADD COLUMN content_hash TEXT")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dimension_members (
                    indicator_id INTEGER,
                    dim_id INTEGER,
                    member_id INTEGER,
                    member_name TEXT,
                    PRIMARY KEY (indicator_id, dim_id, member_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indicator_relationships (
                    indicator_a INTEGER,
                    indicator_b INTEGER,
                    rel_type TEXT,
                    PRIMARY KEY (indicator_a, indicator_b)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS temporal_availability (
                    indicator_id INTEGER,
                    country_code TEXT,
                    year INTEGER,
                    status TEXT,
                    prev_anchor INTEGER,
                    next_anchor INTEGER,
                    PRIMARY KEY (indicator_id, country_code, year)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indicator_metadata (
                    indicator_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    concept TEXT,
                    measure_type TEXT,
                    unit TEXT,
                    supported_facets TEXT
                )
            """)

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

    def store_indicator_dimensions(
        self,
        indicator_id: int,
        dimensions: list[Dimension],
        content_hash: str | None = None,
        harvested_at: str | None = None,
    ) -> None:
        """Store dimensions and their members for an indicator."""
        if harvested_at is None:
            harvested_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM dimension_members WHERE indicator_id = ?", (indicator_id,))
            conn.execute("DELETE FROM indicator_dimensions WHERE indicator_id = ?", (indicator_id,))
            for pos, dim in enumerate(dimensions):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO indicator_dimensions (indicator_id, dim_id, dim_name, pos, harvested_at, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (indicator_id, dim.id, dim.name, pos, harvested_at, content_hash),
                )
                for member in dim.members:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO dimension_members (indicator_id, dim_id, member_id, member_name)
                        VALUES (?, ?, ?, ?)
                        """,
                        (indicator_id, dim.id, member.id, member.name),
                    )

    def get_harvested_indicator_ids(self) -> set[int]:
        """Return a set of all indicator IDs present in indicator_dimensions."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT DISTINCT indicator_id FROM indicator_dimensions").fetchall()
            return {int(row["indicator_id"]) for row in rows}

    def get_harvest_stats(self) -> dict[str, int]:
        """Return harvesting statistics for indicator dimensions and members."""
        with self._get_connection() as conn:
            h_count = conn.execute(
                "SELECT COUNT(DISTINCT indicator_id) AS cnt FROM indicator_dimensions"
            ).fetchone()["cnt"]
            d_count = conn.execute("SELECT COUNT(*) AS cnt FROM indicator_dimensions").fetchone()["cnt"]
            m_count = conn.execute("SELECT COUNT(*) AS cnt FROM dimension_members").fetchone()["cnt"]
            return {
                "harvested_indicators": int(h_count or 0),
                "total_dimensions": int(d_count or 0),
                "total_members": int(m_count or 0),
            }

    def get_distinct_harvested_dimensions(self) -> list[dict[str, Any]]:
        """Return distinct harvested dimensions grouped by dim_id and dim_name with frequencies."""
        with self._get_connection() as conn:
            try:
                rows = conn.execute(
                    """
                    SELECT dim_id, dim_name, COUNT(DISTINCT indicator_id) AS indicator_count,
                           GROUP_CONCAT(indicator_id) AS raw_indicator_ids
                    FROM indicator_dimensions
                    GROUP BY dim_id, dim_name
                    ORDER BY indicator_count DESC, dim_id ASC
                    """
                ).fetchall()
            except sqlite3.OperationalError:
                return []

            result: list[dict[str, Any]] = []
            for row in rows:
                raw_ids = row["raw_indicator_ids"] or ""
                indicator_ids = sorted({int(x) for x in raw_ids.split(",") if x.strip()})
                result.append(
                    {
                        "dim_id": int(row["dim_id"]),
                        "dim_name": str(row["dim_name"] or ""),
                        "indicator_count": int(row["indicator_count"]),
                        "sample_indicator_ids": indicator_ids[:5],
                    }
                )
            return result

    def get_indicator_dimensions(self, indicator_id: int) -> list[Dimension]:
        """Retrieve dimensions and nested members for an indicator."""
        with self._get_connection() as conn:
            dim_rows = conn.execute(
                "SELECT dim_id, dim_name, pos FROM indicator_dimensions WHERE indicator_id = ? ORDER BY pos ASC",
                (indicator_id,),
            ).fetchall()
            if not dim_rows:
                return []

            member_rows = conn.execute(
                "SELECT dim_id, member_id, member_name FROM dimension_members WHERE indicator_id = ? ORDER BY rowid ASC",
                (indicator_id,),
            ).fetchall()

            members_by_dim: dict[int, list[Member]] = {}
            for m_row in member_rows:
                members_by_dim.setdefault(m_row["dim_id"], []).append(
                    Member(id=m_row["member_id"], name=m_row["member_name"])
                )

            dimensions: list[Dimension] = []
            for d_row in dim_rows:
                d_id = d_row["dim_id"]
                dimensions.append(
                    Dimension(
                        id=d_id,
                        name=d_row["dim_name"],
                        members=members_by_dim.get(d_id, []),
                    )
                )
            return dimensions

    def store_relationship(self, indicator_a: int, indicator_b: int, rel: str) -> None:
        """Store a typed relationship between two indicators."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO indicator_relationships (indicator_a, indicator_b, rel_type)
                VALUES (?, ?, ?)
                """,
                (indicator_a, indicator_b, rel),
            )

    def get_relationships(self, indicator_a: int) -> dict[int, str]:
        """Get all relationships for a given indicator."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT indicator_b, rel_type FROM indicator_relationships WHERE indicator_a = ?",
                (indicator_a,),
            ).fetchall()
            return {row["indicator_b"]: row["rel_type"] for row in rows}

    def store_temporal_record(
        self,
        indicator_id: int,
        country: str,
        year: int,
        status: str,
        prev: int | None,
        next: int | None,
    ) -> None:
        """Store an empirical temporal availability record."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO temporal_availability
                (indicator_id, country_code, year, status, prev_anchor, next_anchor)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (indicator_id, country, year, status, prev, next),
            )

    def get_temporal_record(
        self,
        indicator_id: int,
        country: str,
        year: int,
    ) -> tuple[str, int | None, int | None] | None:
        """Get the temporal availability record for (indicator_id, country, year)."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT status, prev_anchor, next_anchor
                FROM temporal_availability
                WHERE indicator_id = ? AND country_code = ? AND year = ?
                """,
                (indicator_id, country, year),
            ).fetchone()
            if not row:
                return None
            return (row["status"], row["prev_anchor"], row["next_anchor"])

    def get_target_indicators(self, indicator_a: int, rel_type: str) -> list[int]:
        """Get all target indicators related to indicator_a by a specific relationship type."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT indicator_b FROM indicator_relationships WHERE indicator_a = ? AND lower(rel_type) = ?",
                (indicator_a, rel_type.lower()),
            ).fetchall()
            return [row["indicator_b"] for row in rows]

    def store_indicator_metadata(
        self,
        indicator_id: int,
        name: str,
        concept: str,
        measure_type: str,
        unit: str,
        supported_facets: set[str] | list[str] | None = None,
    ) -> None:
        """Store indicator metadata including measure type, unit and facets."""
        facets_str = ",".join(sorted(supported_facets)) if supported_facets else ""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO indicator_metadata
                (indicator_id, name, concept, measure_type, unit, supported_facets)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (indicator_id, name, concept, measure_type, unit, facets_str),
            )

    def get_indicator_metadata(self, indicator_id: int) -> dict[str, Any] | None:
        """Retrieve indicator metadata from SQLite."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT indicator_id, name, concept, measure_type, unit, supported_facets FROM indicator_metadata WHERE indicator_id = ?",
                (indicator_id,),
            ).fetchone()
            if not row:
                return None
            facets = set(row["supported_facets"].split(",")) if row["supported_facets"] else set()
            return {
                "indicator_id": row["indicator_id"],
                "name": row["name"],
                "concept": row["concept"],
                "measure_type": row["measure_type"],
                "unit": row["unit"],
                "supported_facets": facets,
            }

    def populate_official_indicators(self) -> None:
        """Seed SQLite semantic tables with the 25 official CEPALSTAT indicators, dimensions, and relationships."""
        from statscepal.semantic.registry import DEFAULT_OFFICIAL_DIMENSIONS, VERTICAL_SLICE_INDICATORS

        self.init_semantic_tables()
        for ind_id, meta in VERTICAL_SLICE_INDICATORS.items():
            self.store_indicator_metadata(
                indicator_id=meta.indicator_id,
                name=meta.name,
                concept=meta.concept,
                measure_type=meta.measure_type,
                unit=meta.unit,
                supported_facets=meta.supported_facets,
            )
            for target_id, rel in meta.relationships.items():
                rel_str = rel.value if hasattr(rel, "value") else str(rel)
                self.store_relationship(meta.indicator_id, target_id, rel_str)

        for ind_id, dims in DEFAULT_OFFICIAL_DIMENSIONS.items():
            self.store_indicator_dimensions(ind_id, dims)

