"""Harvesting engine for CEPALSTAT indicator dimension metadata."""

import hashlib
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

from unofficial_cepalstat_mcp.catalog.models import HarvestSummary
from unofficial_cepalstat_mcp.catalog.store import CatalogStore, strip_accents
from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.dimensions import (
    SYNTHETIC_DIMENSION_MEMBER_IDS,
    Dimension,
    Member,
)
from unofficial_cepalstat_mcp.exceptions import CepalStatAPIError, CepalStatNetworkError
from unofficial_cepalstat_mcp.thematic_tree import ThematicTree

logger = logging.getLogger(__name__)


class CatalogHarvester:
    """Harvests indicator dimension metadata with checkpointing, rate limiting, and backoff."""

    def __init__(
        self,
        client: CepalStatClient,
        store: CatalogStore,
        rate_limit_delay: float = 0.05,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
    ) -> None:
        self.client = client
        self.store = store
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base

    @staticmethod
    def compute_content_hash(payload: Any) -> str:
        """Compute deterministic SHA-256 hash of API payload."""
        if isinstance(payload, bytes):
            return hashlib.sha256(payload).hexdigest()
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_dimensions(raw_response: dict[str, Any]) -> list[Dimension]:
        """Decode and parse raw API response into a list of Dimension objects."""
        body = raw_response.get("body") or {}
        raw_dims = body.get("dimensions", []) if isinstance(body, dict) else []

        dimensions: list[Dimension] = []
        if isinstance(raw_dims, list):
            for raw_dim in raw_dims:
                if not isinstance(raw_dim, dict):
                    continue
                members = [
                    Member(
                        id=int(m["id"]),
                        name=str(m.get("name", "")),
                        order=m.get("order"),
                        parent=m.get("parent"),
                        selected=m.get("selected"),
                        is_synthetic=int(m["id"]) in SYNTHETIC_DIMENSION_MEMBER_IDS,
                    )
                    for m in raw_dim.get("members", [])
                    if isinstance(m, dict) and "id" in m
                ]
                dimensions.append(
                    Dimension(
                        id=int(raw_dim["id"]),
                        name=str(raw_dim.get("name", "")),
                        members=members,
                    )
                )
        return dimensions

    @staticmethod
    def _notify_progress(
        on_progress: Any,
        current_idx: int,
        total_count: int,
        indicator_id: int,
        status: str,
    ) -> None:
        if on_progress is None:
            return
        try:
            on_progress(current_idx, total_count, indicator_id, status)
        except TypeError:
            on_progress(current_idx, total_count, indicator_id)

    @staticmethod
    def _parse_metadata(raw: Any) -> dict[str, str]:
        """Parse indicator metadata response into clean dict."""
        if not isinstance(raw, dict):
            return {"unit": "", "definition": "", "periodicity": ""}
        body = raw.get("body", raw)
        meta = body.get("metadata", body) if isinstance(body, dict) else {}
        if not isinstance(meta, dict):
            return {"unit": "", "definition": "", "periodicity": ""}
        return {
            "unit": str(meta.get("unit") or "").strip(),
            "definition": str(meta.get("definition") or "").strip(),
            "periodicity": str(meta.get("periodicity") or "").strip(),
        }

    def harvest(
        self,
        indicator_ids: list[int] | None = None,
        resume: bool = True,
        force: bool = False,
        on_progress: Callable[[int, int, int, str], None] | Callable[[int, int, int], None] | None = None,
        include_metadata: bool = True,
    ) -> HarvestSummary:
        """Harvest dimension metadata for indicators.

        Args:
            indicator_ids: Specific indicator IDs to harvest. If None, queries all master_indicators.
            resume: If True and not force, skips already harvested indicators.
            force: If True, re-harvests indicators even if already harvested.
            on_progress: Optional callback invoked as (idx, total, indicator_id, status).
            include_metadata: If True, fetches and stores indicator metadata (unit, definition, periodicity).

        Returns:
            HarvestSummary with run statistics.
        """
        start_time = time.perf_counter()

        if indicator_ids is None:
            with self.store._get_connection() as conn:
                rows = conn.execute(
                    "SELECT indicator_id FROM master_indicators ORDER BY indicator_id ASC"
                ).fetchall()
                target_ids = [int(r["indicator_id"]) for r in rows]
        else:
            target_ids = list(indicator_ids)

        harvested_ids = self.store.get_harvested_indicator_ids()
        if resume and not force:
            pending_ids = [i for i in target_ids if i not in harvested_ids]
            already_harvested = len(target_ids) - len(pending_ids)
        else:
            pending_ids = list(target_ids)
            already_harvested = 0

        newly_harvested = 0
        failed_ids: list[int] = []
        total_pending = len(pending_ids)

        max_attempts = max(1, self.max_retries)

        for idx, ind_id in enumerate(pending_ids, start=1):
            for attempt in range(max_attempts):
                if self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)
                try:
                    raw_response = self.client.get(f"/cepalstat/api/v1/indicator/{ind_id}/dimensions")
                    dimensions = self._parse_dimensions(raw_response)
                    content_hash = self.compute_content_hash(raw_response)
                    harvested_at = datetime.now(timezone.utc).isoformat()
                    self.store.store_indicator_dimensions(
                        indicator_id=ind_id,
                        dimensions=dimensions,
                        content_hash=content_hash,
                        harvested_at=harvested_at,
                    )

                    if include_metadata:
                        try:
                            if self.rate_limit_delay > 0:
                                time.sleep(self.rate_limit_delay)
                            raw_meta = self.client.get(f"/cepalstat/api/v1/indicator/{ind_id}/metadata")
                            parsed_meta = self._parse_metadata(raw_meta)
                            existing_meta = self.store.get_indicator_metadata(ind_id)
                            name = ""
                            concept = ""
                            measure_type = ""
                            facets: set[str] = set()
                            if existing_meta:
                                name = existing_meta.get("name") or ""
                                concept = existing_meta.get("concept") or ""
                                measure_type = existing_meta.get("measure_type") or ""
                                facets = existing_meta.get("supported_facets") or set()
                            if not name:
                                master = self.store.get_master_indicator(ind_id)
                                if master and master.get("name"):
                                    name = str(master["name"])
                                else:
                                    name = f"Indicator {ind_id}"
                            self.store.store_indicator_metadata(
                                indicator_id=ind_id,
                                name=name,
                                concept=concept,
                                measure_type=measure_type,
                                unit=parsed_meta["unit"] or (existing_meta.get("unit", "") if existing_meta else ""),
                                supported_facets=facets,
                                definition=parsed_meta["definition"] or (existing_meta.get("definition", "") if existing_meta else ""),
                                periodicity=parsed_meta["periodicity"] or (existing_meta.get("periodicity", "") if existing_meta else ""),
                            )
                        except Exception as meta_exc:
                            logger.warning("Could not harvest metadata for indicator %s: %s", ind_id, meta_exc)

                    newly_harvested += 1
                    self._notify_progress(on_progress, idx, total_pending, ind_id, "success")
                    break
                except CepalStatAPIError as exc:
                    status_code = getattr(exc, "status_code", None)
                    is_transient = status_code is not None and (status_code >= 500 or status_code == 429)
                    if is_transient and attempt + 1 < max_attempts:
                        backoff = self.retry_backoff_base * (2**attempt)
                        time.sleep(backoff)
                        continue
                    failed_ids.append(ind_id)
                    self._notify_progress(on_progress, idx, total_pending, ind_id, "failed")
                    break
                except (CepalStatNetworkError, httpx.RequestError):
                    if attempt + 1 < max_attempts:
                        backoff = self.retry_backoff_base * (2**attempt)
                        time.sleep(backoff)
                        continue
                    failed_ids.append(ind_id)
                    self._notify_progress(on_progress, idx, total_pending, ind_id, "failed")
                    break
                except Exception:
                    failed_ids.append(ind_id)
                    self._notify_progress(on_progress, idx, total_pending, ind_id, "failed")
                    break

        duration = round(time.perf_counter() - start_time, 4)
        return HarvestSummary(
            total_target=len(target_ids),
            already_harvested=already_harvested,
            newly_harvested=newly_harvested,
            failed_ids=failed_ids,
            duration_seconds=duration,
        )

    @staticmethod
    def _matches_theme(theme_name: str, target_theme: str) -> bool:
        """Match theme names across English/Spanish and regional taxonomy variants."""
        norm_name = strip_accents(theme_name).lower()
        norm_target = strip_accents(target_theme).lower()
        if norm_target in norm_name or norm_name in norm_target:
            return True
        theme_aliases: dict[str, list[str]] = {
            "economic": ["econom", "actividad", "finan"],
            "economico": ["econom", "actividad", "finan"],
            "economicos": ["econom", "actividad", "finan"],
            "social": ["social", "demograf", "poblacion", "trabajo", "salud", "educacion"],
            "sociales": ["social", "demograf", "poblacion", "trabajo", "salud", "educacion"],
            "demographic": ["demograf", "poblacion"],
            "demografico": ["demograf", "poblacion"],
            "demograficos": ["demograf", "poblacion"],
            "environment": ["ambient", "medio ambiente", "recurso"],
            "ambiental": ["ambient", "medio ambiente", "recurso"],
            "ambientales": ["ambient", "medio ambiente", "recurso"],
            "transversal": ["transvers"],
            "transversales": ["transvers"],
        }
        aliases = theme_aliases.get(norm_target, [norm_target])
        return any(alias in norm_name for alias in aliases)

    def harvest_staging(
        self,
        theme_id: str,
        area_id: str | int | None = None,
        output_db: Path | str | None = None,
        output_dir: Path | str | None = None,
        on_progress: Callable[[int, int, int, str], None] | Callable[[int, int, int], None] | None = None,
        include_metadata: bool = True,
    ) -> HarvestSummary:
        """Harvest indicators for a thematic area into staging, preserving curated provenance and isolating synthetic members.

        Args:
            theme_id: Thematic area to harvest (e.g. 'economic', 'social', 'environment', 'demographic').
            area_id: Optional area name or ID filter.
            output_db: Optional path to output SQLite staging database. If None, uses self.store.
            output_dir: Optional path to write markdown draft recipes.
            on_progress: Optional callback invoked as (idx, total, indicator_id, status).
            include_metadata: Whether to fetch and persist unit, definition, periodicity.

        Returns:
            HarvestSummary with run statistics including inferred_count and curated_count.
        """
        start_time = time.perf_counter()

        if output_db is not None:
            target_store = CatalogStore(db_path=Path(output_db))
        else:
            target_store = self.store

        target_store.initialize_schema()

        # 1. Discover indicators from thematic tree API
        tree_indicators: list[dict[str, Any]] = []
        try:
            tree_obj = ThematicTree(self.client)
            raw_tree = tree_obj.get_raw_tree()
            if isinstance(raw_tree, dict):
                def traverse(node: dict[str, Any], path_parts: list[str]) -> None:
                    name = str(node.get("name", ""))
                    current_path = path_parts + [name] if name else path_parts
                    if "indicator_id" in node:
                        clean_path = [
                            p for p in path_parts
                            if "clasificación" not in p.lower() and "clasificacion" not in p.lower()
                        ]
                        theme = clean_path[0] if len(clean_path) > 0 else ""
                        area = clean_path[1] if len(clean_path) > 1 else ""
                        subarea = clean_path[2] if len(clean_path) > 2 else ""
                        if self._matches_theme(theme or name, theme_id):
                            tree_indicators.append({
                                "indicator_id": int(node["indicator_id"]),
                                "name": name,
                                "order_num": node.get("order") if node.get("order") is not None else node.get("order_num"),
                                "theme": theme,
                                "area": area,
                                "subarea": subarea,
                                "full_path": " > ".join(clean_path),
                            })
                    children = node.get("children")
                    if isinstance(children, list):
                        for child in children:
                            if isinstance(child, dict):
                                traverse(child, current_path)
                traverse(raw_tree, [])
        except Exception as tree_err:
            logger.debug("Tree traversal skipped or unavailable: %s", tree_err)

        # 2. Inspect target_store and self.store for indicators matching theme
        store_indicators: list[dict[str, Any]] = []
        stores_to_check = [target_store]
        if self.store is not target_store:
            stores_to_check.append(self.store)

        for s in stores_to_check:
            with s._get_connection() as conn:
                for tbl in ("master_indicators", "staging_indicators"):
                    try:
                        if tbl == "master_indicators":
                            query = (
                                "SELECT indicator_id, name, order_num, theme, area, subarea, "
                                "full_path, 'curated' AS provenance FROM master_indicators"
                            )
                        else:
                            query = (
                                "SELECT indicator_id, name, order_num, theme, area, subarea, "
                                "full_path, provenance FROM staging_indicators"
                            )
                        rows = conn.execute(query).fetchall()
                        for r in rows:
                            if self._matches_theme(r["theme"] or r["name"], theme_id):
                                store_indicators.append(dict(r))
                    except sqlite3.OperationalError:
                        pass

        # 3. Merge candidates (tree + store)
        candidate_map: dict[int, dict[str, Any]] = {}
        for item in tree_indicators:
            candidate_map[item["indicator_id"]] = item
        for item in store_indicators:
            ind_id = item["indicator_id"]
            if ind_id in candidate_map:
                if item.get("provenance") == "curated":
                    candidate_map[ind_id]["provenance"] = "curated"
            else:
                candidate_map[ind_id] = item

        # Apply area_id filter if provided
        target_candidates: list[dict[str, Any]] = []
        for cand in candidate_map.values():
            if area_id is not None:
                area_str = str(area_id).lower()
                c_area = str(cand.get("area") or "").lower()
                c_subarea = str(cand.get("subarea") or "").lower()
                c_order = str(cand.get("order_num") or "")
                if area_str not in c_area and area_str not in c_subarea and area_str != c_order:
                    continue
            target_candidates.append(cand)

        target_candidates.sort(key=lambda x: x["indicator_id"])

        total_target = len(target_candidates)
        newly_harvested = 0
        inferred_count = 0
        curated_count = 0
        failed_ids: list[int] = []
        max_attempts = max(1, self.max_retries)

        # 4. Process each candidate
        for idx, cand in enumerate(target_candidates, start=1):
            ind_id = cand["indicator_id"]
            ind_name = cand["name"]

            # Guard: check if existing indicator in either store has provenance='curated'
            existing_ind = target_store.get_indicator(ind_id)
            if existing_ind is None and self.store is not target_store:
                existing_ind = self.store.get_indicator(ind_id)

            is_curated = (
                (existing_ind is not None and existing_ind.provenance == "curated")
                or cand.get("provenance") == "curated"
            )

            # Process candidate: handle curated vs inferred
            if is_curated:
                curated_count += 1
                target_store.upsert_indicator(
                    indicator_id=ind_id,
                    name=ind_name,
                    provenance="curated",
                    order_num=cand.get("order_num"),
                    theme=cand.get("theme", ""),
                    area=cand.get("area", ""),
                    subarea=cand.get("subarea", ""),
                    full_path=cand.get("full_path", ""),
                    staging=True,
                )

                # For curated indicators: DO NOT overwrite dimensions or metadata in DB.
                # Only write staging markdown draft if output_dir is provided.
                if output_dir:
                    existing_meta = target_store.get_indicator_metadata(ind_id) or (
                        self.store.get_indicator_metadata(ind_id) if self.store is not target_store else None
                    ) or {}
                    existing_dims = target_store.get_indicator_dimensions(ind_id) or (
                        self.store.get_indicator_dimensions(ind_id) if self.store is not target_store else []
                    )
                    out_dir_path = Path(output_dir)
                    out_dir_path.mkdir(parents=True, exist_ok=True)
                    draft_file = out_dir_path / f"indicator_{ind_id}.md"
                    recipe_content = (
                        f"# Receta CEPALSTAT Indicador {ind_id}\n\n"
                        f"provenance: curated\n\n"
                        f"- **Nombre:** {ind_name}\n"
                        f"- **Tema:** {cand.get('theme', '')}\n"
                        f"- **Área:** {cand.get('area', '')}\n"
                        f"- **Unidad:** {existing_meta.get('unit', '')}\n"
                        f"- **Periodicidad:** {existing_meta.get('periodicity', '')}\n"
                        f"- **Provenance:** curated\n"
                        f"- **Dimensiones:** {len(existing_dims)}\n"
                    )
                    draft_file.write_text(recipe_content, encoding="utf-8")

                newly_harvested += 1
                self._notify_progress(on_progress, idx, total_target, ind_id, "success")
                continue

            # Inferred indicator: upsert into staging and harvest dimensions/metadata
            inferred_count += 1
            target_store.upsert_indicator(
                indicator_id=ind_id,
                name=ind_name,
                provenance="inferred",
                order_num=cand.get("order_num"),
                theme=cand.get("theme", ""),
                area=cand.get("area", ""),
                subarea=cand.get("subarea", ""),
                full_path=cand.get("full_path", ""),
                staging=True,
            )

            # Harvest dimensions and metadata
            harvest_success = False
            for attempt in range(max_attempts):
                if self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)
                try:
                    raw_response = self.client.get(f"/cepalstat/api/v1/indicator/{ind_id}/dimensions")
                    dimensions = self._parse_dimensions(raw_response)
                    content_hash = self.compute_content_hash(raw_response)
                    harvested_at = datetime.now(timezone.utc).isoformat()
                    target_store.store_indicator_dimensions(
                        indicator_id=ind_id,
                        dimensions=dimensions,
                        content_hash=content_hash,
                        harvested_at=harvested_at,
                        staging=True,
                    )

                    parsed_meta = {"unit": "", "definition": "", "periodicity": ""}
                    if include_metadata:
                        try:
                            if self.rate_limit_delay > 0:
                                time.sleep(self.rate_limit_delay)
                            raw_meta = self.client.get(f"/cepalstat/api/v1/indicator/{ind_id}/metadata")
                            parsed_meta = self._parse_metadata(raw_meta)
                            target_store.store_indicator_metadata(
                                indicator_id=ind_id,
                                name=ind_name,
                                concept="",
                                measure_type="",
                                unit=parsed_meta["unit"],
                                definition=parsed_meta["definition"],
                                periodicity=parsed_meta["periodicity"],
                            )
                        except Exception as meta_exc:
                            logger.debug("Could not harvest metadata for %s: %s", ind_id, meta_exc)

                    # Generate markdown recipe draft if output_dir provided
                    if output_dir:
                        out_dir_path = Path(output_dir)
                        out_dir_path.mkdir(parents=True, exist_ok=True)
                        draft_file = out_dir_path / f"indicator_{ind_id}.md"
                        recipe_content = (
                            f"# Receta CEPALSTAT Indicador {ind_id}\n\n"
                            f"provenance: inferred\n\n"
                            f"- **Nombre:** {ind_name}\n"
                            f"- **Tema:** {cand.get('theme', '')}\n"
                            f"- **Área:** {cand.get('area', '')}\n"
                            f"- **Unidad:** {parsed_meta.get('unit', '')}\n"
                            f"- **Periodicidad:** {parsed_meta.get('periodicity', '')}\n"
                            f"- **Provenance:** inferred\n"
                            f"- **Dimensiones:** {len(dimensions)}\n"
                        )
                        draft_file.write_text(recipe_content, encoding="utf-8")

                    newly_harvested += 1
                    harvest_success = True
                    self._notify_progress(on_progress, idx, total_target, ind_id, "success")
                    break
                except CepalStatAPIError as exc:
                    status_code = getattr(exc, "status_code", None)
                    is_transient = status_code is not None and (status_code >= 500 or status_code == 429)
                    if is_transient and attempt + 1 < max_attempts:
                        time.sleep(self.retry_backoff_base * (2**attempt))
                        continue
                    break
                except (CepalStatNetworkError, httpx.RequestError):
                    if attempt + 1 < max_attempts:
                        time.sleep(self.retry_backoff_base * (2**attempt))
                        continue
                    break
                except Exception:
                    break

            if not harvest_success:
                failed_ids.append(ind_id)
                self._notify_progress(on_progress, idx, total_target, ind_id, "failed")

        duration = round(time.perf_counter() - start_time, 4)
        return HarvestSummary(
            total_target=total_target,
            already_harvested=0,
            newly_harvested=newly_harvested,
            inferred_count=inferred_count,
            curated_count=curated_count,
            failed_ids=failed_ids,
            duration_seconds=duration,
        )
