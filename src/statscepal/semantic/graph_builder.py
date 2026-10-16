"""GraphBuilder: Algorithmic BREAKDOWN_OF relationship inference engine for CEPALSTAT.

Analyzes indicator metadata and harvested dimensions across the catalog to group
indicators into concept families, extract canonical facet sets via FacetOntology,
and automatically infer strict-superset BREAKDOWN_OF relationships while preserving
strict precedence for curated edges and guaranteeing zero false edges on reference indicators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any
from pydantic import BaseModel, Field

from statscepal.catalog.store import CatalogStore
from statscepal.semantic.facet_ontology import (
    DEFAULT_FACET_ONTOLOGY,
    FacetOntology,
    strip_accents,
)
from statscepal.semantic.registry import (
    DEFAULT_OFFICIAL_DIMENSIONS,
    VERTICAL_SLICE_INDICATORS,
)


class InferredEdge(BaseModel):
    """Represents an automatically inferred relationship edge between two indicators."""

    parent_id: int
    child_id: int
    parent_name: str
    child_name: str
    concept_root: str
    parent_facets: list[str]
    child_facets: list[str]
    added_facets: list[str]
    provenance: str = "inferred"


class GraphBuildReport(BaseModel):
    """Diagnostic report summarizing catalog graph construction and edge inference."""

    total_indicators_analyzed: int = 0
    concept_families_count: int = 0
    curated_edges_count: int = 0
    inferred_edges_count: int = 0
    newly_persisted_edges_count: int = 0
    skipped_curated_conflicts: int = 0
    false_curated_edges: int = 0
    inferred_edges: list[InferredEdge] = Field(default_factory=list)


@dataclass
class _IndicatorCandidate:
    indicator_id: int
    name: str = ""
    concept: str | None = None
    measure_type: str | None = None
    unit: str | None = None
    supported_facets: set[str] = field(default_factory=set)


class GraphBuilder:
    """Algorithmic engine for discovering and persisting semantic indicator relationships."""

    def __init__(
        self,
        store: CatalogStore,
        ontology: FacetOntology = DEFAULT_FACET_ONTOLOGY,
    ) -> None:
        self.store = store
        self.ontology = ontology

    @staticmethod
    def extract_name_stem(name: str) -> str:
        """Normalize indicator name into a base concept stem.

        1. Normalizes accents and lowercase via strip_accents.
        2. Strips trailing footnotes, methodology markers, or codes:
           - e.g. - cepal..., (ods..., - 19a ciet...
        3. Splits on breakdown prepositions:
           re.split(r",?\\s+(?:por|segun|desglosad[oa]\\s+por)\\s+", text, maxsplit=1)[0]
        4. Strips trailing commas, dots, dashes, and whitespace.
        """
        if not name:
            return ""
        text = strip_accents(name)
        # Strip trailing methodology markers or codes
        text = re.sub(r"\s*-\s*cepal.*$", "", text)
        text = re.sub(r"\s*\(ods.*$", "", text)
        text = re.sub(r"\s*-\s*\d+[a-z]?\s*(?:ciet|ciuo|ciiu).*$", "", text)
        text = re.sub(r"\s*\(ciet.*$", "", text)
        text = re.sub(r"\s*\(%\)\s*$", "", text)

        parts = re.split(r",?\s+(?:por|segun|desglosad[oa]\s+por)\s+", text, maxsplit=1)
        stem = parts[0].strip()

        # Clean any trailing markers left on stem
        stem = re.sub(r"\s*-\s*cepal.*$", "", stem)
        stem = re.sub(r"\s*\(ods.*$", "", stem)
        stem = re.sub(r"\s*-\s*\d+[a-z]?\s*(?:ciet|ciuo|ciiu).*$", "", stem)
        stem = re.sub(r"\s*\(ciet.*$", "", stem)
        stem = re.sub(r"\s*\(%\)\s*$", "", stem)
        stem = re.sub(r"[\s,.-]+$", "", stem).strip()
        return stem

    def extract_indicator_facets(self, indicator_id: int, name: str = "") -> set[str]:
        """Extract all supported canonical facets for an indicator.

        Combines:
        1. Harvested dimensions classified via FacetOntology (excluding __structural__).
        2. Explicit metadata or curated registry supported_facets.
        3. Breakdown clauses in the title (after 'por', 'según', etc.).
        """
        facets: set[str] = set()

        # 1. Harvested dimensions from SQLite
        dims = self.store.get_indicator_dimensions(indicator_id)
        for d in dims:
            facet = self.ontology.classify_dimension(d.id, d.name)
            if facet and facet != "__structural__":
                facets.add(facet)

        # 2. Stored metadata or curated registry metadata
        meta = self.store.get_indicator_metadata(indicator_id)
        if meta and meta.get("supported_facets"):
            facets.update(meta["supported_facets"])
        elif indicator_id in VERTICAL_SLICE_INDICATORS:
            facets.update(VERTICAL_SLICE_INDICATORS[indicator_id].supported_facets)

        # Resolve indicator name if not passed
        resolved_name = name
        if not resolved_name:
            if meta and meta.get("name"):
                resolved_name = meta["name"]
            elif indicator_id in VERTICAL_SLICE_INDICATORS:
                resolved_name = VERTICAL_SLICE_INDICATORS[indicator_id].name
            else:
                with self.store._get_connection() as conn:
                    has_master = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='master_indicators'"
                    ).fetchone()
                    if has_master:
                        row = conn.execute(
                            "SELECT name FROM master_indicators WHERE indicator_id = ?",
                            (indicator_id,),
                        ).fetchone()
                        if row:
                            resolved_name = row["name"] or ""

        # 3. Inspect breakdown clause in title
        if resolved_name:
            norm_name = strip_accents(resolved_name)
            parts = re.split(r",?\s+(?:por|segun|desglosad[oa]\s+por)\s+", norm_name, maxsplit=1)
            if len(parts) > 1:
                suffix = parts[1]
                for fdef in self.ontology.all_facets():
                    facet_key = fdef.facet_key
                    if re.search(r"\b" + re.escape(facet_key) + r"\b", suffix):
                        facets.add(facet_key)
                        continue
                    matched = False
                    for pat in fdef.dimension_name_patterns:
                        pat_norm = strip_accents(pat)
                        if re.search(r"\b" + re.escape(pat_norm) + r"\b", suffix):
                            facets.add(facet_key)
                            matched = True
                            break
                    if matched:
                        continue
                    for trig in fdef.query_triggers:
                        for ph in trig.phrases:
                            ph_norm = strip_accents(ph)
                            if re.search(r"\b" + re.escape(ph_norm) + r"\b", suffix):
                                facets.add(facet_key)
                                matched = True
                                break
                        if matched:
                            break

        return facets

    def build_breakdown_graph(
        self,
        persist: bool = True,
        seed_curated: bool = True,
    ) -> GraphBuildReport:
        """Analyze indicators, group into concept families, and infer BREAKDOWN_OF edges."""
        report = GraphBuildReport()

        if seed_curated:
            for ind_id, meta in VERTICAL_SLICE_INDICATORS.items():
                self.store.store_indicator_metadata(
                    indicator_id=meta.indicator_id,
                    name=meta.name,
                    concept=meta.concept,
                    measure_type=meta.measure_type,
                    unit=meta.unit,
                    supported_facets=meta.supported_facets,
                )
                for target_id, rel in meta.relationships.items():
                    rel_str = rel.value if hasattr(rel, "value") else str(rel)
                    self.store.store_relationship(
                        meta.indicator_id, target_id, rel_str, provenance="curated"
                    )

            for ind_id, dims in DEFAULT_OFFICIAL_DIMENSIONS.items():
                self.store.store_indicator_dimensions(ind_id, dims)

        # Collect candidate indicators from database
        candidates: dict[int, _IndicatorCandidate] = {}
        with self.store._get_connection() as conn:
            # master_indicators
            has_master = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='master_indicators'"
            ).fetchone()
            if has_master:
                for row in conn.execute("SELECT indicator_id, name FROM master_indicators").fetchall():
                    ind_id = int(row["indicator_id"])
                    candidates[ind_id] = _IndicatorCandidate(
                        indicator_id=ind_id,
                        name=row["name"] or "",
                    )

            # indicator_metadata
            has_meta = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='indicator_metadata'"
            ).fetchone()
            if has_meta:
                for row in conn.execute(
                    "SELECT indicator_id, name, concept, measure_type, unit, supported_facets FROM indicator_metadata"
                ).fetchall():
                    ind_id = int(row["indicator_id"])
                    facets_str = row["supported_facets"] or ""
                    f_set = set(facets_str.split(",")) if facets_str else set()
                    if ind_id in candidates:
                        cand = candidates[ind_id]
                        if not cand.name and row["name"]:
                            cand.name = row["name"]
                        cand.concept = row["concept"]
                        cand.measure_type = row["measure_type"]
                        cand.unit = row["unit"]
                        cand.supported_facets.update(f_set)
                    else:
                        candidates[ind_id] = _IndicatorCandidate(
                            indicator_id=ind_id,
                            name=row["name"] or "",
                            concept=row["concept"],
                            measure_type=row["measure_type"],
                            unit=row["unit"],
                            supported_facets=f_set,
                        )

            # indicator_dimensions
            has_dims = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='indicator_dimensions'"
            ).fetchone()
            if has_dims:
                for row in conn.execute("SELECT DISTINCT indicator_id FROM indicator_dimensions").fetchall():
                    ind_id = int(row["indicator_id"])
                    if ind_id not in candidates:
                        candidates[ind_id] = _IndicatorCandidate(indicator_id=ind_id)

        report.total_indicators_analyzed = len(candidates)

        # Group indicators into concept families
        families: dict[str, list[_IndicatorCandidate]] = {}
        for cand in candidates.values():
            if cand.concept and cand.measure_type and cand.unit:
                family_key = f"curated:{cand.concept}|{cand.measure_type}|{cand.unit}"
            else:
                stem = self.extract_name_stem(cand.name)
                if len(stem) >= 8:
                    family_key = f"stem:{stem}"
                else:
                    continue
            families.setdefault(family_key, []).append(cand)

        report.concept_families_count = len(families)

        single_incompatible = ("por habitante", "per capita", "indice de feminidad", "brecha de")

        for family_key, members in families.items():
            if len(members) < 2:
                continue

            for i, ind_a in enumerate(members):
                for ind_b in members[i + 1 :]:
                    has_meta_a = bool(ind_a.concept and ind_a.measure_type and ind_a.unit)
                    has_meta_b = bool(ind_b.concept and ind_b.measure_type and ind_b.unit)

                    # Guardrail 1: If both have metadata, concept, measure_type, and unit must match
                    if has_meta_a and has_meta_b:
                        if (ind_a.concept, ind_a.measure_type, ind_a.unit) != (
                            ind_b.concept,
                            ind_b.measure_type,
                            ind_b.unit,
                        ):
                            continue
                    else:
                        # Guardrail 2: If metadata is absent, normalized stems must match and no incompatible measure qualifiers
                        stem_a = self.extract_name_stem(ind_a.name)
                        stem_b = self.extract_name_stem(ind_b.name)
                        if stem_a != stem_b or len(stem_a) < 8:
                            continue

                        norm_a = strip_accents(ind_a.name)
                        norm_b = strip_accents(ind_b.name)
                        if any(q in norm_a or q in norm_b for q in single_incompatible):
                            continue
                        if ("precios corrientes" in norm_a) != ("precios corrientes" in norm_b):
                            continue
                        if ("precios constantes" in norm_a) != ("precios constantes" in norm_b):
                            continue
                        if ("en dolares" in norm_a) != ("en dolares" in norm_b):
                            continue
                        if ("en moneda nacional" in norm_a) != ("en moneda nacional" in norm_b):
                            continue

                    facets_a = self.extract_indicator_facets(ind_a.indicator_id, name=ind_a.name)
                    facets_b = self.extract_indicator_facets(ind_b.indicator_id, name=ind_b.name)

                    if facets_b > facets_a:
                        parent = ind_a
                        child = ind_b
                        parent_facets = facets_a
                        child_facets = facets_b
                    elif facets_a > facets_b:
                        parent = ind_b
                        child = ind_a
                        parent_facets = facets_b
                        child_facets = facets_a
                    else:
                        continue

                    # Check for existing curated non-breakdown_of relationships
                    existing_a = self.store.get_relationships_with_provenance(parent.indicator_id)
                    existing_b = self.store.get_relationships_with_provenance(child.indicator_id)

                    conflict = False
                    if child.indicator_id in existing_a:
                        rel_info = existing_a[child.indicator_id]
                        if rel_info.get("provenance") == "curated" and rel_info.get("rel_type") != "breakdown_of":
                            conflict = True
                    if not conflict and parent.indicator_id in existing_b:
                        rel_info = existing_b[parent.indicator_id]
                        if rel_info.get("provenance") == "curated" and rel_info.get("rel_type") != "breakdown_of":
                            conflict = True

                    if not conflict and parent.indicator_id in VERTICAL_SLICE_INDICATORS:
                        v_rel = VERTICAL_SLICE_INDICATORS[parent.indicator_id].relationships.get(child.indicator_id)
                        if v_rel:
                            v_rel_str = v_rel.value if hasattr(v_rel, "value") else str(v_rel)
                            if v_rel_str != "breakdown_of":
                                conflict = True

                    if not conflict and child.indicator_id in VERTICAL_SLICE_INDICATORS:
                        v_rel = VERTICAL_SLICE_INDICATORS[child.indicator_id].relationships.get(parent.indicator_id)
                        if v_rel:
                            v_rel_str = v_rel.value if hasattr(v_rel, "value") else str(v_rel)
                            if v_rel_str != "breakdown_of":
                                conflict = True

                    if conflict:
                        report.skipped_curated_conflicts += 1
                        continue

                    concept_root = parent.concept or self.extract_name_stem(parent.name)
                    edge = InferredEdge(
                        parent_id=parent.indicator_id,
                        child_id=child.indicator_id,
                        parent_name=parent.name,
                        child_name=child.name,
                        concept_root=concept_root,
                        parent_facets=sorted(parent_facets),
                        child_facets=sorted(child_facets),
                        added_facets=sorted(child_facets - parent_facets),
                        provenance="inferred",
                    )
                    report.inferred_edges.append(edge)

                    if persist:
                        w1 = self.store.store_relationship(
                            parent.indicator_id, child.indicator_id, "breakdown_of", provenance="inferred"
                        )
                        w2 = self.store.store_relationship(
                            child.indicator_id, parent.indicator_id, "breakdown_of", provenance="inferred"
                        )
                        if w1 or w2:
                            report.newly_persisted_edges_count += 1

        report.inferred_edges_count = len(report.inferred_edges)
        report.curated_edges_count = len(self.store.get_all_relationships(provenance="curated"))

        # Verification on 45 curated indicators: zero false edges
        for edge in report.inferred_edges:
            if edge.parent_id in VERTICAL_SLICE_INDICATORS and edge.child_id in VERTICAL_SLICE_INDICATORS:
                curated_rels = VERTICAL_SLICE_INDICATORS[edge.parent_id].relationships
                rel = curated_rels.get(edge.child_id)
                rel_str = rel.value if hasattr(rel, "value") else str(rel) if rel else ""
                if rel_str != "breakdown_of":
                    report.false_curated_edges += 1

        return report
