"""CatalogStore for indexing and searching master indicators in SQLite."""

import json
import re
import sqlite3
import unicodedata
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from unofficial_cepalstat_mcp.catalog.models import CatalogIndicator, CatalogStats
from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.config import get_cache_db_path
from unofficial_cepalstat_mcp.dimensions import Dimension, Member
from unofficial_cepalstat_mcp.thematic_tree import ThematicTree

DEFAULT_DB_PATH = get_cache_db_path()

SPANISH_STOPWORDS: frozenset[str] = frozenset({
    "de", "del", "la", "el", "los", "las", "en", "por", "segun", "para", "con", "sin", "a", "y", "o",
    "un", "una", "unos", "unas", "al", "lo", "su", "sus", "sobre", "entre", "tras", "durante", "mediante",
    "contra", "hacia", "hasta", "desde", "e", "u", "ni", "que", "cual", "cuales", "como", "donde", "cuando",
    "quien", "quienes", "and", "or", "not", "near",
})


def _spanish_stems(token: str) -> list[str]:
    """Extract base stems for Spanish plural and gender inflections."""
    stems: list[str] = []
    t = token.lower()
    if t.endswith("ces") and len(t) > 4:
        stems.append(t[:-3] + "z")
    elif t.endswith("es") and len(t) > 4:
        stems.append(t[:-2])
    elif t.endswith("s") and len(t) > 3:
        stems.append(t[:-1])

    for s in list(stems) + [t]:
        if (s.endswith("a") or s.endswith("o")) and len(s) > 4:
            stems.append(s[:-1])

    if t.startswith("desocup") and len(t) > 7:
        stems.append("desocup")

    return list(dict.fromkeys(stems))


@lru_cache(maxsize=1)
def _get_thesaurus_synonym_lookup() -> dict[str, list[str]]:
    """Build bidirectional synonym lookup from Thesaurus and domain equivalences."""
    from unofficial_cepalstat_mcp.semantic.thesaurus import get_default_thesaurus

    thesaurus = get_default_thesaurus()
    lookup: dict[str, set[str]] = {}

    def add_syn(k: str, v: str) -> None:
        k_clean = strip_accents(k).strip()
        v_clean = strip_accents(v).strip()
        if k_clean and v_clean and k_clean != v_clean:
            lookup.setdefault(k_clean, set()).add(v_clean)

    for domain, synset_list in thesaurus.synsets.items():
        for synset in synset_list:
            if synset.canonical_id == "EMPLEO_GENERAL":
                unemp = {"desempleo", "desocupacion", "paro"}
                for t1 in unemp:
                    for t2 in unemp:
                        add_syn(t1, t2)
                emp = {"empleo", "trabajo", "ocupacion", "chamba", "pega", "laburo", "camello"}
                for t1 in emp:
                    for t2 in emp:
                        add_syn(t1, t2)
                continue

            all_terms: set[str] = set()
            if synset.canonical_term:
                all_terms.add(synset.canonical_term)
            all_terms.update(synset.synonyms)
            for tags in synset.regional_tags.values():
                all_terms.update(tags)

            terms_list = [strip_accents(t) for t in all_terms if t.strip()]
            for t1 in terms_list:
                for t2 in terms_list:
                    add_syn(t1, t2)

    # Curated domain associations
    for inf_term in ["inflacion", "tasa de inflacion"]:
        add_syn(inf_term, "ipc")
        add_syn(inf_term, "precios consumidor")
        add_syn(inf_term, "indice de precios al consumidor")
    add_syn("ipc", "inflacion")
    add_syn("ipc", "precios al consumidor")
    add_syn("pib", "producto interno bruto")
    add_syn("pib", "actividad economica")
    add_syn("producto interno bruto", "pib")

    return {k: sorted(v) for k, v in lookup.items()}


