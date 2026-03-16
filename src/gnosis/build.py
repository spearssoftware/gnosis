"""Gnosis build pipeline and CLI entry point."""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from gnosis.merge.places import merge_places
from gnosis.merge.verse_index import build_verse_index
from gnosis.parsers.openbible import parse_openbible
from gnosis.parsers.theographic import parse_theographic
from gnosis.validate.checks import print_results, validate

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
OUTPUT_DIR = PROJECT_ROOT / "output"

console = Console()


def _parse_all() -> tuple:
    """Parse and merge all sources. Returns (people, places, events, groups, match_log)."""
    people, places, events, groups = parse_theographic(SOURCES_DIR / "theographic")
    openbible_places = parse_openbible(SOURCES_DIR / "openbible")
    places, match_log = merge_places(places, openbible_places)
    return people, places, events, groups, match_log


def _write_output(data: dict, filename: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    console.print(f"  Wrote {path.name} ({len(data)} entries)")


def cmd_build(strict: bool = False) -> bool:
    """Run the full build pipeline."""
    console.print("[bold]Gnosis Build Pipeline[/bold]\n")

    with Progress(console=console) as progress:
        task = progress.add_task("Parsing sources...", total=3)

        people, places, events, groups, match_log = _parse_all()
        progress.update(task, advance=1, description="Building verse index...")

        verse_index = build_verse_index(people, places, events)
        progress.update(task, advance=1, description="Validating...")

        results = validate(people, places, events, groups, match_log, strict=strict)
        progress.update(task, advance=1, description="Done ✓")

    console.print()
    ok = print_results(results)
    console.print()

    if not ok:
        console.print("[red]Validation failed. Output not written.[/red]")
        return False

    # Serialize to JSON dicts keyed by slug ID
    _write_output(
        {k: v.model_dump(exclude_none=True) for k, v in sorted(people.items())},
        "people.json",
    )
    _write_output(
        {k: v.model_dump(exclude_none=True) for k, v in sorted(places.items())},
        "places.json",
    )
    _write_output(
        {k: v.model_dump(exclude_none=True) for k, v in sorted(events.items())},
        "events.json",
    )
    _write_output(
        {k: v.model_dump(exclude_none=True) for k, v in sorted(groups.items())},
        "people-groups.json",
    )
    _write_output(
        {k: v.model_dump() for k, v in sorted(verse_index.items())},
        "verse-index.json",
    )

    console.print("\n[bold green]Build complete.[/bold green]")
    return True


def cmd_validate(strict: bool = False) -> bool:
    """Run validation only (no output written)."""
    console.print("[bold]Gnosis Validation[/bold]\n")

    people, places, events, groups, match_log = _parse_all()
    results = validate(people, places, events, groups, match_log, strict=strict)
    return print_results(results)


def main() -> None:
    parser = argparse.ArgumentParser(prog="gnosis", description="Gnosis biblical knowledge graph")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build", help="Run full build pipeline")
    build_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    validate_parser = subparsers.add_parser("validate", help="Run validation only")
    validate_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    args = parser.parse_args()

    if args.command == "build":
        ok = cmd_build(strict=args.strict)
    elif args.command == "validate":
        ok = cmd_validate(strict=args.strict)
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if ok else 1)
