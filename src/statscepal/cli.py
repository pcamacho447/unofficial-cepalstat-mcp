"""Command Line Interface for CEPALSTAT."""

import argparse
import sys
from typing import Sequence

from statscepal.client import CepalStatClient
from statscepal.exceptions import CepalStatError
from statscepal.extractor import DataExtractor
from statscepal.thematic_tree import ThematicTree


def main(args: Sequence[str] | None = None) -> int:
    """Run the CEPALSTAT CLI command.

    Args:
        args: Optional list of command-line arguments. If None, sys.argv[1:] is used.

    Returns:
        Exit code: 0 for success, non-zero for errors.
    """
    parser = argparse.ArgumentParser(
        prog="statscepal",
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

    try:
        parsed = parser.parse_args(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0

    if not parsed.command:
        parser.print_help()
        return 0

    try:
        with CepalStatClient() as client:
            if parsed.command == "search":
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
                meta = extractor.get_metadata(parsed.indicator_id)
                if not meta:
                    print(f"Indicator {parsed.indicator_id} not found.")
                    return 1
                print(f"=== Indicator {parsed.indicator_id} ===")
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

    except CepalStatError as err:
        print(f"CEPALSTAT Error: {err}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
