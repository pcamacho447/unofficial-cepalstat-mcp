"""Command Line Interface for CEPALSTAT."""

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

import pandas as pd

from unofficial_cepalstat_mcp.analysis import DecouplingAnalyzer
from unofficial_cepalstat_mcp.bitacora import AntiBiasValidator, BitacoraRecipe, BitacoraStore
from unofficial_cepalstat_mcp.catalog import CatalogStore
from unofficial_cepalstat_mcp.catalog.harvester import CatalogHarvester
from unofficial_cepalstat_mcp.client import CepalStatClient
from unofficial_cepalstat_mcp.exceptions import CepalStatError
from unofficial_cepalstat_mcp.extractor import DataExtractor
from unofficial_cepalstat_mcp.semantic import (
    GraphBuilder,
    SemanticDataFetcher,
    SemanticRegistry,
    SemanticResolutionEngine,
)
from unofficial_cepalstat_mcp.semantic.facet_ontology import DEFAULT_FACET_ONTOLOGY
from unofficial_cepalstat_mcp.thematic_tree import ThematicTree


def _handle_catalog_build_graph(args: argparse.Namespace) -> int:
    """Handle the 'catalog build-graph' command."""
    store = CatalogStore()
    builder = GraphBuilder(store=store)
    report = builder.build_breakdown_graph(
        persist=not args.no_persist,
        seed_curated=not args.no_seed_curated,
    )

    if args.json:
        print(report.model_dump_json(indent=2))
        return 0

    print("=" * 70)
    print("CEPALSTAT Breakdown Graph Builder")
    print("=" * 70)
    print(f"Total indicators analyzed:    {report.total_indicators_analyzed}")
    print(f"Concept families discovered:  {report.concept_families_count}")
    print(f"Curated relationships:        {report.curated_edges_count}")
    print(f"Inferred BREAKDOWN_OF pairs:  {report.inferred_edges_count}")
    print(f"Newly persisted edges:        {report.newly_persisted_edges_count}")
    print(f"Skipped curated conflicts:    {report.skipped_curated_conflicts}")
    print(f"False curated edges:          {report.false_curated_edges}")
    print("=" * 70)
    print("Sample inferred edges:")
    if not report.inferred_edges:
        print("  (None)")
    else:
        for edge in report.inferred_edges[:10]:
            added_str = f" (+{', '.join(edge.added_facets)})" if edge.added_facets else ""
            print(f"  [{edge.parent_id}] -> [{edge.child_id}] {edge.concept_root}{added_str}")
        if len(report.inferred_edges) > 10:
            print(f"  ... and {len(report.inferred_edges) - 10} more.")
    print("=" * 70)
    return 0


def _resolve_prog(prog: str | None = None) -> str:
    """Determine the CLI program name dynamically based on invoked binary or explicit argument."""
    if prog:
        return prog
    if sys.argv and sys.argv[0]:
        stem = Path(sys.argv[0]).stem.lower()
        if stem in ("unofficial-cepalstat-mcp", "cepalstat-mcp", "statscepal"):
            return stem
    return "unofficial-cepalstat-mcp"