def _build_fts_match_query(query: str, operator: str = "AND") -> str:
    """Construct an FTS5 MATCH query with stems and Thesaurus synonym expansions."""
    clean = strip_accents(query)
    raw_tokens = re.findall(r"[a-z0-9]+", clean)
    tokens = [
        tok for tok in raw_tokens
        if len(tok) >= 2 and not re.match(r"^\d{4}$", tok) and tok not in SPANISH_STOPWORDS
    ]
    if not tokens:
        return ""

    syn_map = _get_thesaurus_synonym_lookup()
    clauses: list[str] = []
    for tok in tokens:
        variants: set[str] = {f"{tok}*"}
        for stem in _spanish_stems(tok):
            variants.add(f"{stem}*")
        for syn in syn_map.get(tok, []):
            syn_words = syn.split()
            if len(syn_words) == 1:
                variants.add(f"{syn}*")
                for stem in _spanish_stems(syn):
                    variants.add(f"{stem}*")
            else:
                clean_syn = " ".join(re.findall(r"[a-z0-9]+", syn))
                if clean_syn:
                    variants.add(f'"{clean_syn}"')
        clauses.append("(" + " OR ".join(sorted(variants)) + ")")

    join_str = f" {operator} "
    return join_str.join(clauses)


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
        db_path: Path | str | None = None,
        client: CepalStatClient | None = None,
        auto_seed: bool | None = None,
    ):
        self.db_path = Path(db_path) if db_path is not None else get_cache_db_path()
        self.client = client
        should_seed = auto_seed if auto_seed is not None else (db_path is None)
        if should_seed:
            from unofficial_cepalstat_mcp.catalog.seed import ensure_seed_hydrated

            ensure_seed_hydrated(self.db_path, force=bool(auto_seed and db_path is not None))
        if self.db_path.parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield an active SQLite connection and ensure it is properly closed."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.create_function("unaccent", 1, strip_accents)
        conn.execute("PRAGMA busy_timeout = 10000;")
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
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS indicators_fts USING fts5(
                    indicator_id UNINDEXED,
                    name,
                    subarea,
                    area,
                    theme,
                    unit,
                    member_labels,
                    tokenize='unicode61 remove_diacritics 2'
                )
            """)
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
                    provenance TEXT DEFAULT 'curated',
                    PRIMARY KEY (indicator_a, indicator_b)
                )
            """)
            cur = conn.execute("PRAGMA table_info(indicator_relationships)")
            existing_rel_cols = {row["name"] for row in cur.fetchall()}
            if "provenance" not in existing_rel_cols:
                conn.execute("ALTER TABLE indicator_relationships ADD COLUMN provenance TEXT DEFAULT 'curated'")
                conn.execute("UPDATE indicator_relationships SET provenance = 'curated' WHERE provenance IS NULL")
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
                    supported_facets TEXT,
                    definition TEXT DEFAULT '',
                    periodicity TEXT DEFAULT ''
                )
            """)
            cur_meta = conn.execute("PRAGMA table_info(indicator_metadata)")
            existing_meta_cols = {row["name"] for row in cur_meta.fetchall()}
            if "definition" not in existing_meta_cols:
                conn.execute("ALTER TABLE indicator_metadata ADD COLUMN definition TEXT DEFAULT ''")
            if "periodicity" not in existing_meta_cols:
                conn.execute("ALTER TABLE indicator_metadata ADD COLUMN periodicity TEXT DEFAULT ''")

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

        self.rebuild_fts_index()
        return len(indicators_to_insert)

    def _update_indicator_fts(self, conn: sqlite3.Connection, indicator_id: int) -> None:
        """Update or insert a single indicator in indicators_fts."""
        from unofficial_cepalstat_mcp.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY

        row = conn.execute(
            "SELECT indicator_id, name, subarea, area, theme FROM master_indicators WHERE indicator_id = ?",
            (indicator_id,),
        ).fetchone()
        if not row:
            return

        meta_row = conn.execute(
            "SELECT unit FROM indicator_metadata WHERE indicator_id = ?",
            (indicator_id,),
        ).fetchone()
        unit = meta_row["unit"] if meta_row and meta_row["unit"] else ""

        dim_rows = conn.execute(
            """
            SELECT d.dim_id, d.dim_name, m.member_name
            FROM indicator_dimensions d
            JOIN dimension_members m ON d.indicator_id = m.indicator_id AND d.dim_id = m.dim_id
            WHERE d.indicator_id = ?
            """,
            (indicator_id,),
        ).fetchall()

        member_names: set[str] = set()
        for d in dim_rows:
            if not DEFAULT_FACET_ONTOLOGY.is_structural_dimension(d["dim_id"], d["dim_name"]):
                member_names.add(str(d["member_name"]))

        member_labels = " ".join(sorted(member_names))

        conn.execute("DELETE FROM indicators_fts WHERE indicator_id = ?", (indicator_id,))
        conn.execute(
            """
            INSERT INTO indicators_fts (indicator_id, name, subarea, area, theme, unit, member_labels)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                indicator_id,
                row["name"],
                row["subarea"] or "",
                row["area"] or "",
                row["theme"] or "",
                unit,
                member_labels,
            ),
        )

    def rebuild_fts_index(self) -> int:
        """Rebuild the indicators_fts virtual table from master_indicators and dimensions."""
        from unofficial_cepalstat_mcp.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY

        with self._get_connection() as conn:
            conn.execute("DELETE FROM indicators_fts")

            dim_rows = conn.execute(
                """
                SELECT d.indicator_id, d.dim_id, d.dim_name, m.member_name
                FROM indicator_dimensions d
                JOIN dimension_members m ON d.indicator_id = m.indicator_id AND d.dim_id = m.dim_id
                """
            ).fetchall()
            members_by_ind: dict[int, set[str]] = {}
            for r in dim_rows:
                if not DEFAULT_FACET_ONTOLOGY.is_structural_dimension(r["dim_id"], r["dim_name"]):
                    members_by_ind.setdefault(int(r["indicator_id"]), set()).add(str(r["member_name"]))

            ind_rows = conn.execute(
                """
                SELECT m.indicator_id, m.name, m.subarea, m.area, m.theme, COALESCE(md.unit, '') AS unit
                FROM master_indicators m
                LEFT JOIN indicator_metadata md ON m.indicator_id = md.indicator_id
                """
            ).fetchall()

            count = 0
            for r in ind_rows:
                ind_id = int(r["indicator_id"])
                mem_labels = " ".join(sorted(members_by_ind.get(ind_id, set())))
                conn.execute(
                    """
                    INSERT INTO indicators_fts (indicator_id, name, subarea, area, theme, unit, member_labels)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ind_id,
                        r["name"],
                        r["subarea"] or "",
                        r["area"] or "",
                        r["theme"] or "",
                        r["unit"] or "",
                        mem_labels,
                    ),
                )
                count += 1
            return count

    def _build_fts_match_query(self, query: str, operator: str = "AND") -> str:
        """Construct an FTS5 MATCH query with stems and Thesaurus synonym expansions."""
        return _build_fts_match_query(query, operator=operator)

    def search(
        self,
        query: str = "",
        theme: str | None = None,
        area: str | None = None,
        limit: int = 20,
    ) -> list[CatalogIndicator]:
        """Search master indicators with FTS5 BM25 ranking, synonym expansion, and fallback matching."""
        if not query or not query.strip():
            sql = "SELECT * FROM master_indicators WHERE 1=1"
            params: list[Any] = []
            if theme:
                sql += " AND unaccent(theme) LIKE ?"
                params.append(f"%{strip_accents(theme)}%")
            if area:
                sql += " AND unaccent(area) LIKE ?"
                params.append(f"%{strip_accents(area)}%")
            sql += " ORDER BY order_num ASC, indicator_id ASC LIMIT ?"
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

        def _execute_fts(conn: sqlite3.Connection, match_clause: str) -> list[CatalogIndicator]:
            sql = """
                SELECT m.indicator_id, m.name, m.order_num, m.theme, m.area, m.subarea, m.full_path, m.updated_at,
                       bm25(indicators_fts, 0.0, 10.0, 4.0, 3.0, 1.5, 2.0, 2.5) AS bm25_score
                FROM master_indicators m
                JOIN indicators_fts ON m.indicator_id = indicators_fts.indicator_id
                WHERE indicators_fts MATCH ?
            """
            params: list[Any] = [match_clause]
            if theme:
                sql += " AND unaccent(m.theme) LIKE ?"
                params.append(f"%{strip_accents(theme)}%")
            if area:
                sql += " AND unaccent(m.area) LIKE ?"
                params.append(f"%{strip_accents(area)}%")
            sql += " ORDER BY bm25_score ASC, m.indicator_id ASC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            fts_results: list[CatalogIndicator] = []
            for row in cursor.fetchall():
                fts_results.append(
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
            return fts_results

        with self._get_connection() as conn:
            fts_count_row = conn.execute("SELECT 1 FROM indicators_fts LIMIT 1").fetchone()
            if not fts_count_row:
                has_master = conn.execute("SELECT 1 FROM master_indicators LIMIT 1").fetchone()
                if has_master:
                    self.rebuild_fts_index()

            and_query = self._build_fts_match_query(query, operator="AND")
            if and_query:
                try:
                    and_res = _execute_fts(conn, and_query)
                    if and_res:
                        return and_res
                except sqlite3.OperationalError:
                    pass

            or_query = self._build_fts_match_query(query, operator="OR")
            if or_query and or_query != and_query:
                try:
                    or_res = _execute_fts(conn, or_query)
                    if or_res:
                        return or_res
                except sqlite3.OperationalError:
                    pass

            # Safe fallback to substring LIKE query
            clean_q = strip_accents(query)
            fallback_sql = "SELECT * FROM master_indicators WHERE 1=1"
            fallback_params: list[Any] = []
            if clean_q:
                fallback_sql += (
                    " AND (unaccent(name) LIKE ? OR unaccent(full_path) LIKE ? OR unaccent(area) LIKE ?)"
                )
                wildcard = f"%{clean_q}%"
                fallback_params.extend([wildcard, wildcard, wildcard])
            if theme:
                fallback_sql += " AND unaccent(theme) LIKE ?"
                fallback_params.append(f"%{strip_accents(theme)}%")
            if area:
                fallback_sql += " AND unaccent(area) LIKE ?"
                fallback_params.append(f"%{strip_accents(area)}%")
            fallback_sql += " ORDER BY order_num ASC, indicator_id ASC LIMIT ?"
            fallback_params.append(limit)

            cursor = conn.execute(fallback_sql, fallback_params)
            fallback_results: list[CatalogIndicator] = []
            for row in cursor.fetchall():
                fallback_results.append(
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
            return fallback_results

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
            self._update_indicator_fts(conn, indicator_id)

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

    def get_all_indicator_dimensions(
        self, *, include_structural: bool = True
    ) -> dict[int, list[Dimension]]:
        """Retrieve all indicator dimensions and members from SQLite in bulk."""
        from unofficial_cepalstat_mcp.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY

        with self._get_connection() as conn:
            try:
                dim_rows = conn.execute(
                    "SELECT indicator_id, dim_id, dim_name FROM indicator_dimensions ORDER BY indicator_id, dim_id"
                ).fetchall()
                if not include_structural:
                    structural_dims = {
                        (int(d["indicator_id"]), int(d["dim_id"]))
                        for d in dim_rows
                        if DEFAULT_FACET_ONTOLOGY.is_structural_dimension(
                            int(d["dim_id"]), str(d["dim_name"])
                        )
                    }
                    member_rows = conn.execute(
                        "SELECT indicator_id, dim_id, member_id, member_name FROM dimension_members ORDER BY indicator_id, dim_id, member_id"
                    ).fetchall()
                    member_rows = [
                        m
                        for m in member_rows
                        if (int(m["indicator_id"]), int(m["dim_id"])) not in structural_dims
                    ]
                else:
                    structural_dims = set()
                    member_rows = conn.execute(
                        "SELECT indicator_id, dim_id, member_id, member_name FROM dimension_members ORDER BY indicator_id, dim_id, member_id"
                    ).fetchall()
            except sqlite3.OperationalError:
                return {}

            members_by_ind_dim: dict[tuple[int, int], list[Member]] = {}
            for m in member_rows:
                key = (int(m["indicator_id"]), int(m["dim_id"]))
                members_by_ind_dim.setdefault(key, []).append(
                    Member(id=int(m["member_id"]), name=str(m["member_name"]))
                )

            dims_by_ind: dict[int, list[Dimension]] = {}
            for d in dim_rows:
                ind_id = int(d["indicator_id"])
                dim_id = int(d["dim_id"])
                if not include_structural and (ind_id, dim_id) in structural_dims:
                    members = []
                else:
                    members = members_by_ind_dim.get((ind_id, dim_id), [])
                dims_by_ind.setdefault(ind_id, []).append(
                    Dimension(id=dim_id, name=str(d["dim_name"]), members=members)
                )

            return dims_by_ind

    def store_relationship(
        self,
        indicator_a: int,
        indicator_b: int,
        rel: str,
        provenance: str = "curated",
    ) -> bool:
        """Store a typed relationship between two indicators with provenance tracking."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT provenance FROM indicator_relationships WHERE indicator_a = ? AND indicator_b = ?",
                (indicator_a, indicator_b),
            ).fetchone()
            if row is not None and row["provenance"] == "curated" and provenance == "inferred":
                return False

            conn.execute(
                """
                INSERT OR REPLACE INTO indicator_relationships (indicator_a, indicator_b, rel_type, provenance)
                VALUES (?, ?, ?, ?)
                """,
                (indicator_a, indicator_b, rel, provenance),
            )
            return True

    def get_relationships_with_provenance(self, indicator_a: int) -> dict[int, dict[str, str]]:
        """Get all relationships for a given indicator including provenance."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT indicator_b, rel_type, provenance FROM indicator_relationships WHERE indicator_a = ?",
                (indicator_a,),
            ).fetchall()
            return {
                row["indicator_b"]: {
                    "rel_type": row["rel_type"],
                    "provenance": row["provenance"] or "curated",
                }
                for row in rows
            }

    def get_all_relationships(self, provenance: str | None = None) -> list[dict[str, Any]]:
        """Retrieve all relationships optionally filtered by provenance."""
        sql = "SELECT indicator_a, indicator_b, rel_type, provenance FROM indicator_relationships"
        params: list[Any] = []
        if provenance is not None:
            sql += " WHERE provenance = ?"
            params.append(provenance)
        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [
                {
                    "indicator_a": row["indicator_a"],
                    "indicator_b": row["indicator_b"],
                    "rel_type": row["rel_type"],
                    "provenance": row["provenance"] or "curated",
                }
                for row in rows
            ]

    def clear_inferred_relationships(self) -> int:
        """Clear all inferred relationships while preserving curated relationships."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM indicator_relationships WHERE provenance = 'inferred'")
            return cursor.rowcount

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
        definition: str = "",
        periodicity: str = "",
    ) -> None:
        """Store indicator metadata including measure type, unit, facets, definition and periodicity."""
        facets_str = ",".join(sorted(supported_facets)) if supported_facets else ""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO indicator_metadata
                (indicator_id, name, concept, measure_type, unit, supported_facets, definition, periodicity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (indicator_id, name, concept, measure_type, unit, facets_str, definition, periodicity),
            )
            self._update_indicator_fts(conn, indicator_id)

    def get_indicator_metadata(self, indicator_id: int) -> dict[str, Any] | None:
        """Retrieve indicator metadata from SQLite."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT indicator_id, name, concept, measure_type, unit, supported_facets, definition, periodicity FROM indicator_metadata WHERE indicator_id = ?",
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
                "definition": row["definition"] or "",
                "periodicity": row["periodicity"] or "",
            }

    def get_all_indicator_metadata(self) -> dict[int, dict[str, Any]]:
        """Retrieve all indicator metadata from SQLite in bulk."""
        with self._get_connection() as conn:
            try:
                rows = conn.execute(
                    "SELECT indicator_id, name, concept, measure_type, unit, supported_facets, definition, periodicity FROM indicator_metadata"
                ).fetchall()
            except sqlite3.OperationalError:
                return {}

            results: dict[int, dict[str, Any]] = {}
            for row in rows:
                raw_facets = row["supported_facets"]
                facets: set[str] = set()
                if raw_facets:
                    raw_str = str(raw_facets).strip()
                    if raw_str.startswith("[") or raw_str.startswith("{"):
                        try:
                            parsed = json.loads(raw_str)
                            if isinstance(parsed, (list, set)):
                                facets = {str(x) for x in parsed}
                        except Exception:
                            facets = {x.strip() for x in raw_str.split(",") if x.strip()}
                    else:
                        facets = {x.strip() for x in raw_str.split(",") if x.strip()}

                results[int(row["indicator_id"])] = {
                    "indicator_id": int(row["indicator_id"]),
                    "name": str(row["name"]),
                    "concept": row["concept"],
                    "measure_type": row["measure_type"],
                    "unit": row["unit"],
                    "supported_facets": facets,
                    "definition": row["definition"] or "",
                    "periodicity": row["periodicity"] or "",
                }
            return results

    def get_master_indicator(self, indicator_id: int) -> dict[str, Any] | None:
        """Retrieve a single master indicator row by indicator_id."""
        with self._get_connection() as conn:
            try:
                row = conn.execute(
                    "SELECT indicator_id, name, order_num, theme, area, subarea, full_path, updated_at FROM master_indicators WHERE indicator_id = ?",
                    (indicator_id,),
                ).fetchone()
                return dict(row) if row else None
            except sqlite3.OperationalError:
                return None

    def get_all_master_indicators(self) -> list[dict[str, Any]]:
        """Retrieve all master indicators from SQLite."""
        with self._get_connection() as conn:
            try:
                rows = conn.execute(
                    "SELECT indicator_id, name, order_num, theme, area, subarea, full_path, updated_at FROM master_indicators"
                ).fetchall()
                return [
                    {
                        "indicator_id": int(r["indicator_id"]),
                        "name": str(r["name"]),
                        "order_num": r["order_num"],
                        "theme": str(r["theme"]),
                        "area": str(r["area"]),
                        "subarea": str(r["subarea"] or "") if r["subarea"] is not None else "",
                        "full_path": str(r["full_path"]),
                        "updated_at": str(r["updated_at"] or "") if r["updated_at"] is not None else "",
                    }
                    for r in rows
                ]
            except sqlite3.OperationalError:
                return []

    def populate_official_indicators(self) -> None:
        """Seed SQLite semantic tables with the 25 official CEPALSTAT indicators, dimensions, and relationships."""
        from unofficial_cepalstat_mcp.semantic.registry import (
            DEFAULT_OFFICIAL_DIMENSIONS,
            VERTICAL_SLICE_INDICATORS,
        )

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

