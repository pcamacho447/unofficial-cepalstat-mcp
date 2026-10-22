"""Harvesting engine for CEPALSTAT indicator dimension metadata."""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from unofficial_cepalstat_mcp.catalog.models import HarvestSummary
from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.dimensions import Dimension, Member
from unofficial_cepalstat_mcp.exceptions import CepalStatAPIError, CepalStatNetworkError


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

    def harvest(
        self,
        indicator_ids: list[int] | None = None,
        resume: bool = True,
        force: bool = False,
        on_progress: Callable[[int, int, int, str], None] | Callable[[int, int, int], None] | None = None,
    ) -> HarvestSummary:
        """Harvest dimension metadata for indicators.

        Args:
            indicator_ids: Specific indicator IDs to harvest. If None, queries all master_indicators.
            resume: If True and not force, skips already harvested indicators.
            force: If True, re-harvests indicators even if already harvested.
            on_progress: Optional callback invoked as (idx, total, indicator_id, status).

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