def main(args: Sequence[str] | None = None, prog: str | None = None) -> int:
    """Run the CEPALSTAT CLI command.

    Args:
        args: Optional list of command-line arguments. If None, sys.argv[1:] is used.
        prog: Optional program name override for help and usage output.

    Returns:
        Exit code: 0 for success, non-zero for errors.
    """
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    resolved_prog = _resolve_prog(prog)
    parser = argparse.ArgumentParser(
        prog=resolved_prog,
        description="CEPALSTAT Open Data CLI tool for Latin America and Caribbean statistics.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # search
    search_parser = subparsers.add_parser("search", help="Search indicators by keyword")
    search_parser.add_argument("query", help="Keyword to search for")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results to display")

    # info
    info_parser = subparsers.add_parser("info", help="Get metadata of an indicator")
    info_parser.add_argument("indicator_id", type=int, help="Indicator ID")

    # fetch
    fetch_parser = subparsers.add_parser("fetch", help="Fetch records and output as table or CSV")
    fetch_parser.add_argument("indicator_id", type=int, help="Indicator ID")
    fetch_parser.add_argument("--members", help="Comma-separated member IDs")
    fetch_parser.add_argument("--csv", help="Save output to CSV file")

    # bitacora
    bitacora_parser = subparsers.add_parser(
        "bitacora", help="Manage and query certified Bitácora recipes"
    )
    bitacora_subparsers = bitacora_parser.add_subparsers(
        dest="bitacora_command", help="Bitácora action to execute"
    )

    # bitacora lookup
    lookup_parser = bitacora_subparsers.add_parser(
        "lookup", help="Search recipes by query, country, or tag"
    )
    lookup_parser.add_argument("query", nargs="?", default="", help="Search query")
    lookup_parser.add_argument("--country", help="Filter by country or ISO3")
    lookup_parser.add_argument("--tag", help="Filter by tag")

    # bitacora list
    bitacora_subparsers.add_parser("list", help="List all certified recipes")

    # bitacora sync
    bitacora_subparsers.add_parser("sync", help="Rebuild the SQLite index from markdown files")

    # bitacora add
    add_parser = bitacora_subparsers.add_parser(
        "add", help="Add and certify a new recipe for an indicator"
    )
    add_parser.add_argument("indicator_id", type=int, help="Indicator ID")
    add_parser.add_argument("--country", required=True, help="Country name or ISO3")
    add_parser.add_argument("--members", help="Comma-separated member IDs")
    add_parser.add_argument("--tags", help="Comma-separated tags")
    add_parser.add_argument("--id", help="Optional custom recipe ID")

    # catalog
    catalog_parser = subparsers.add_parser(
        "catalog", help="Manage and query the master indicator catalog"
    )
    catalog_subparsers = catalog_parser.add_subparsers(
        dest="catalog_command", help="Catalog action to execute"
    )

    # catalog build
    build_parser = catalog_subparsers.add_parser(
        "build", help="Build or update the master indicator catalog from CEPALSTAT"
    )
    build_parser.add_argument(
        "--force", action="store_true", help="Force rebuild from remote thematic tree"
    )

    # catalog stats
    catalog_subparsers.add_parser("stats", help="Display catalog summary statistics")

    # catalog search
    search_cat_parser = catalog_subparsers.add_parser(
        "search", help="Search indicators in the master catalog"
    )
    search_cat_parser.add_argument("query", nargs="?", default="", help="Search query")
    search_cat_parser.add_argument("--theme", help="Filter by thematic area")
    search_cat_parser.add_argument(
        "--limit", type=int, default=20, help="Max results to display (default: 20)"
    )

    # catalog export
    export_parser = catalog_subparsers.add_parser(
        "export", help="Export the catalog to JSON or CSV"
    )
    export_parser.add_argument("filepath", help="Output file path (.json or .csv)")
    export_parser.add_argument(
        "--format", choices=["json", "csv"], default=None, help="Export format (json or csv)"
    )

    # catalog harvest
    harvest_parser = catalog_subparsers.add_parser(
        "harvest", help="Harvest dimension metadata for catalog indicators"
    )
    harvest_parser.add_argument(
        "--ids", help="Comma-separated list of indicator IDs (e.g. 3328,3342)"
    )
    harvest_parser.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        default=True,
        help="Disable resumption and process all targets",
    )
    harvest_parser.add_argument(
        "--resume",
        action="store_true",
        dest="resume",
        default=True,
        help="Resume from last harvested indicator (default: True)",
    )
    harvest_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-harvesting of all targets even if already harvested",
    )
    harvest_parser.add_argument(
        "--rate",
        type=float,
        default=0.05,
        help="Inter-request rate limit delay in seconds (default: 0.05)",
    )
    harvest_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of pending indicators to process in this run",
    )

    # catalog facet-audit
    facet_audit_parser = catalog_subparsers.add_parser(
        "facet-audit", help="Audit harvested dimensions against declarative facet ontology"
    )
    facet_audit_parser.add_argument(
        "--json", action="store_true", help="Output audit report in JSON format"
    )

    # catalog build-graph
    build_graph_parser = catalog_subparsers.add_parser(
        "build-graph",
        help="Infer and persist multidimensional BREAKDOWN_OF relationships across the catalog",
        description="Analyzes indicators, groups into concept families, infers strict-superset breakdowns, and persists edges to SQLite.",
    )
    build_graph_parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Dry-run mode: do not write inferred edges to SQLite",
    )
    build_graph_parser.add_argument(
        "--no-seed-curated",
        action="store_true",
        help="Do not seed curated vertical slice edges prior to inference",
    )
    build_graph_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit report as JSON to stdout",
    )

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analytical workflows")
    analyze_subparsers = analyze_parser.add_subparsers(
        dest="analyze_command", help="Analysis action"
    )

    # analyze desacople
    desacople_parser = analyze_subparsers.add_parser(
        "desacople", help="Run Growth vs Wellbeing Decoupling analysis"
    )
    desacople_parser.add_argument(
        "--countries",
        default="Argentina,Chile,Colombia,México,Perú,Uruguay",
        help="Comma-separated list of countries (default: Argentina,Chile,Colombia,México,Perú,Uruguay)",
    )
    desacople_parser.add_argument(
        "--output",
        help="Optional path to export results as CSV",
    )
    desacople_parser.add_argument(
        "--econometrics",
        action="store_true",
        help="Run and display OLS multivariate regression summary",
    )

    # semantic
    semantic_parser = subparsers.add_parser(
        "semantic", help="CEPALSTAT Semantic Intent Disambiguation Engine diagnostics"
    )
    semantic_subparsers = semantic_parser.add_subparsers(
        dest="semantic_command", help="Semantic action to execute"
    )

    # semantic resolve
    resolve_parser = semantic_subparsers.add_parser(
        "resolve", help="Resolve natural language statistical query"
    )
    resolve_parser.add_argument("query", help="Statistical query to resolve")
    resolve_parser.add_argument(
        "--fetch",
        action="store_true",
        default=False,
        help="Fetch empirical observation from CEPALSTAT",
    )
    resolve_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output full SemanticResolutionResponse as JSON",
    )
    resolve_parser.add_argument(
        "--explain",
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Display step-by-step reasoning trace and decision audit logs",
    )

    try:
        parsed = parser.parse_args(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0

    if not parsed.command:
        parser.print_help()
        return 0

    if parsed.command == "analyze":
        if not parsed.analyze_command:
            analyze_parser.print_help()
            return 0

    if parsed.command == "bitacora":
        if not parsed.bitacora_command:
            bitacora_parser.print_help()
            return 0

        store = BitacoraStore()

        if parsed.bitacora_command == "list":
            recipes = store.list_recipes()
            if not recipes:
                print("No certified recipes found in Bitácora.")
                return 0
            print(f"Certified recipes ({len(recipes)}):")
            for r in recipes:
                tags_str = f" [tags: {', '.join(r.tags)}]" if r.tags else ""
                print(f"  [{r.id}] {r.indicator_name} - {r.country} (Indicator {r.indicator_id}){tags_str}")
            return 0

        if parsed.bitacora_command == "lookup":
            recipes = store.lookup(
                query=parsed.query,
                country=parsed.country,
                tag=parsed.tag,
            )
            if not recipes:
                print("No recipes found matching query.")
                return 0
            print(f"Found {len(recipes)} recipes:")
            for r in recipes:
                tags_str = f" [tags: {', '.join(r.tags)}]" if r.tags else ""
                print(f"  [{r.id}] {r.indicator_name} - {r.country} (Indicator {r.indicator_id}){tags_str}")
            return 0

        if parsed.bitacora_command == "sync":
            count = store.sync()
            print(f"Bitácora index synchronized. {count} recipes indexed.")
            return 0

        if parsed.bitacora_command == "add":
            member_ids: list[int] | None = None
            if parsed.members:
                try:
                    member_ids = [
                        int(m.strip()) for m in parsed.members.split(",") if m.strip()
                    ]
                except ValueError:
                    print(
                        f"Error: Invalid member IDs '{parsed.members}'. Must be comma-separated integers.",
                        file=sys.stderr,
                    )
                    return 1

            tags = (
                [t.strip() for t in parsed.tags.split(",") if t.strip()]
                if parsed.tags
                else []
            )

            try:
                with CepalStatClient() as client:
                    extractor = DataExtractor(client)
                    meta = extractor.get_metadata(parsed.indicator_id)
                    if not meta:
                        print(f"Indicator {parsed.indicator_id} not found.", file=sys.stderr)
                        return 1

                    df = extractor.get_dataframe(
                        parsed.indicator_id, members=member_ids, decode_labels=True
                    )

                    quality, antibias = AntiBiasValidator.audit(df, metadata=meta)

                    country_slug = re.sub(
                        r"[^a-zA-Z0-9]+", "-", parsed.country.strip().lower()
                    ).strip("-")
                    recipe_id = parsed.id or f"recipe-{country_slug}-{parsed.indicator_id}"

                    members_code = f", members={member_ids}" if member_ids else ""
                    python_code = (
                        f"from unofficial_cepalstat_mcp import CepalStatClient, DataExtractor\n\n"
                        f"with CepalStatClient() as client:\n"
                        f"    extractor = DataExtractor(client)\n"
                        f"    df = extractor.get_dataframe({parsed.indicator_id}{members_code}, decode_labels=True)"
                    )

                    recipe = BitacoraRecipe(
                        id=recipe_id,
                        indicator_id=parsed.indicator_id,
                        indicator_name=meta.get(
                            "indicator_name", f"Indicator {parsed.indicator_id}"
                        ),
                        country=parsed.country,
                        country_iso3=parsed.country.upper() if len(parsed.country) == 3 else "",
                        theme=meta.get("area", ""),
                        unit=meta.get("unit", ""),
                        member_ids=member_ids or [],
                        python_code=python_code,
                        status="certified",
                        date_certified=date.today().isoformat(),
                        tags=tags,
                        quality_report=quality,
                        antibias=antibias,
                    )

                    saved_path = store.save_recipe(recipe)
                    print(f"Certified recipe saved to {saved_path} (ID: {recipe.id})")
                    if antibias.warnings:
                        print(f"Warnings ({len(antibias.warnings)}):")
                        for w in antibias.warnings:
                            print(f"  - {w}")
                    return 0
            except CepalStatError as err:
                print(f"CEPALSTAT Error: {err}", file=sys.stderr)
                return 1

    if parsed.command == "catalog":
        if not parsed.catalog_command:
            catalog_parser.print_help()
            return 0

        store = CatalogStore()

        if parsed.catalog_command == "build":
            try:
                count = store.build(force=parsed.force)
                print(f"Catalog built successfully with {count} indicators.")
                return 0
            except CepalStatError as err:
                print(f"CEPALSTAT Error: {err}", file=sys.stderr)
                return 1

        if parsed.catalog_command == "stats":
            stats = store.get_stats()
            print("=== Master Indicator Catalog Statistics ===")
            print(f"Total indicators: {stats.total_indicators}")
            print(f"Thematic areas: {stats.themes_count}")
            print(f"Areas: {stats.areas_count}")
            if stats.by_theme:
                print("Indicators by theme:")
                for theme, count in stats.by_theme.items():
                    print(f"  - {theme}: {count}")
            return 0

        if parsed.catalog_command == "search":
            results = store.search(
                query=parsed.query,
                theme=parsed.theme,
                limit=parsed.limit,
            )
            if not results:
                print(f"No indicators found matching '{parsed.query}'.")
                return 0
            print(f"Found {len(results)} indicators:")
            for item in results:
                print(f"  [{item.indicator_id}] {item.name}")
                if item.full_path:
                    print(f"      Path: {item.full_path}")
            return 0

        if parsed.catalog_command == "export":
            filepath = parsed.filepath
            format_to_use = parsed.format
            if not format_to_use:
                ext = Path(filepath).suffix.lower()
                format_to_use = "csv" if ext == ".csv" else "json"

            out_path = store.export(filepath, format=format_to_use)
            print(f"Catalog exported successfully to {out_path} (format: {format_to_use}).")
            return 0

        if parsed.catalog_command == "harvest":
            store.init_semantic_tables()
            client = CepalStatClient()
            harvester = CatalogHarvester(
                client=client,
                store=store,
                rate_limit_delay=parsed.rate,
            )

            target_ids: list[int] | None = None
            if parsed.ids:
                try:
                    target_ids = [int(x.strip()) for x in parsed.ids.split(",") if x.strip()]
                except ValueError:
                    print(
                        f"Error: Invalid --ids value '{parsed.ids}'. Expected comma-separated integers.",
                        file=sys.stderr,
                    )
                    return 1

            if target_ids is None and parsed.limit is not None:
                with store._get_connection() as conn:
                    rows = conn.execute(
                        "SELECT indicator_id FROM master_indicators ORDER BY indicator_id ASC"
                    ).fetchall()
                    all_ids = [int(r["indicator_id"]) for r in rows]
                if parsed.resume and not parsed.force:
                    harvested = store.get_harvested_indicator_ids()
                    pending = [i for i in all_ids if i not in harvested]
                    target_ids = pending[:parsed.limit]
                else:
                    target_ids = all_ids[:parsed.limit]
            elif target_ids is not None and parsed.limit is not None:
                target_ids = target_ids[:parsed.limit]

            if parsed.ids:
                target_desc = f"{len(target_ids)} indicator(s) [{parsed.ids}]"
            elif target_ids is not None and parsed.limit is not None:
                target_desc = f"{len(target_ids)} indicator(s) (limit: {parsed.limit})"
            else:
                target_desc = "All catalog indicators"

            mode_desc = (
                "Force re-harvest"
                if parsed.force
                else ("Resume (skip harvested)" if parsed.resume else "Full (no resume)")
            )

            print("=" * 70)
            print("CEPALSTAT Dimension Metadata Harvester")
            print("=" * 70)
            print(f"Target: {target_desc}")
            print(f"Mode:   {mode_desc}")
            print("=" * 70)

            def on_progress(idx: int, total: int, ind_id: int, status: str) -> None:
                print(f"[Harvesting] ({idx}/{total}) Indicator ID: {ind_id} - {status}")

            try:
                summary = harvester.harvest(
                    indicator_ids=target_ids,
                    resume=parsed.resume,
                    force=parsed.force,
                    on_progress=on_progress,
                )

                print("=" * 70)
                print("Catalog Harvest Complete")
                print("=" * 70)
                print(f"Total target:      {summary.total_target}")
                print(f"Already harvested: {summary.already_harvested}")
                print(f"Newly harvested:   {summary.newly_harvested}")
                print(f"Failed:            {summary.failed_count}")
                print(f"Duration:          {summary.duration_seconds:.2f}s")
                print("=" * 70)
                if summary.failed_ids:
                    print(f"Failed indicator IDs: {summary.failed_ids}")

                return 0
            except Exception as err:
                print(f"CEPALSTAT Error during harvest: {err}", file=sys.stderr)
                return 1

        if parsed.catalog_command == "facet-audit":
            ontology = DEFAULT_FACET_ONTOLOGY
            store.init_semantic_tables()
            distinct_dims = store.get_distinct_harvested_dimensions()
            report = ontology.audit_dimensions(distinct_dims)

            if parsed.json:
                print(report.model_dump_json(indent=2))
                return 0

            print("=" * 70)
            print("CEPALSTAT Facet Ontology Audit")
            print("=" * 70)
            print(f"Total distinct dimensions: {report.total_distinct_dimensions}")
            print(f"Structural dimensions:     {len(report.structural_dimensions)} (Country, Time)")
            print(f"Mapped facet dimensions:   {report.mapped_count}")
            print(f"Unmapped dimensions:       {len(report.unmapped_dimensions)}")
            print(f"Coverage ratio:            {report.coverage_ratio * 100:.1f}%")
            print("=" * 70)
            print("Mapped Dimensions by Facet:")
            if not report.mapped_dimensions:
                print("  (None)")
            else:
                for f_key in sorted(report.mapped_dimensions.keys()):
                    dims = report.mapped_dimensions[f_key]
                    dim_desc = ", ".join(f"[{d['dim_id']}] {d.get('dim_name', '')}" for d in dims)
                    print(f"  - [{f_key}]: {len(dims)} dimension(s) ({dim_desc})")
            print("=" * 70)
            print("Unmapped Dimensions (Gap Report):")
            if not report.unmapped_dimensions:
                print("  (None)")
            else:
                for d in report.unmapped_dimensions:
                    print(
                        f"  - [{d['dim_id']}] {d.get('dim_name', '')} (occurs in {d.get('indicator_count', 0)} indicators)"
                    )
            print("=" * 70)
            return 0

        if parsed.catalog_command == "build-graph":
            return _handle_catalog_build_graph(parsed)

    if parsed.command == "semantic":
        if not parsed.semantic_command:
            semantic_parser.print_help()
            return 0

        if parsed.semantic_command == "resolve":
            store = CatalogStore()
            registry = SemanticRegistry(store=store)
            engine = SemanticResolutionEngine(registry=registry)

            try:
                res = engine.resolve_query(parsed.query)

                if parsed.fetch:
                    fetcher = SemanticDataFetcher()
                    emp_data = fetcher.fetch_resolved_data(res)
                    if emp_data and not res.empirical_data:
                        res.empirical_data = emp_data


                if parsed.json:
                    print(res.model_dump_json(indent=2))
                    return 0

                print("=" * 70)
                print("CEPALSTAT Semantic Resolution Engine")
                print("=" * 70)
                print(f"Query:     {res.query}")
                print(f"Status:    {res.status.value}")

                if res.selected_candidate:
                    sc = res.selected_candidate
                    print(
                        f"Indicator: {sc.indicator_id} - {sc.name} (Measure: {sc.measure_type}, Unit: {sc.unit})"
                    )
                    print(f"Score:     {sc.relevance_score}")
                else:
                    if res.abstention_reason:
                        print(f"Reason:    {res.abstention_reason}")

                if res.conversational_hint:
                    print(f"Hint:      {res.conversational_hint}")

                if res.polarity_info:
                    print(
                        f"Polarity:  {res.polarity_info.polarity_type.value} (Detected: '{res.polarity_info.term_detected}', Expected Sign: {res.polarity_info.expected_sign.value})"
                    )

                if res.temporal_info:
                    ti = res.temporal_info
                    prev_str = (
                        ti.previous_anchor_year
                        if ti.previous_anchor_year is not None
                        else "None"
                    )
                    next_str = (
                        ti.next_anchor_year
                        if ti.next_anchor_year is not None
                        else "None"
                    )
                    if getattr(ti, "requested_countries", None) and len(ti.requested_countries) > 1:
                        if ti.unobserved_countries:
                            unobs_fmt = []
                            for c in ti.unobserved_countries:
                                if getattr(ti, "country_anchors", None) and c in ti.country_anchors:
                                    ca = ti.country_anchors[c]
                                    unobs_fmt.append(f"{c} (Prev={ca.previous_anchor_year}, Next={ca.next_anchor_year})")
                                else:
                                    unobs_fmt.append(str(c))
                            print(
                                f"Temporal:  {ti.temporal_status.value} (Observed Countries: {ti.observed_countries}, Unobserved: [{', '.join(unobs_fmt)}])"
                            )
                        else:
                            print(
                                f"Temporal:  {ti.temporal_status.value} (Observed Countries: {ti.observed_countries}, Unobserved: [])"
                            )
                    elif getattr(ti, "requested_years", None) and len(ti.requested_years) > 1:
                        print(
                            f"Temporal:  {ti.temporal_status.value} (Observed: {ti.observed_years}, Unobserved: {ti.unobserved_years})"
                        )
                    else:
                        print(
                            f"Temporal:  {ti.temporal_status.value} (Anchors: Prev={prev_str}, Next={next_str})"
                        )
                    if ti.disclaimer:
                        print(f"Notice:    {ti.disclaimer}")
                else:
                    print("Temporal:  N/A")

                af = res.applied_filters
                if getattr(af, "country_codes", None) and len(af.country_codes) > 1:
                    countries_str = ", ".join(
                        f"{n} ({c})" for n, c in zip(af.country_names, af.country_codes)
                    )
                    print(f"Country:   {countries_str}")
                else:
                    country_name = af.country_name or "N/A"
                    country_code = af.country_code or "N/A"
                    print(f"Country:   {country_name} ({country_code})")
                if af.time_mode == "RANGE" and len(af.years) > 1:
                    years_csv = ", ".join(str(y) for y in af.years)
                    print(f"Year:      {af.years[0]}-{af.years[-1]} [{years_csv}] (Mode: RANGE)")
                elif af.time_mode == "LIST" and len(af.years) > 1:
                    years_csv = ", ".join(str(y) for y in af.years)
                    print(f"Year:      [{years_csv}] (Mode: LIST)")
                elif af.time_mode == "RELATIVE_WINDOW" and af.relative_window_size:
                    print(f"Year:      Últimos {af.relative_window_size} años (Mode: RELATIVE_WINDOW)")
                else:
                    print(f"Year:      {af.year or 'N/A'}")

                facets_str = (
                    ", ".join(f"{k}={v}" for k, v in res.applied_filters.facets.items())
                    if res.applied_filters.facets
                    else "None"
                )
                print(f"Facets:    {facets_str}")

                if res.applied_filters.dimensions:
                    dim_parts = []
                    for d in res.applied_filters.dimensions:
                        if getattr(d, "is_breakdown", False) and getattr(d, "member_names", None):
                            members_fmt = ", ".join(
                                f"{n} (ID: {i})" for n, i in zip(d.member_names, d.member_ids)
                            )
                            dim_parts.append(f"{d.dim_name}=[{members_fmt}] (Desglose)")
                        elif d.member_id is not None:
                            dim_parts.append(
                                f"{d.dim_name}={d.member_name} (ID: {d.member_id})"
                            )
                        else:
                            dim_parts.append(f"{d.dim_name}={d.member_name}")
                    filters_str = ", ".join(dim_parts)
                else:
                    filters_str = "None"
                print(f"Filters:   {filters_str}")

                if res.alternatives:
                    print("Alternatives:")
                    for alt in res.alternatives:
                        print(
                            f"  - [{alt.indicator_id}] {alt.name} ({alt.relationship.value})"
                        )

                if parsed.fetch:
                    print("-" * 70)
                    emp = res.empirical_data or {}
                    if (
                        emp.get("empirical_indicator_id")
                        and res.selected_candidate
                        and emp.get("empirical_indicator_id") != res.selected_candidate.indicator_id
                    ):
                        print(f"CEPALSTAT API Table ID: {emp['empirical_indicator_id']}")
                    series = emp.get("series")
                    if series:
                        print(f"Empirical Series ({len(series)} observations):")
                        has_country_col = any(item.get("country") for item in series)
                        has_member_col = any(item.get("member") for item in series)
                        if has_country_col and has_member_col:
                            print(f"  {'Country':<14} {'Year':<8} {'Member / Group':<28} {'Value':<12} {'Unit'}")
                            print(f"  {'-'*12} {'-'*6} {'-'*26} {'-'*10} {'-'*20}")
                            for item in series:
                                val_str = (
                                    f"{item['value']:g}"
                                    if isinstance(item["value"], (int, float))
                                    else str(item["value"])
                                )
                                c_str = str(item.get("country", ""))[:12]
                                member_str = str(item.get("member", ""))[:26]
                                year_val = item.get("year", "")
                                year_str = f"{year_val}*" if item.get("is_anchor") else str(year_val)
                                notes_val = str(item.get("notes", "")).strip() if item.get("notes") else ""
                                if item.get("is_anchor") and "[Ancla" not in notes_val:
                                    notes_val = f"{notes_val} [Ancla]".strip()
                                unit_val = str(item.get("unit", "")).strip() if item.get("unit") else ""
                                desc_str = f"{unit_val}  {notes_val}".strip() if notes_val else unit_val
                                print(
                                    f"  {c_str:<14} {year_str:<8} {member_str:<28} {val_str:<12} {desc_str}"
                                )
                        elif has_country_col:
                            print(f"  {'Country':<16} {'Year':<8} {'Value':<12} {'Unit'}")
                            print(f"  {'-'*14} {'-'*6} {'-'*10} {'-'*20}")
                            for item in series:
                                val_str = (
                                    f"{item['value']:g}"
                                    if isinstance(item["value"], (int, float))
                                    else str(item["value"])
                                )
                                c_str = str(item.get("country", ""))[:14]
                                year_val = item.get("year", "")
                                year_str = f"{year_val}*" if item.get("is_anchor") else str(year_val)
                                notes_val = str(item.get("notes", "")).strip() if item.get("notes") else ""
                                if item.get("is_anchor") and "[Ancla" not in notes_val:
                                    notes_val = f"{notes_val} [Ancla]".strip()
                                unit_val = str(item.get("unit", "")).strip() if item.get("unit") else ""
                                desc_str = f"{unit_val}  {notes_val}".strip() if notes_val else unit_val
                                print(
                                    f"  {c_str:<16} {year_str:<8} {val_str:<12} {desc_str}"
                                )
                        elif has_member_col:
                            print(f"  {'Year':<8} {'Member / Group':<34} {'Value':<12} {'Unit'}")
                            print(f"  {'-'*6} {'-'*32} {'-'*10} {'-'*20}")
                            for item in series:
                                val_str = (
                                    f"{item['value']:g}"
                                    if isinstance(item["value"], (int, float))
                                    else str(item["value"])
                                )
                                member_str = str(item.get("member", ""))[:32]
                                year_val = item.get("year", "")
                                year_str = f"{year_val}*" if item.get("is_anchor") else str(year_val)
                                notes_val = str(item.get("notes", "")).strip() if item.get("notes") else ""
                                if item.get("is_anchor") and "[Ancla" not in notes_val:
                                    notes_val = f"{notes_val} [Ancla]".strip()
                                unit_val = str(item.get("unit", "")).strip() if item.get("unit") else ""
                                desc_str = f"{unit_val}  {notes_val}".strip() if notes_val else unit_val
                                print(
                                    f"  {year_str:<8} {member_str:<34} {val_str:<12} {desc_str}"
                                )
                        else:
                            print(f"  {'Year':<8} {'Value':<12} {'Unit'}")
                            print(f"  {'-'*6} {'-'*10} {'-'*20}")
                            for item in series:
                                val_str = (
                                    f"{item['value']:g}"
                                    if isinstance(item["value"], (int, float))
                                    else str(item["value"])
                                )
                                year_val = item.get("year", "")
                                year_str = f"{year_val}*" if item.get("is_anchor") else str(year_val)
                                notes_val = str(item.get("notes", "")).strip() if item.get("notes") else ""
                                if item.get("is_anchor") and "[Ancla" not in notes_val:
                                    notes_val = f"{notes_val} [Ancla]".strip()
                                unit_val = str(item.get("unit", "")).strip() if item.get("unit") else ""
                                desc_str = f"{unit_val}  {notes_val}".strip() if notes_val else unit_val
                                print(
                                    f"  {year_str:<8} {val_str:<12} {desc_str}"
                                )

                    elif emp.get("observation_exists"):
                        print("Empirical Observation:")
                        val = emp.get("value")
                        unit = emp.get("unit", "")
                        unit_str = f" {unit}" if unit else ""
                        print(f"Value:     {val}{unit_str}")
                        print(f"Year:      {emp.get('year')}")
                        print(f"Notes:     {emp.get('notes', '')}")
                    else:
                        print("Empirical Observation:")
                        reason = emp.get("reason", "No observation available")
                        print(f"Status:    Unavailable ({reason})")


                if parsed.explain and res.execution_trace:
                    print("-" * 70)
                    print("Execution Trace & Decision Audit Logs:")
                    for trace_line in res.execution_trace:
                        print(f"  {trace_line}")

                print("=" * 70)
                return 0
            except CepalStatError as err:
                print(f"CEPALSTAT Error: {err}", file=sys.stderr)
                return 1

    if parsed.command == "search":
        catalog_store = CatalogStore()
        if catalog_store.is_built():
            results = catalog_store.search(parsed.query, limit=parsed.limit)
            if not results:
                print(f"No indicators found matching '{parsed.query}'.")
                return 0
            count = len(results)
            limit = min(count, parsed.limit)
            print(f"Found {count} indicators (showing top {limit}):")
            for item in results[:limit]:
                print(f"  [{item.indicator_id}] {item.name}")
                if item.full_path:
                    print(f"      Path: {item.full_path}")
            return 0

    try:
        with CepalStatClient() as client:
            if parsed.command == "search":
                print(
                    "(Tip: Run 'statscepal catalog build' to enable fast offline search)",
                    file=sys.stderr,
                )
                tree = ThematicTree(client)
                results = tree.search(parsed.query)
                if not results:
                    print(f"No indicators found matching '{parsed.query}'.")
                    return 0
                count = len(results)
                limit = min(count, parsed.limit)
                print(f"Found {count} indicators (showing top {limit}):")
                for item in results[:limit]:
                    print(f"  [{item.indicator_id}] {item.name}")
                    if item.path:
                        print(f"      Path: {item.path}")
                return 0

            if parsed.command == "info":
                extractor = DataExtractor(client)
                target_id = parsed.indicator_id
                mapped_from = None
                from unofficial_cepalstat_mcp.semantic.registry import EMPIRICAL_INDICATOR_ID_MAP

                if (
                    target_id in EMPIRICAL_INDICATOR_ID_MAP
                    and EMPIRICAL_INDICATOR_ID_MAP[target_id] != target_id
                ):
                    mapped_from = target_id
                    target_id = EMPIRICAL_INDICATOR_ID_MAP[target_id]

                meta = extractor.get_metadata(target_id)
                if not meta:
                    print(f"Indicator {parsed.indicator_id} not found.")
                    return 1
                if mapped_from:
                    print(
                        f"=== Indicator {target_id} (CEPALSTAT API Table, mapped from canonical ID {mapped_from}) ==="
                    )
                else:
                    print(f"=== Indicator {target_id} ===")
                print(f"Name: {meta.get('indicator_name')}")
                print(f"Area: {meta.get('area')}")
                print(f"Unit: {meta.get('unit')}")
                print(f"Definition: {meta.get('definition')}")
                return 0

            if parsed.command == "fetch":
                extractor = DataExtractor(client)
                member_ids: list[int] | None = None
                if parsed.members:
                    try:
                        member_ids = [
                            int(m.strip()) for m in parsed.members.split(",") if m.strip()
                        ]
                    except ValueError:
                        print(
                            f"Error: Invalid member IDs '{parsed.members}'. Must be comma-separated integers.",
                            file=sys.stderr,
                        )
                        return 1

                df = extractor.get_dataframe(
                    parsed.indicator_id, members=member_ids, decode_labels=True
                )
                if df.empty:
                    print("No data records returned.")
                    return 0

                if parsed.csv:
                    df.to_csv(parsed.csv, index=False)
                    print(f"Saved {len(df)} rows to {parsed.csv}")
                else:
                    print(df.to_string(index=False))
                return 0

            if parsed.command == "analyze":
                if parsed.analyze_command == "desacople":
                    countries = [
                        c.strip() for c in parsed.countries.split(",") if c.strip()
                    ]
                    periods = [
                        ("P1: 2015-2019", 2015, 2019),
                        ("P2: 2021-2023", 2021, 2023),
                    ]
                    extractor = DataExtractor(client=client)
                    analyzer = DecouplingAnalyzer(extractor=extractor)
                    dataset = analyzer.analyze_countries(
                        countries=countries, periods=periods
                    )

                    rows = []
                    for r in dataset.records:
                        rows.append(
                            {
                                "País": r.country,
                                "Periodo": r.period_label,
                                "Δ PIB pc (%)": r.gdp_pc_growth_mean,
                                "Δ Pob. Tot (pp)": r.poverty_total_change_pp,
                                "Δ Pob. Ext (pp)": r.poverty_extreme_change_pp,
                                "Δ Sal. Real (%)": r.real_min_wage_change_pct,
                                "Infl. Alim (%)": r.food_inflation_mean_pct,
                                "Brecha Sal/Alim (%)": r.food_wage_gap_pct,
                                "Δ Gini": r.gini_change,
                                "Elasticidad": r.social_elasticity,
                                "Cuadrante": r.quadrant,
                            }
                        )
                    df_table = pd.DataFrame(rows)
                    if not df_table.empty:
                        print(df_table.to_string(index=False))
                    else:
                        print("No records found.")

                    if parsed.econometrics:
                        summary = analyzer.run_econometric_regression(dataset)
                        print("=" * 70)
                        print("CEPALSTAT ECONOMETRIC REGRESSION SUMMARY (OLS)")
                        print(
                            f"Dep. Variable: Δ Pobreza Total (pp) | N = {summary.n_obs} | "
                            f"R² = {summary.r_squared} (Adj. R² = {summary.r_squared_adj})"
                        )
                        print(f"F-statistic p-value: {summary.f_pvalue}")
                        print("-" * 70)
                        print("Variable              Coef.      Std.Err.   p-value    [95% Conf. Interval]")
                        print("-" * 70)
                        for var_name, coef in summary.coefficients.items():
                            std_err = summary.std_errors.get(var_name, 0.0)
                            pval = summary.p_values.get(var_name, 1.0)
                            ci = summary.confidence_intervals.get(var_name, (0.0, 0.0))
                            print(
                                f"{var_name:<21} {coef:>10.4f} {std_err:>10.4f} {pval:>10.4f}    [{ci[0]:.4f}, {ci[1]:.4f}]"
                            )
                        print("=" * 70)

                    if parsed.output:
                        df_table.to_csv(parsed.output, index=False)
                        print(f"Saved {len(df_table)} rows to {parsed.output}")

                    return 0

    except CepalStatError as err:
        print(f"CEPALSTAT Error: {err}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
